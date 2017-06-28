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
from .anno_defaults import CATCH_RESPONSE_FORMATS
from .anno_defaults import CATCH_EXTRA_RESPONSE_FORMATS
from .anno_defaults import CATCH_RESPONSE_FORMAT_HTTPHEADER


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
        # TODO: REMOVE FAKE
        return {
            'userId': '123456789',
            'consumerKey': 'abc',
            'issuedAt': datetime.now(dateutil.tz.tzutc).replace(
                microsecond=0).isoformat(),
            'ttl': 60,
            'override': [],
            'error': '',
            'consumer': None,
        }


def get_default_permissions_for_user(user):
    return {
        'can_read': [],
        'can_update': [user],
        'can_delete': [user],
        'can_admin': [user],
    }


def get_input_json(request):
    if request.body:
        return json.loads(request.body)
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
        status = HTTPStatus.OK
        response = JsonResponse(status=status, data=resp)

        if request.method == 'POST' or request.method == 'PUT':
            # add response header with location for new resource
            response['Location'] = request.build_absolute_uri(
                reverse('crud_api', kwargs={'anno_id': resp['id']}))
        return response

    except AnnoError as e:
        return JsonResponse(status=e.status,
                            data={'status': e.status, 'payload': [str(e)]})

    except (ValueError, KeyError) as e:
        logger.error('anno({}): bad input:'.format(anno_id), exc_info=True)
        return JsonResponse(
            status=HTTPStatus.BAD_REQUEST,
            data={'status': HTTPStatus.BAD_REQUEST, 'payload': [str(e)]})


def has_permission_for_op(op, request, anno):
    # backward-compat
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

    response_format = fetch_response_format(request)
    return _format_response(r, response_format)



def fetch_response_format(request):
    response_format = getattr(settings, 'CATCH_RESPONSE_FORMAT', CATCH_ANNO_FORMAT)
    if CATCH_RESPONSE_FORMAT_HTTPHEADER in request.META:
        response_format = request.META[CATCH_RESPONSE_FORMAT_HTTPHEADER]
    return response_format


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
            # unknown format or plug custom formatters!
            raise UnknownResponseFormatError(
                'unknown response format({})'.format(response_format))
    else:  # assume it's a QuerySet resulting from search
        response = {
             'rows': [],
        }
        if response_format == ANNOTATORJS_FORMAT:
            for anno in anno_result:
                annojs = AnnoJS.convert_from_anno(anno)
                response['rows'].append(annojs)
        elif response_format == CATCH_ANNO_FORMAT:
            # doesn't need formatting! SERIALIZE as webannotation
            for anno in anno_result:
                response['rows'].append(anno.serialized)
        else:
            # unknown format or plug custom formatters!
            raise UnknownResponseFormatError(
                'unknown response format({})'.format(response_format))

    return response


def partial_update_api(request, anno_id):
    pass


@require_http_methods(['GET', 'HEAD', 'POST'])
@csrf_exempt
@require_catchjwt
def search_api(request):
    # accepts POST for backward-compat
    logger.debug('search query=({})'.format(request.GET))
    try:
        resp = _do_search_api(request)
        logger.debug('search response({})'.format(resp))
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



def _do_search_api(request):

    payload = request.catchjwt
    logger.debug('_do_search payload[userid]=({})'.format(payload['userId']))

    # filter out the soft-deleted
    query = Anno._default_manager.filter(anno_deleted=False)

    # TODO: check override POLICIES (override allow private reads)
    if 'CAN_READ' not in payload.get('override', []):
        # filter out permission cannot_read
        q = Q(can_read__len=0) | Q(can_read__contains=[payload['userId']])
        query = query.filter(q)

    usernames = request.GET.getlist('username', [])
    if usernames:
        #unames = [x.strip() for x in usernames.split(',')]
        query = query.filter(query_username(usernames))

    userids = request.GET.getlist('userid', [])
    if userids:
        query = query.filter(query_userid(userids))

    tags = request.GET.getlist('tag', [])
    if tags:
        query = query.filter(query_tags(tags))

    # back-compat
    targets = request.GET.get('uri', [])
    if not targets:
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
    q = Anno.custom_manager.search_expression(request.GET)

    if q:
        query = query.filter(q)

    # sort by created date
    query = query.order_by('created')

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
    total = query.count()      # is it here when the querysets are evaluated?
    size = q_result.count()

    response_format = fetch_response_format(request)
    logger.debug('default_format({})'.format(getattr(settings,
                                                     'CATCH_RESPONSE_FORMAT',
                                                     CATCH_ANNO_FORMAT)))
    logger.debug('response_format({})'.format(response_format))
    response = _format_response(q_result, response_format)
    response['total'] = total  # add response info
    response['size'] = size
    response['limit'] = limit
    response['offset'] = offset
    return response


@require_http_methods('GET')
@csrf_exempt
def index(request):
    # TODO: return info on the api
    return HttpResponse('placeholder for api docs. soon.')


@require_http_methods('GET')
@csrf_exempt
@require_catchjwt
def stash(request):
    filepath = request.GET.get('filepath', None)
    if filepath:
        with open(filepath, 'r') as fh:
            data = fh.read()
        catcha_list = json.loads(data)

    payload = get_jwt_payload(request)
    try:
        resp = CRUD.import_annos(catcha_list, payload)
        return JsonResponse(status=HTTPStatus.OK, data=resp)

    except AnnoError as e:
        return JsonResponse(status=e.status,
                            data={'status': e.status, 'payload': [str(e)]})

    except (ValueError, KeyError) as e:
        logger.error('bad input: requuest({})'.format(request), exc_info=True)
        return JsonResponse(
            status=HTTPStatus.BAD_REQUEST,
            data={'status': HTTPStatus.BAD_REQUEST, 'payload': [str(e)]})



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


@require_http_methods('POST')
@csrf_exempt
@require_catchjwt
def crud_create(request):
    '''view for create, with no anno_id in querystring.'''
    must_be_int = request.path.startswith('/create')  # backward-compat
    anno_id = generate_uid(must_be_int)
    return crud_api(request, anno_id)


@require_http_methods('POST')
@csrf_exempt
@require_catchjwt
def crud_compat_update(request):
    '''back compat view for update.'''
    try:
        resp = _do_crud_compat_update(request, anno_id)
        status = HTTPStatus.OK
        response = JsonResponse(status=status, data=resp)

        # add response header with location for new resource
        response['Location'] = request.build_absolute_uri(
            reverse('crud_api', kwargs={'anno_id': resp['id']}))
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

    if not has_permission_for_op(
            METHOD_PERMISSION_MAP[request.method], request, anno):
        raise NoPermissionForOperationError(
            'no permission to {} anno({}) for user({})'.format(
                METHOD_PERMISSION_MAP[request.method], anno_id,
                request.catchjwt['userId']))

        r = process_update(request, anno)

    assert r is not None

    response_format = fetch_response_format(request)
    return _format_response(r, response_format)
