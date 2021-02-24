import json
import logging
from datetime import datetime
from http import HTTPStatus

from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .anno_defaults import (
    ANNO,
    ANNOTATORJS_FORMAT,
    CATCH_ADMIN_GROUP_ID,
    CATCH_ANNO_FORMAT,
    CATCH_LOG_SEARCH_TIME,
    CATCH_RESPONSE_LIMIT,
    MODERATED_MESSAGE_TEXT,
    MODERATED_MESSAGE_FORMAT,
    PURPOSE_COMMENTING,
    PURPOSE_REPLYING,
)
from .crud import CRUD
from .decorators import require_catchjwt
from .errors import (
    AnnoError,
    AnnotatorJSError,
    DuplicateAnnotationIdError,
    InconsistentAnnotationError,
    MethodNotAllowedError,
    MissingAnnotationError,
    MissingAnnotationInputError,
    NoPermissionForOperationError,
    UnknownResponseFormatError,
)
from .json_models import AnnoJS, Catcha
from .models import Anno
from .search import (
    query_tags,
    query_target_medias,
    query_target_sources,
    query_userid,
    query_username,
)
from .utils import generate_uid

logger = logging.getLogger(__name__)


# mapping for http method and annotation permission type
METHOD_PERMISSION_MAP = {
    "GET": "read",
    "HEAD": "read",
    "DELETE": "delete",
    "PUT": "update",
}


def get_jwt_payload(request):
    try:
        return request.catchjwt
    except Exception:
        raise NoPermissionForOperationError("missing jwt token")


def get_default_permissions_for_user(user):
    return {
        "can_read": [],
        "can_update": [user],
        "can_delete": [user],
        "can_admin": [user],
    }


def get_input_json(request):
    if request.body:
        return json.loads(request.body.decode("utf-8"))
    else:
        raise MissingAnnotationInputError(
            "missing json in body request for create/update"
        )


def process_create(request, anno_id):
    # throws MissingAnnotationInputError
    a_input = get_input_json(request)
    logger.debug("[CREATE BODY ({})] {}".format(anno_id, a_input))

    requesting_user = request.catchjwt["userId"]

    # fill info for create-anno
    a_input["id"] = anno_id
    if "permissions" not in a_input:
        a_input["permissions"] = get_default_permissions_for_user(requesting_user)

    # throws InvalidInputWebAnnotationError
    catcha = Catcha.normalize(a_input)

    # check for conflicts
    Catcha.check_for_create_conflicts(catcha, requesting_user)

    # throws AnnoError
    anno = CRUD.create_anno(catcha)
    return anno


def process_update(request, anno):
    # throws MissingAnnotationInputError
    a_input = get_input_json(request)
    logger.debug("[UPDATE BODY ({})] {}".format(anno.anno_id, a_input))

    requesting_user = request.catchjwt["userId"]

    # throws InvalidInputWebAnnotationError
    catcha = Catcha.normalize(a_input)

    # check if trying to update permissions
    if not CRUD.is_identical_permissions(catcha, anno.raw):
        # check permissions again, but now for admin
        if not has_permission_for_op("admin", request, anno):
            msg = "user({}) not allowed to admin anno({})".format(
                requesting_user, anno.anno_id
            )
            logger.info(msg)
            raise NoPermissionForOperationError(msg)

    # throws AnnoError
    anno = CRUD.update_anno(anno, catcha)
    return anno


@require_http_methods(["GET", "HEAD", "POST", "PUT", "DELETE", "OPTIONS"])
@csrf_exempt
@require_catchjwt
def crud_api(request, anno_id):
    """view to deal with crud api requests."""
    try:
        resp = _do_crud_api(request, anno_id)
    except AnnoError as e:
        logger.error("anno({}): {}".format(anno_id, e), exc_info=True)
        response = JsonResponse(
            status=e.status, data={"status": e.status, "payload": [str(e)]}
        )
    except (ValueError, KeyError) as e:
        logger.error("anno({}): bad input: {}".format(anno_id, e), exc_info=True)
        response = JsonResponse(
            status=HTTPStatus.BAD_REQUEST,
            data={"status": HTTPStatus.BAD_REQUEST, "payload": [str(e)]},
        )
    # no crud errors, try to convert to requested format
    else:
        response_format = CATCH_ANNO_FORMAT
        try:
            formatted_response = _format_response(resp, response_format)
        except (AnnotatorJSError, UnknownResponseFormatError) as e:
            # at this point, the requested operation is completed successfully
            # returns 203 to say op was done, but can't return proper anno json
            status = HTTPStatus.NON_AUTHORITATIVE_INFORMATION  # 203
            error_response = {"id": resp.anno_id, "msg": str(e)}
            logger.error("anno({}): {}".format(anno_id, e), exc_info=True)
            response = JsonResponse(status=status, data=error_response)
        else:
            status = HTTPStatus.OK
            response = JsonResponse(status=status, data=formatted_response)
            if request.method == "POST" or request.method == "PUT":
                # add response header with location for new resource
                response["Location"] = request.build_absolute_uri(
                    reverse("crud_api", kwargs={"anno_id": resp.anno_id})
                )

    # info log
    logger.info(
        "[{0}] {1}:{2} {3} {4}".format(
            request.catchjwt["consumerKey"],
            request.method,
            response.status_code,
            request.path,
            request.META["QUERY_STRING"],
        )
    )
    return response


@require_http_methods(["GET", "HEAD", "POST", "PUT", "DELETE", "OPTIONS"])
@csrf_exempt
@require_catchjwt
def crud_compat_api(request, anno_id):
    """view to deal with crud api requests."""
    try:
        resp = _do_crud_api(request, anno_id)
    except AnnoError as e:
        logger.error("anno({}): {}".format(anno_id, e), exc_info=True)
        response = JsonResponse(
            status=e.status, data={"status": e.status, "payload": [str(e)]}
        )
    except (ValueError, KeyError) as e:
        logger.error("anno({}): {}".format(anno_id, e), exc_info=True)
        response = JsonResponse(
            status=HTTPStatus.BAD_REQUEST,
            data={"status": HTTPStatus.BAD_REQUEST, "payload": [str(e)]},
        )
    # no crud errors, try to convert to requested format
    else:
        response_format = ANNOTATORJS_FORMAT
        try:
            formatted_response = _format_response(resp, response_format)
        except (AnnotatorJSError, UnknownResponseFormatError) as e:
            # at this point, the requested operation is completed successfully
            # returns 203 to say op was done, but can't return proper anno json
            status = HTTPStatus.NON_AUTHORITATIVE_INFORMATION  # 203
            error_response = {"id": resp.anno_id, "msg": str(e)}
            logger.error("anno({}): {}".format(anno_id, e), exc_info=True)
            response = JsonResponse(status=status, data=error_response)
        else:
            status = HTTPStatus.OK
            response = JsonResponse(status=status, data=formatted_response)
            if request.method == "POST" or request.method == "PUT":
                # add response header with location for new resource
                response["Location"] = request.build_absolute_uri(
                    reverse("crud_api", kwargs={"anno_id": resp.anno_id})
                )

    # info log
    logger.info(
        "[{0}] {1}:{4} {2} {3}".format(
            request.catchjwt["consumerKey"],
            request.method,
            request.path,
            request.META["QUERY_STRING"],
            response.status_code,
        )
    )
    return response


def has_permission_for_op(op, request, anno):
    # back-compat
    if request.catchjwt["userId"] == CATCH_ADMIN_GROUP_ID:
        return True

    # catchpy trusts the jwt; `override` missing means it's back-compat.
    # in back-compat, catchpy trusts the hxat, and performs any op requested.
    override = (
        "CAN_{}".format(op).upper() in request.catchjwt["override"]
        if "override" in request.catchjwt
        else True
    )

    if anno.has_permission_for(op, request.catchjwt["userId"]) or override:
        return True
    else:
        return False


def _do_crud_api(request, anno_id):
    # assumes went through main auth and is ok

    # info log
    logger.info(
        "[{0}] {1} {2}/{3}".format(
            request.catchjwt["consumerKey"],
            request.method,
            request.path,
            anno_id,
        )
    )

    # retrieves anno
    anno = CRUD.get_anno(anno_id)

    if anno is None:
        if request.method == "POST":
            # sure there's no duplication and it's a create
            r = process_create(request, anno_id)
        else:
            raise MissingAnnotationError("anno({}) not found".format(anno_id))
    else:
        if request.method == "POST":
            raise DuplicateAnnotationIdError(
                "anno({}): already exists, failed to create".format(anno.anno_id)
            )

        if not has_permission_for_op(
            METHOD_PERMISSION_MAP[request.method], request, anno
        ):
            raise NoPermissionForOperationError(
                "no permission to {} anno({}) for user({})".format(
                    METHOD_PERMISSION_MAP[request.method],
                    anno_id,
                    request.catchjwt["userId"],
                )
            )

        if request.method == "GET" or request.method == "HEAD":
            r = CRUD.read_anno(anno)
        elif request.method == "DELETE":
            r = CRUD.delete_anno(anno)
        elif request.method == "PUT":
            r = process_update(request, anno)
        else:
            raise MethodNotAllowedError(
                "method ({}) not allowed".format(request.method)
            )

    assert r is not None
    return r

def _do_overwrite():
    # if anno.is_hidden and
    # request.catchjwt["userId"] in [CATCH_ADMIN_GROUP_ID, anno.creator_id]
    # and not req.QUERYSTRING has everwrite
    return True

def _format_response(anno_result, response_format):
    # is it single anno or a QuerySet from search?
    is_single = isinstance(anno_result, Anno)

    if is_single:
        if response_format == ANNOTATORJS_FORMAT:
            response = AnnoJS.convert_from_anno(anno_result)
        elif response_format == CATCH_ANNO_FORMAT:
            # doesn't need formatting! SERIALIZE as webannotation
            ###################################################################>>
            # MODERATION
            #
            catcha = anno_result.serialized
            if _do_overwrite():
                # if anno.is_hidden and
                # request.catchjwt["userId"] in [CATCH_ADMIN_GROUP_ID, anno.creator_id]
                # and not req.QUERYSTRING has everwrite
                for bi in catcha["body"]["items"]:
                    if bi["purpose"] in [PURPOSE_COMMENTING, PURPOSE_REPLYING]:
                        bi["value"] = MODERATED_MESSAGE_TEXT
                        bi["format"] = MODERATED_MESSAGE_FORMAT
            #
            ###################################################################>>
            response = catcha
        else:
            # worked hard and have nothing to show: format UNKNOWN
            raise UnknownResponseFormatError(
                "unknown response format({})".format(response_format)
            )
    else:  # assume it's a QuerySet resulting from search
        response = {
            "rows": [],
        }
        if response_format == ANNOTATORJS_FORMAT:
            failed = []
            for anno in anno_result:
                try:
                    annojs = AnnoJS.convert_from_anno(anno)
                except AnnotatorJSError as e:
                    failed.append({"id": anno.anno_id, "msg": str(e)})
                else:
                    response["rows"].append(annojs)
            response["size"] = len(response["rows"])
            response["failed"] = failed
            response["size_failed"] = len(failed)
        elif response_format == CATCH_ANNO_FORMAT:
            # doesn't need formatting! SERIALIZE as webannotation
            for anno in anno_result:
                ###################################################################>>
                # MODERATION
                #
                catcha = anno.serialized
                if _do_overwrite():
                    # if anno.is_hidden and
                    # request.catchjwt["userId"] in [CATCH_ADMIN_GROUP_ID, anno.creator_id]
                    # and not req.QUERYSTRING has everwrite
                    for bi in catcha["body"]["items"]:
                        if bi["purpose"] in [PURPOSE_COMMENTING, PURPOSE_REPLYING]:
                            bi["value"] = MODERATED_MESSAGE_TEXT
                            bi["format"] = MODERATED_MESSAGE_FORMAT
                #
                ###################################################################>>
                response["rows"].append(catcha)
            response["size"] = len(response["rows"])

        else:
            # worked hard and have nothing to show: format UNKNOWN
            raise UnknownResponseFormatError(
                "unknown response format({})".format(response_format)
            )

    return response


def partial_update_api(request, anno_id):
    pass


def search_api(request):
    # naomi note: always return catcha
    try:
        resp = _do_search_api(request, back_compat=False)

        logger.debug(
            (
                "[SEARCH RESULT] total({}), size({}), "
                "limit({}), offset({}), size_failed({})"
            ).format(
                resp["total"],
                resp["size"],
                resp["limit"],
                resp["offset"],
                resp.get("size_failed", 0),
            )
        )

        return JsonResponse(status=HTTPStatus.OK, data=resp)

    except AnnoError as e:
        logger.error("search failed: {}".format(e), exc_info=True)
        return JsonResponse(
            status=e.status, data={"status": e.status, "payload": [str(e)]}
        )

    except Exception as e:
        logger.error("search failed; request({})".format(request), exc_info=True)
        return JsonResponse(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            data={"status": HTTPStatus.INTERNAL_SERVER_ERROR, "payload": [str(e)]},
        )


@require_http_methods(["GET", "HEAD", "POST", "OPTIONS"])
@csrf_exempt
@require_catchjwt
def search_back_compat_api(request):
    try:
        resp = _do_search_api(request, back_compat=True)
        response = JsonResponse(status=HTTPStatus.OK, data=resp)

    except AnnoError as e:
        logger.error("search failed: {}".format(e), exc_info=True)
        response = JsonResponse(
            status=e.status, data={"status": e.status, "payload": [str(e)]}
        )

    except Exception as e:
        logger.error("search failed; request({}): {}".format(request, e), exc_info=True)
        response = JsonResponse(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            data={"status": HTTPStatus.INTERNAL_SERVER_ERROR, "payload": [str(e)]},
        )

    # info log
    logger.info(
        "[{0}] {1}:{4} {2} {3}".format(
            request.catchjwt["consumerKey"],
            request.method,
            request.path,
            request.META["QUERY_STRING"],
            response.status_code,
        )
    )
    return response


def step_in_time(delta_list=None):
    if not delta_list:
        return [(datetime.utcnow(), 0)]

    i = len(delta_list) - 1
    ts = datetime.utcnow()
    d = ts - delta_list[i][0]
    delta_list.append((ts, d))


def _do_search_api(request, back_compat=False):

    # prep to count how long a search is taking
    ts_deltas = step_in_time()

    # info log
    logger.info(
        "[{3}] {0} {1} {2}".format(
            request.method,
            request.path,
            request.META["QUERY_STRING"],
            request.catchjwt["consumerKey"],
        )
    )

    payload = request.catchjwt

    # filter out the soft-deleted
    query = Anno._default_manager.filter(anno_deleted=False)

    # TODO: check override POLICIES (override allow private reads)
    if (
        "CAN_READ" not in payload.get("override", [])
        and request.catchjwt["userId"] != CATCH_ADMIN_GROUP_ID
    ):
        # filter out permission cannot_read
        q = Q(can_read__len=0) | Q(can_read__contains=[payload["userId"]])
        query = query.filter(q)

    if back_compat:
        query = process_search_back_compat_params(request, query)
    else:
        query = process_search_params(request, query)

    # delta[1] - process search params
    step_in_time(ts_deltas)

    # sort by created date, descending (more recent first)
    query = query.order_by("-created")

    # max results and offset
    try:
        limit = int(request.GET.get("limit", 10))
    except ValueError:
        limit = CATCH_RESPONSE_LIMIT

    try:
        offset = int(request.GET.get("offset", 0))
    except ValueError:
        offset = 0

    # calculate response size
    total = query.count()
    if limit < 0:  # limit -1 means complete result, limit response size
        size = (
            CATCH_RESPONSE_LIMIT
            if (total - offset) > CATCH_RESPONSE_LIMIT
            else (total - offset)
        )
    else:
        size = limit

    # delta[2]
    step_in_time(ts_deltas)

    q_result = query[offset : (offset + size)]

    # delta[3]
    step_in_time(ts_deltas)

    if back_compat:
        response_format = ANNOTATORJS_FORMAT
    else:
        response_format = CATCH_ANNO_FORMAT

    # delta[4] - just before formatting
    step_in_time(ts_deltas)

    response = _format_response(q_result, response_format)

    # delta[5] - how  long to format
    step_in_time(ts_deltas)

    if CATCH_LOG_SEARCH_TIME:
        logger.info(
            (
                "[SEARCH_TIME] (prep, count, eval, -, format, total) "
                "{0:12.3f} {1:12.3f} {2:12.3f} {3:12.3f} {4:12.3f} {5:12.3f}"
            ).format(
                (ts_deltas[1][1].total_seconds()),
                (ts_deltas[2][1].total_seconds()),
                (ts_deltas[3][1].total_seconds()),
                (ts_deltas[4][1].total_seconds()),
                (ts_deltas[5][1].total_seconds()),
                (datetime.utcnow() - ts_deltas[0][0]).total_seconds(),
            )
        )
    response["total"] = total  # add response info
    response["limit"] = limit
    response["offset"] = offset
    return response


def process_search_params(request, query):
    usernames = request.GET.getlist("username", [])
    if not usernames:
        usernames = request.GET.getlist("username[]", [])
    if usernames:
        query = query.filter(query_username(usernames))

    excl_usernames = request.GET.getlist("exclude_username", [])
    if not excl_usernames:
        excl_usernames = request.GET.getlist("exclude_username[]", [])
    if excl_usernames:
        query = query.exclude(query_username(excl_usernames))

    userids = request.GET.getlist("userid", [])
    if not userids:
        userids = request.GET.getlist("userid[]", [])
    if userids:
        query = query.filter(query_userid(userids))

    excl_userids = request.GET.getlist("exclude_userid", [])
    if not excl_userids:
        excl_userids = request.GET.getlist("exclude_userid[]", [])
    if excl_userids:
        query = query.exclude(query_userid(excl_userids))

    tags = request.GET.getlist("tag", [])
    if not tags:
        tags = request.GET.getlist("tag[]", [])
    if tags:
        query = query.filter(query_tags(tags))

    targets = request.GET.get("target_source", [])
    if not targets:
        targets = request.GET.getlist("target_source[]", [])
    if targets:
        query = query.filter(query_target_sources(targets))

    medias = request.GET.getlist("media", [])
    if not medias:
        medias = request.GET.getlist("media[]", [])
    if medias:
        mlist = [x.capitalize() for x in medias]
        query = query.filter(query_target_medias(mlist))

    text = request.GET.get("text", [])
    if text:
        query = query.filter(body_text__search=text)

    # custom searches for platform params
    q = Anno.custom_manager.search_expression(request.GET)

    if q:
        query = query.filter(q)

    return query


def process_search_back_compat_params(request, query):

    parent_id = request.GET.get("parentid", None)
    if parent_id:  # not None nor empty string
        query = query.filter(anno_reply_to__anno_id=parent_id)

    medias = request.GET.getlist("media", [])
    if medias:
        if "comment" in medias:
            medias.remove("comment")
            medias.append(ANNO)

        mlist = [x.capitalize() for x in medias]
        query = query.filter(query_target_medias(mlist))

    target = request.GET.get("uri", None)
    if target:
        if parent_id:  # not None nor empty string
            pass  # in this case `uri` is irrelevant; see [2] at the bottom
        else:
            query = query.filter(raw__platform__target_source_id=target)

    text = request.GET.get("text", [])
    if text:
        query = query.filter(body_text__search=text)

    userids = request.GET.getlist("userid", [])
    if not userids:  # back-compat list in querystring
        userids = request.GET.getlist("userid[]", [])
    if userids:
        query = query.filter(query_userid(userids))

    usernames = request.GET.getlist("username", [])
    if usernames:
        query = query.filter(query_username(usernames))

    source = request.GET.get("source", None)
    if source:  # 19dec17 naomi: does [2] applies to `source` as well?
        query = query.filter(query_target_sources([source]))

    context_id = request.GET.get("contextId", None)
    if context_id is None:  # forward-compat!!! see [1] at the bottom
        context_id = request.GET.get("context_id", None)
    if context_id:
        query = query.filter(raw__platform__context_id=context_id)

    collection_id = request.GET.get("collectionId", None)
    if collection_id is None:  # forward-compat!!! see [1] at the bottom
        collection_id = request.GET.get("collection_id", None)
    if collection_id:
        query = query.filter(raw__platform__collection_id=collection_id)

    tags = request.GET.getlist("tag", [])
    if tags:
        query = query.filter(query_tags(tags))

    return query


@require_http_methods(["POST", "OPTIONS"])
@csrf_exempt
@require_catchjwt
def copy_api(request):

    # check permissions to copy
    jwt_payload = get_jwt_payload(request)
    if "CAN_COPY" not in jwt_payload["override"]:
        msg = "user ({}) not allowed to copy".format(jwt_payload["name"])
        logger.error(msg, exc_info=True)
        raise NoPermissionForOperationError(msg)

    params = get_input_json(request)

    # sanity check: not allowed to copy to same course or collection
    if params["source_context_id"] == params["target_context_id"]:
        msg = "not allowed to copy to same context_id({})".format(
            params["source_context_id"]
        )
        logger.error(msg, exc_info=True)
        raise InconsistentAnnotationError(msg)

    back_compat = params["back_compat"] if "back_compat" in params else False

    userids = params["userid_list"] if "userid_list" in params else None
    usernames = params["username_list"] if "username_list" in params else None
    anno_list = CRUD.select_annos(
        context_id=params["source_context_id"],
        collection_id=params["source_collection_id"],
        platform_name=params["platform_name"],
        userid_list=userids,
        username_list=usernames,
    )

    logger.debug("select for copy returned ({})".format(anno_list.count()))

    resp = CRUD.copy_annos(
        anno_list,
        params["target_context_id"],
        params["target_collection_id"],
        back_compat=back_compat,
    )

    return JsonResponse(status=HTTPStatus.OK, data=resp)


def process_partial_update(request, anno_id):
    # assumes request.method == PUT
    return {
        "status": HTTPStatus.NOT_IMPLEMENTED,
        "payload": ["partial update not implemented."],
    }

    # retrieve anno

    # request user can update this?

    # validates -- no formatting here

    # performs update and save to database

    # needs formatting?
    pass


@require_http_methods(["POST", "GET", "OPTIONS"])
@csrf_exempt
@require_catchjwt
def create_or_search(request):
    """view for create, with no anno_id in querystring."""

    if request.method == "POST":
        anno_id = generate_uid()
        response = crud_api(request, anno_id)

        # info log
        logger.info(
            "[{0}] {1}:{4} {2} {3}".format(
                request.catchjwt["consumerKey"],
                request.method,
                request.path,
                anno_id,
                response.status_code,
            )
        )
        return response
    else:  # it's a GET
        response = search_api(request)
        # info log
        logger.info(
            "[{0}] {1}:{4} {2} {3}".format(
                request.catchjwt["consumerKey"],
                request.method,
                request.path,
                request.META["QUERY_STRING"],
                response.status_code,
            )
        )
        return response


@require_http_methods(["POST", "OPTIONS"])
@csrf_exempt
@require_catchjwt
def crud_compat_create(request):
    """view for create, with no anno_id in querystring."""
    must_be_int = True
    anno_id = generate_uid(must_be_int)
    return crud_compat_api(request, anno_id)


@require_http_methods(["DELETE", "OPTIONS"])
@csrf_exempt
@require_catchjwt
def crud_compat_delete(request, anno_id):
    """back compat view for delete."""
    return crud_compat_api(request, anno_id)


@require_http_methods(["GET", "OPTIONS"])
@csrf_exempt
@require_catchjwt
def crud_compat_read(request, anno_id):
    """back compat view for read."""
    return crud_compat_api(request, anno_id)


@require_http_methods(["POST", "PUT", "OPTIONS"])
@csrf_exempt
@require_catchjwt
def crud_compat_update(request, anno_id):
    """back compat view for update."""

    # info log
    logger.info(
        "[{0}] {1} {2} {3}".format(
            request.catchjwt["consumerKey"],
            request.method,
            request.path,
            anno_id,
        )
    )

    try:
        resp = _do_crud_compat_update(request, anno_id)
        status = HTTPStatus.OK
        response = JsonResponse(status=status, data=resp)

        # add response header with location for new resource
        response["Location"] = request.build_absolute_uri(
            reverse("compat_read", kwargs={"anno_id": resp["id"]})
        )

    except AnnoError as e:
        logger.error("anno({}): {}".format(anno_id, e), exc_info=True)
        response = JsonResponse(
            status=e.status, data={"status": e.status, "payload": [str(e)]}
        )

    except (ValueError, KeyError) as e:
        logger.error("anno({}): {}".format(anno_id, e), exc_info=True)
        response = JsonResponse(
            status=HTTPStatus.BAD_REQUEST,
            data={"status": HTTPStatus.BAD_REQUEST, "payload": [str(e)]},
        )

    # info log
    logger.info(
        "[{0}] {1}:{4} {2} {3}".format(
            request.catchjwt["consumerKey"],
            request.method,
            request.path,
            request.META["QUERY_STRING"],
            response.status_code,
        )
    )
    return response


def _do_crud_compat_update(request, anno_id):
    # retrieves anno
    anno = CRUD.get_anno(anno_id)

    if anno is None:
        raise MissingAnnotationError("anno({}) not found".format(anno_id))

    if not has_permission_for_op("update", request, anno):
        raise NoPermissionForOperationError(
            "no permission to {} anno({}) for user({})".format(
                METHOD_PERMISSION_MAP[request.method],
                anno_id,
                request.catchjwt["userId"],
            )
        )

    r = process_update(request, anno)
    response_format = ANNOTATORJS_FORMAT
    return _format_response(r, response_format)


"""
[1] got rid of camelCase in v2 for uniformity, so contextId is not allowed.
    BUT, it might be that users want to set `context-id` in back-compat
    searches... i did this in performance test and was thrown out by having the
    whole db as result. In back-compat having a search return everything will
    cause problems because of the anno_id: in back-compat it must be an
    integer.

[2] in back-compat mode, the hxat always sends a filter for `uri` in searches.
    Usually, `uri` is translated as target_source_id (internal id for target);
    but in searches for replies, `uri` carries the internal id for the target
    annotated by the parent, instead of the parent id (which is the source
    being annotated). So, in the "search for replies" context, the use of `uri`
    in the list of filters selects OUT the replies the search actually wants
    and should be ignored.
"""
