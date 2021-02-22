import logging
from http import HTTPStatus

from anno.decorators import require_catchjwt
from django.conf import settings
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import __version__


@require_http_methods(["GET", "HEAD"])
@csrf_exempt
def app_version(request):
    """return the current version of this project."""
    response = JsonResponse(
        status=HTTPStatus.OK,
        data={"version": __version__},
    )
    return response


@require_http_methods(["GET"])
@csrf_exempt
@require_catchjwt
def is_alive(request):
    # if has a valid jwt, then accessed db to check consumer key
    response = JsonResponse(
        status=HTTPStatus.OK, data={"status": HTTPStatus.OK, "payload": ["ok"]}
    )
    return response
