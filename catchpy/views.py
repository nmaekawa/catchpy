from http import HTTPStatus

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from anno.errors import AnnoError
from . import __version__
from anno.models import Anno


@require_http_methods(['GET', 'HEAD'])
@csrf_exempt
def app_version(request):
    '''return the current version of this project.'''
    response = JsonResponse(
        status=HTTPStatus.OK,
        data={'version': __version__},
    )

    return response


@require_http_methods(['GET'])
@csrf_exempt
def is_alive(request):

    try:
        # TODO: queryset is NOT being evaluated, so useless check for db conn
        result = Anno._default_manager.all()[:1]
    except AnnoError as e:
        return JsonResponse(
            status=e.status,
            data={'status': e.status, 'payload': str(e)})
    else:
        return JsonResponse(
            status=HTTPStatus.OK,
            data={'status': HTTPStatus.OK, 'payload': 'db access ok'})



