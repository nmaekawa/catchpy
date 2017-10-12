from datetime import datetime
import dateutil
from functools import wraps
import json
import logging

from django.db.models import Q
from django.conf import settings
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from http import HTTPStatus

from .json_models import AnnoJS
from .json_models import Catcha
from .crud import CRUD
from .errors import AnnoError
from .errors import AnnotatorJSError
from .errors import InvalidAnnotationCreatorError
from .errors import DuplicateAnnotationIdError
from .errors import MethodNotAllowedError
from .errors import MissingAnnotationError
from .errors import MissingAnnotationInputError
from .errors import NoPermissionForOperationError
from .errors import UnknownResponseFormatError
from .search import query_username
from .search import query_userid
from .search import query_tags
from .search import query_target_medias
from .search import query_target_sources
from .models import Anno
from .utils import generate_uid

from .anno_defaults import ANNOTATORJS_FORMAT
from .anno_defaults import CATCH_ADMIN_GROUP_ID
from .anno_defaults import CATCH_ANNO_FORMAT
from .anno_defaults import CATCH_CURRENT_SCHEMA_VERSION
from .anno_defaults import CATCH_JSONLD_CONTEXT_IRI
from .anno_defaults import CATCH_RESPONSE_LIMIT
from .anno_defaults import CATCH_LOG_SEARCH_TIME


logger = logging.getLogger(__name__)


# mapping for http method and annotation permission type
METHOD_PERMISSION_MAP = {
    'GET': 'read',
    'HEAD': 'read',
    'DELETE': 'delete',
    'PUT': 'update',
}


def require_catchjwt(view_func):
    def _decorator(request, *args, **kwargs):
        # check that middleware added jwt info in request
        catchjwt = getattr(request, 'catchjwt', None)
        if catchjwt is None:
            return JsonResponse(
                status=HTTPStatus.UNAUTHORIZED,
                data={'status': HTTPStatus.UNAUTHORIZED,
                      'payload': ['looks like catchjwt middleware is not on']}
            )
        if catchjwt['error']:
            return JsonResponse(
                status=HTTPStatus.UNAUTHORIZED,
                data={'status': HTTPStatus.UNAUTHORIZED,
                      'payload': catchjwt['error']},
            )

        response = view_func(request, *args, **kwargs)
        return response
    return wraps(view_func)(_decorator)


def get_jwt_payload(request):
    try:
        return request.catchjwt
    except Exception:
        raise NoPermissionForOperationError('missing jwt token')


def get_default_permissions_for_user(user):
    return {
        'can_read': [],
        'can_update': [user],
        'can_delete': [user],
        'can_admin': [user],
    }


def get_input_json(request):
    if request.body:
        return json.loads(request.body.decode('utf-8'))
    else:
        raise MissingAnnotationInputError(
            'missing json in body request for create/update')


def process_create(request, anno_id):
    # throws MissingAnnotationInputError
    a_input = get_input_json(request)
    requesting_user = request.catchjwt['userId']

    # fill info for create-anno
    a_input['id'] = anno_id
    if 'permissions' not in a_input:
        a_input['permissions'] = get_default_permissions_for_user(
            requesting_user)

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
    requesting_user = request.catchjwt['userId']

    # throws InvalidInputWebAnnotationError
    catcha = Catcha.normalize(a_input)

    # check if trying to update permissions
    if not CRUD.is_identical_permissions(catcha, anno.raw):
        # check permissions again, but now for admin
        if not has_permission_for_op('admin', request, anno):
            msg = 'user({}) not allowed to admin anno({})'.format(
                requesting_user, anno.anno_id)
            logger.info(msg)
            raise NoPermissionForOperationError(msg)

    # throws AnnoError
    anno = CRUD.update_anno(anno, catcha)
    return anno


@require_http_methods(['GET', 'HEAD', 'POST', 'PUT', 'DELETE'])
@csrf_exempt
@require_catchjwt
def crud_api(request, anno_id):
    '''view to deal with crud api requests.'''
    try:
        resp = _do_crud_api(request, anno_id)
    except AnnoError as e:
        return JsonResponse(status=e.status,
                            data={'status': e.status, 'payload': [str(e)]})
    except (ValueError, KeyError) as e:
        logger.error('anno({}): bad input:'.format(anno_id), exc_info=True)
        return JsonResponse(
            status=HTTPStatus.BAD_REQUEST,
            data={'status': HTTPStatus.BAD_REQUEST, 'payload': [str(e)]})
    # no crud errors, try to convert to requested format
    else:
        response_format = CATCH_ANNO_FORMAT
        try:
            formatted_response = _format_response(resp, response_format)
        except (AnnotatorJSError,
                UnknownResponseFormatError) as e:
            # at this point, the requested operation is completed successfully
            # returns 203 to say op was done, but can't return proper anno json
            status = HTTPStatus.NON_AUTHORITATIVE_INFORMATION  # 203
            error_response = {'id': resp.anno_id,
                              'msg': str(e)}
            response = JsonResponse(status=status, data=error_response)
        else:
            status = HTTPStatus.OK
            response = JsonResponse(status=status, data=formatted_response)
            if request.method == 'POST' or request.method == 'PUT':
                # add response header with location for new resource
                response['Location'] = request.build_absolute_uri(
                    reverse('crud_api', kwargs={'anno_id': resp.anno_id}))

        return response


@require_http_methods(['GET', 'HEAD', 'POST', 'PUT', 'DELETE'])
@csrf_exempt
@require_catchjwt
def crud_compat_api(request, anno_id):
    '''view to deal with crud api requests.'''
    try:
        resp = _do_crud_api(request, anno_id)
    except AnnoError as e:
        return JsonResponse(status=e.status,
                            data={'status': e.status, 'payload': [str(e)]})
    except (ValueError, KeyError) as e:
        logger.error('anno({}): bad input:'.format(anno_id), exc_info=True)
        return JsonResponse(
            status=HTTPStatus.BAD_REQUEST,
            data={'status': HTTPStatus.BAD_REQUEST, 'payload': [str(e)]})
    # no crud errors, try to convert to requested format
    else:
        response_format = ANNOTATORJS_FORMAT
        try:
            formatted_response = _format_response(resp, response_format)
        except (AnnotatorJSError,
                UnknownResponseFormatError) as e:
            # at this point, the requested operation is completed successfully
            # returns 203 to say op was done, but can't return proper anno json
            status = HTTPStatus.NON_AUTHORITATIVE_INFORMATION  # 203
            error_response = {'id': resp.anno_id,
                              'msg': str(e)}
            response = JsonResponse(status=status, data=error_response)
        else:
            status = HTTPStatus.OK
            response = JsonResponse(status=status, data=formatted_response)
            if request.method == 'POST' or request.method == 'PUT':
                # add response header with location for new resource
                response['Location'] = request.build_absolute_uri(
                    reverse('crud_api', kwargs={'anno_id': resp.anno_id}))

        return response


def has_permission_for_op(op, request, anno):
    # back-compat
    if request.catchjwt['userId'] == CATCH_ADMIN_GROUP_ID:
        return True

    if anno.has_permission_for(op, request.catchjwt['userId']) \
       or 'CAN_{}'.format(op).upper() in request.catchjwt['override']:
        return True
    else:
        return False


def _do_crud_api(request, anno_id):
    # assumes went through main auth and is ok

    # retrieves anno
    anno = CRUD.get_anno(anno_id)

    if anno is None:
        if request.method == 'POST':
            # sure there's no duplication and it's a create
            r = process_create(request, anno_id)
        else:
            raise MissingAnnotationError('anno({}) not found'.format(anno_id))
    else:
        if request.method == 'POST':
            raise DuplicateAnnotationIdError(
                'anno({}): already exists, failed to create'.format(
                    anno.anno_id))

        if not has_permission_for_op(
                METHOD_PERMISSION_MAP[request.method], request, anno):
            raise NoPermissionForOperationError(
                'no permission to {} anno({}) for user({})'.format(
                    METHOD_PERMISSION_MAP[request.method], anno_id,
                    request.catchjwt['userId']))

        if request.method == 'GET' or request.method == 'HEAD':
            r = CRUD.read_anno(anno)
        elif request.method == 'DELETE':
            r = CRUD.delete_anno(anno)
        elif request.method == 'PUT':
            r = process_update(request, anno)
        else:
            raise MethodNotAllowedError(
                'method ({}) not allowed'.format(request.method))

    assert r is not None
    return r


def _format_response(anno_result, response_format):
    # is it single anno or a QuerySet from search?
    is_single = isinstance(anno_result, Anno)

    if is_single:
        if response_format == ANNOTATORJS_FORMAT:
            response = AnnoJS.convert_from_anno(anno_result)
        elif response_format == CATCH_ANNO_FORMAT:
            # doesn't need formatting! SERIALIZE as webannotation
            response = anno_result.serialized
        else:
            # worked hard and have nothing to show: format UNKNOWN
            raise UnknownResponseFormatError(
                'unknown response format({})'.format(response_format))
    else:  # assume it's a QuerySet resulting from search
        response = {
             'rows': [],
        }
        if response_format == ANNOTATORJS_FORMAT:
            failed = []
            for anno in anno_result:
                try:
                    annojs = AnnoJS.convert_from_anno(anno)
                except AnnotatorJSError as e:
                    failed.append({'id': anno.anno_id, 'msg': str(e)})
                else:
                    response['rows'].append(annojs)
            response['size'] = len(response['rows'])
            response['failed'] = failed
            response['size_failed'] = len(failed)
        elif response_format == CATCH_ANNO_FORMAT:
            # doesn't need formatting! SERIALIZE as webannotation
            for anno in anno_result:
                response['rows'].append(anno.serialized)
            response['size'] = len(response['rows'])

        else:
            # worked hard and have nothing to show: format UNKNOWN
            raise UnknownResponseFormatError(
                'unknown response format({})'.format(response_format))

    return response


def partial_update_api(request, anno_id):
    pass


def search_api(request):
    # naomi note: always return catcha
    try:
        resp = _do_search_api(request, back_compat=False)
        return JsonResponse(status=HTTPStatus.OK, data=resp)

    except AnnoError as e:
        logger.error('search failed: {}'.format(e, exc_info=True))
        return JsonResponse(status=e.status,
                            data={'status': e.status, 'payload': [str(e)]})

    except Exception as e:
        logger.error('search failed; request({})'.format(request), exc_info=True)
        return JsonResponse(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            data={'status': HTTPStatus.INTERNAL_SERVER_ERROR, 'payload': [str(e)]})


@require_http_methods(['GET', 'HEAD', 'POST'])
@csrf_exempt
@require_catchjwt
def search_back_compat_api(request):
    try:
        resp = _do_search_api(request, back_compat=True)
        return JsonResponse(status=HTTPStatus.OK, data=resp)

    except AnnoError as e:
        logger.error('search failed: {}'.format(e, exc_info=True))
        return JsonResponse(status=e.status,
                            data={'status': e.status, 'payload': [str(e)]})

    except Exception as e:
        logger.error('search failed; request({})'.format(request), exc_info=True)
        return JsonResponse(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            data={'status': HTTPStatus.INTERNAL_SERVER_ERROR, 'payload': [str(e)]})

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

    payload = request.catchjwt

    # filter out the soft-deleted
    query = Anno._default_manager.filter(anno_deleted=False)

    # TODO: check override POLICIES (override allow private reads)
    if 'CAN_READ' not in payload.get('override', []) \
       and request.catchjwt['userId'] != CATCH_ADMIN_GROUP_ID:
        # filter out permission cannot_read
        q = Q(can_read__len=0) | Q(can_read__contains=[payload['userId']])
        query = query.filter(q)

    if back_compat:
        query = process_search_back_compat_params(request, query)
    else:
        query = process_search_params(request, query)


    # delta[1] - process search params
    step_in_time(ts_deltas)


    # sort by created date, descending (more recent first)
    query = query.order_by('-created')


    # max results and offset
    try:
        limit = int(request.GET.get('limit', 10))
    except ValueError:
        limit = 10

    try:
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        offset = 0

    # check if limit -1 meaning complete result
    if limit < 0:
        q_result = query[offset:]
    else:
        q_result = query[offset:(offset+limit)]


    # delta[2] - evaluated again?
    step_in_time(ts_deltas)


    total = query.count()      # is it here when the querysets are evaluated?
    size = q_result.count()


    # delta[3] - how long to evaluate query
    step_in_time(ts_deltas)


    # hard limit for response
    if size > CATCH_RESPONSE_LIMIT:
        q_result = q_result[:CATCH_RESPONSE_LIMIT]
        size = q_result.count()

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
        logger.info(('[SEARCH_TIME] (prep, eval, format, total) '
                     '{0:12.3f} {1:12.3f} {2:12.3f} {3:12.3f}').format(
                         (ts_deltas[1][1].total_seconds()),
                         (ts_deltas[3][1].total_seconds()),
                         (ts_deltas[5][1].total_seconds()),
                         (datetime.utcnow() - ts_deltas[0][0]).total_seconds()))


    response['total'] = total  # add response info
    response['limit'] = limit
    response['offset'] = offset
    return response


def process_search_params(request, query):
    usernames = request.GET.getlist('username', [])
    if usernames:
        query = query.filter(query_username(usernames))

    userids = request.GET.getlist('userid', [])
    if userids:
        query = query.filter(query_userid(userids))

    tags = request.GET.getlist('tag', [])
    if tags:
        query = query.filter(query_tags(tags))

    targets = request.GET.get('target_source', [])
    if targets:
        query = query.filter(query_target_sources(targets))

    medias = request.GET.getlist('media', [])
    if medias:
        mlist = [x.capitalize() for x in medias]
        query = query.filter(query_target_medias(mlist))

    text = request.GET.get('text', [])
    if text:
        query = query.filter(body_text__search=text)

    # custom searches for platform params
    q = Anno.custom_manager.search_expression(request.GET)

    if q:
        query = query.filter(q)

    return query


def process_search_back_compat_params(request, query):
    target = request.GET.get('uri', None)
    if target:
        query = query.filter(raw__platform__target_source_id=target)

    medias = request.GET.getlist('media', [])
    if medias:
        if 'comment' in medias:
            medias.remove('comment')
            medias.append('Annotation')

        mlist = [x.capitalize() for x in medias]
        query = query.filter(query_target_medias(mlist))

    # search by quote?

    text = request.GET.get('text', [])
    if text:
        query = query.filter(body_text__search=text)

    userids = request.GET.getlist('userid', [])
    if userids:
        query = query.filter(query_userid(userids))

    usernames = request.GET.getlist('username', [])
    if usernames:
        query = query.filter(query_username(usernames))

    source = request.GET.get('source', None)
    if source:
        query = query.filter(query_target_sources([source]))

    context_id = request.GET.get('contextId', None)
    if context_id is None:  # forward-compat!!! see [1] at the bottom
        context_id = request.GET.get('context_id', None)
    if context_id:
        query = query.filter(raw__platform__context_id=context_id)

    collection_id = request.GET.get('collectionId', None)
    if collection_id is None:  # forward-compat!!! see [1] at the bottom
        collection_id = request.GET.get('collection_id', None)
    if collection_id:
        query = query.filter(raw__platform__collection_id=collection_id)

    parent_id = request.GET.get('parentid', None)
    if parent_id:
        query = query.filter(anno_reply_to__anno_id=parent_id)

    tags = request.GET.getlist('tag', [])
    if tags:
        query = query.filter(query_tags(tags))

    return query


@require_http_methods('POST')
@csrf_exempt
@require_catchjwt
def copy_api(request):

    # check permissions to copy
    jwt_payload = get_jwt_payload(request)
    if 'CAN_COPY' not in jwt_payload['override']:
        raise NoPermissionForOperationError(
            'user ({}) not allowed to copy'.format(jwt_payload['name']))

    params = get_input_json(request)

    # sanity check: not allowed to copy to same course or collection
    if params['source_context_id'] == params['target_context_id']:
        raise InconsistentAnnotationError(
            'not allowed to copy to same context_id({})'.format(
                params['source_context_id']))

    back_compat = params['back_compat'] if 'back_compat' in params else False

    userids = params['userid_list'] if 'userid_list' in params else None
    usernames = params['username_list'] if 'username_list' in params else None
    anno_list = CRUD.select_for_copy(
            context_id=params['source_context_id'],
            collection_id=params['source_collection_id'],
            platform_name=params['platform_name'],
            userid_list=userids,
            username_list=usernames)

    logger.debug('select for copy returned ({})'.format(anno_list.count()))

    resp = CRUD.copy_annos(
        anno_list,
        params['target_context_id'], params['target_collection_id'],
        back_compat=back_compat)

    return JsonResponse(status=HTTPStatus.OK, data=resp)



def process_partial_update(request, anno_id):
    # assumes request.method == PUT
    return {
        'status': HTTPStatus.NOT_IMPLEMENTED,
        'payload': ['partial update not implemented.']}

    # retrieve anno

    # request user can update this?

    # validates -- no formatting here

    # performs update and save to database

    # needs formatting?
    pass


@require_http_methods(['POST', 'GET'])
@csrf_exempt
@require_catchjwt
def create_or_search(request):
    '''view for create, with no anno_id in querystring.'''
    if request.method == 'POST':
        anno_id = generate_uid()
        return crud_api(request, anno_id)
    else:  # it's a GET
        return search_api(request)


@require_http_methods('POST')
@csrf_exempt
@require_catchjwt
def crud_compat_create(request):
    '''view for create, with no anno_id in querystring.'''
    must_be_int = True
    anno_id = generate_uid(must_be_int)
    return crud_compat_api(request, anno_id)


@require_http_methods('DELETE')
@csrf_exempt
@require_catchjwt
def crud_compat_delete(request, anno_id):
    '''back compat view for delete.'''
    return crud_compat_api(request, anno_id)


@require_http_methods('GET')
@csrf_exempt
@require_catchjwt
def crud_compat_read(request, anno_id):
    '''back compat view for read.'''
    return crud_compat_api(request, anno_id)


@require_http_methods('POST')
@csrf_exempt
@require_catchjwt
def crud_compat_update(request, anno_id):
    '''back compat view for update.'''
    try:
        resp = _do_crud_compat_update(request, anno_id)
        status = HTTPStatus.OK
        response = JsonResponse(status=status, data=resp)

        # add response header with location for new resource
        response['Location'] = request.build_absolute_uri(
            reverse('compat_read', kwargs={'anno_id': resp['id']}))
        return response

    except AnnoError as e:
        return JsonResponse(status=e.status,
                            data={'status': e.status, 'payload': [str(e)]})

    except (ValueError, KeyError) as e:
        logger.error('anno({}): bad input:'.format(anno_id), exc_info=True)
        return JsonResponse(
            status=HTTPStatus.BAD_REQUEST,
            data={'status': HTTPStatus.BAD_REQUEST, 'payload': [str(e)]})


def _do_crud_compat_update(request, anno_id):
    # retrieves anno
    anno = CRUD.get_anno(anno_id)

    if anno is None:
        raise MissingAnnotationError('anno({}) not found'.format(anno_id))

    if not has_permission_for_op('update', request, anno):
        raise NoPermissionForOperationError(
            'no permission to {} anno({}) for user({})'.format(
                METHOD_PERMISSION_MAP[request.method], anno_id,
                request.catchjwt['userId']))

    r = process_update(request, anno)
    response_format = ANNOTATORJS_FORMAT
    return _format_response(r, response_format)

"""
[1] got rid of camelCase in v2 for uniformity, so contextId is not allowed.
    BUT, it might be that users want to set `context-id` in back-compat
    searches... i did this in performance test and was thrown out by having the
    whole db as result. In back-compat having a search return everythin will
    cause problems because of the anno_id: in back-compat it must be an
    integer.
"""
