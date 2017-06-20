from datetime import datetime
import dateutil
from functools import wraps
import json
import logging
from uuid import uuid4

from django.db.models import Q
from django.conf import settings
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from http import HTTPStatus

from catchformats.catch_webannotation_validator import \
    validate_format_catchanno as validate_input
from catchformats.errors import CatchFormatsError
from catchformats.errors import AnnotatorJSError

from .annojs import anno_to_annotatorjs
from .crud import CRUD
from .errors import AnnoError
from .errors import InvalidAnnotationCreatorError
from .errors import DuplicateAnnotationIdError
from .errors import MethodNotAllowedError
from .errors import MissingAnnotationError
from .errors import MissingAnnotationInputError
from .errors import NoPermissionForOperationError
from .errors import UnknownOutputFormatError
from .search import query_username
from .search import query_userid
from .search import query_tags
from .search import query_target_medias
from .search import query_target_sources
from .models import Anno


SCHEMA_VERSION = 'catch_v1.0'
CATCH_CONTEXT_IRI = 'http://catch-dev.harvardx.harvard.edu/catch-context.jsonld'
ANNOTATORJS_CONTEXT_IRI = 'http://annotatorjs.org'

CATCH_ANNO_FORMAT = 'CATCH_ANNO_FORMAT'
ANNOTATORJS_FORMAT = 'ANNOTATORJS_FORMAT'
OUTPUT_FORMATS = [CATCH_ANNO_FORMAT, ANNOTATORJS_FORMAT]
CATCH_OUTPUT_FORMAT_HTTPHEADER = 'HTTP_X_CATCH_OUTPUT_FORMAT'

METHOD_PERMISSION_MAP = {
    'GET': 'read',
    'HEAD': 'read',
    'DELETE': 'delete',
    'PUT': 'update',
}

logger = logging.getLogger(__name__)


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

    # fill info for create-anno
    requesting_user = request.catchjwt['userId']
    a_input['id'] = anno_id
    if 'permissions' not in a_input:
        a_input['permissions'] = get_default_permissions_for_user(
            requesting_user)
    if 'schema_version' not in a_input:
        a_input['schema_version'] = SCHEMA_VERSION

    # throws CatchFormatsError, AnnotatorJSError
    catcha = validate_input(a_input)

    # check for conflicts
    if catcha['creator']['id'] != requesting_user:
        raise InvalidAnnotationCreatorError(
            ('anno({}) conflict in input creator_id({}) does not match '
                'requesting_user({}) - not created').format(
                    anno_id, catcha['creator']['id'], requesting_user))

    # TODO: check if creator in permissions
    # TODO: check if reply to itself
    # TODO: check if annotation in targets if reply

    # throws AnnoError
    anno = CRUD.create_anno(catcha)
    return anno


def process_update(request, anno):
    # throws MissingAnnotationInputError
    a_input = get_input_json(request)

    # throws CatchFormatsERror, AnnotatorJSError
    catcha = validate_input(a_input)

    # check if trying to update permissions
    requesting_user = request.catchjwt['userId']
    if not CRUD.is_identical_permissions(catcha, anno.raw):
        if requesting_user not in anno.can_admin \
                and 'CAN_ADMIN' not in request.catchjwt['override']:
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

        if request.method == 'POST' or request.method == 'PUT':
            status = HTTPStatus.SEE_OTHER

        # add response header with location for new resource
        response = JsonResponse(status=status, data=resp)
        response['Location'] = request.build_absolute_uri(
            reverse('crudapi', kwargs={'anno_id': resp['id']}))

        logger.debug('*************** return response status code ({})'.format(
            response.status_code))


        return response

    except AnnoError as e:
        return JsonResponse(status=e.status,
                            data={'status': e.status, 'payload': [str(e)]})

    except (CatchFormatsError, AnnotatorJSError) as e:
        return JsonResponse(
            status=HTTPStatus.BAD_REQUEST,
            data={'status': HTTPStatus.BAD_REQUEST, 'payload': [str(e)]})

    except (ValueError, KeyError) as e:
        logger.error('anno({}): bad input:'.format(anno_id), exc_info=True)
        return JsonResponse(
            status=HTTPStatus.BAD_REQUEST,
            data={'status': HTTPStatus.BAD_REQUEST, 'payload': [str(e)]})


def has_permission_for_op(request, anno):
    permission = METHOD_PERMISSION_MAP[request.method]
    if anno.has_permission_for(permission, request.catchjwt['userId']) \
       or 'CAN_{}'.format(permission).upper() in request.catchjwt['override']:
        return True
    else:
        return False


@require_http_methods('POST')
@csrf_exempt
@require_catchjwt
def c_crud(request):
    anno_id = uuid4()
    try:
        r = process_create(request, anno_id)
        resp = _response_for_single_anno(request, r)

        # add response header with location for new resource
        response = JsonResponse(status=HTTPStatus.OK, data=resp)
        response['Location'] = request.build_absolute_uri(
            reverse('crudapi', kwargs={'anno_id': resp['id']}))
        return response

    except AnnoError as e:
        logger.error('c_crud({}): {}'.format(anno_id, e, exc_info=True))
        return JsonResponse(status=e.status,
                            data={'status': e.status, 'payload': [str(e)]})

    except (CatchFormatsError, AnnotatorJSError) as e:
        logger.error('c_crud({}): {}'.format(anno_id, e, exc_info=True))
        return JsonResponse(
            status=HTTPStatus.BAD_REQUEST,
            data={'status': HTTPStatus.BAD_REQUEST, 'payload': [str(e)]})

    except (ValueError, KeyError) as e:
        logger.error('anno({}): bad input:'.format(anno_id), exc_info=True)
        return JsonResponse(
            status=HTTPStatus.BAD_REQUEST,
            data={'status': HTTPStatus.BAD_REQUEST, 'payload': [str(e)]})


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

        if not has_permission_for_op(request, anno):
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

    return _format_response(request, r)


def _response_for_single_anno(request, anno):
    # prep response
    output_format = getattr(settings, 'CATCH_OUTPUT_FORMAT', CATCH_ANNO_FORMAT)
    if CATCH_OUTPUT_FORMAT_HTTPHEADER in request.META:
        output_format = request.META[CATCH_OUTPUT_FORMAT_HTTPHEADER]

    if output_format == ANNOTATORJS_FORMAT:

        logger.debug(
            '****** about to respond in annotatorjs format({})'.format(
                anno.anno_id))

        payload = anno_to_annotatorjs(anno)

    elif output_format == CATCH_ANNO_FORMAT:
        # doesn't need formatting! SERIALIZE as webannotation
        payload = anno.serialized
    else:
        # unknown format or plug custom formatters!
        raise UnknownOutputFormatError('unknown output format({})'.format(
            output_format))
    return payload


def fetch_output_format(request):
    output_format = getattr(settings, 'CATCH_OUTPUT_FORMAT', CATCH_ANNO_FORMAT)
    if CATCH_OUTPUT_FORMAT_HTTPHEADER in request.META:
        output_format = request.META[CATCH_OUTPUT_FORMAT_HTTPHEADER]
    return output_format


def _format_response(anno_result, output_format):
    # is it single anno or a QuerySet from search?
    is_single = isinstance(anno_result, Anno)

    if is_single:
        if output_format == ANNOTATORJS_FORMAT:
            response = anno_to_annotatorjs(anno_result)
        elif output_format == CATCH_ANNO_FORMAT:
            # doesn't need formatting! SERIALIZE as webannotation
            response = anno_result.serialized
        else:
            # unknown format or plug custom formatters!
            raise UnknownOutputFormatError(
                'unknown output format({})'.format(output_format))
    else:  # assume it's a QuerySet resulting from search
        response = {
            'total': total,
             'size': size,
             'limit': limit,
             'offset': offset,
             'rows': [],
        }
        if output_format == ANNOTATORJS_FORMAT:
            for anno in anno_result:
                annojs = anno_to_annotatorjs(anno)
                response['rows'].append(annojs)
        elif output_format == CATCH_ANNO_FORMAT:
            # doesn't need formatting! SERIALIZE as webannotation
            for anno in q_result:
                response['rows'].append(anno.serialized)
        else:
            # unknown format or plug custom formatters!
            raise UnknownOutputFormatError(
                'unknown output format({})'.format(output_format))

    return response


def partial_update_api(request, anno_id):
    pass

@require_http_methods(['GET', 'DELETE', 'PUT', 'HEAD', 'POST'])
@csrf_exempt
def check(request):
    logger.error('--- checking: method({})'.format(request.method))
    logger.error('--- checking: request content ({})'.format(request.body))

    return JsonResponse(status=HTTPStatus.OK, data={'status': HTTPStatus.OK})


@require_http_methods(['GET', 'HEAD', 'POST'])
@csrf_exempt
@require_catchjwt
def search_api(request):
    try:
        resp = _do_search_api(request)
        return JsonResponse(status=HTTPStatus.OK, data=resp)

    except (CatchFormatsError, AnnotatorJSError) as e:
        return JsonResponse(
            status=HTTPStatus.BAD_REQUEST,
            data={'status': HTTPStatus.BAD_REQUEST, 'payload': [str(e)]})

    except Exception as e:
        logger.error('search failed; request({})'.format(request), exc_info=True)
        return JsonResponse(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            data={'status': HTTPStatus.INTERNAL_SERVER_ERROR, 'payload': [str(e)]})



def _do_search_api(request):

    payload = get_jwt_payload(request)

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

    # prep response
    response = {
        'total': total,
        'size': size,
        'limit': limit,
        'offset': offset,
        'rows': [],
    }

    output_format = getattr(settings, 'CATCH_OUTPUT_FORMAT', CATCH_ANNO_FORMAT)
    if CATCH_OUTPUT_FORMAT_HTTPHEADER in request.META:
        output_format = request.META[CATCH_OUTPUT_FORMAT_HTTPHEADER]

    if output_format == ANNOTATORJS_FORMAT:
        for anno in q_result:
            annojs = anno_to_annotatorjs(anno)
            response['rows'].append(annojs)

    elif output_format == CATCH_ANNO_FORMAT:
        # doesn't need formatting! SERIALIZE as webannotation
        for anno in q_result:
            response['rows'].append(anno.serialized)
    else:
        # unknown format
        raise UnknownOutputFormatError('unknown output format({})'.format(
            output_format))

    return response


@require_http_methods(['GET'])
def index(request):
    # TODO: return info on the api
    return HttpResponse('placeholder for api docs. soon.')


@require_http_methods(['GET'])
@csrf_exempt
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

    except (CatchFormatsError, AnnotatorJSError) as e:
        return JsonResponse(
            status=HTTPStatus.BAD_REQUEST,
            data={'status': HTTPStatus.BAD_REQUEST, 'payload': [str(e)]})

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
