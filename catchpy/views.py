from http import HTTPStatus

from django.conf import settings
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from anno.models import Tag
from . import __version__

import logging

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
def simplest_is_alive(request):
    rows = Tag.objects.all()[:1]
    return JsonResponse(
        status=HTTPStatus.OK,
        data={'status': HTTPStatus.OK,
              'payload': ['ok', 'query is {}'.format(len(rows))]}
    )


@require_http_methods(['GET'])
@csrf_exempt
def wait_is_alive(request):
    rows = Tag.objects.all()
    try:
        x = len(Tag.objects.all())
    except Error as e:
        return JsonResponse(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
                data={'status': HTTPStatus.INTERNAL_SERVER_ERROR,
                      'payload': ['db default error: {}'.format(e)]}
        )

    else:
        return JsonResponse(
            status=HTTPStatus.OK,
            data={'status': HTTPStatus.OK, 'payload': ['ok']}
        )

    return JsonResponse(
        status=HTTPStatus.NOT_FOUND,
            data={'status': HTTPStatus.NOT_FOUND,
                    'payload': ['unknown  error']}
    )





@require_http_methods(['GET'])
@csrf_exempt
def is_alive(request):
    logging.getLogger(__name__).info('in is alive')
    logging.getLogger(__name__).info(
        'in is alive -- {}'.format(connections['default']))
    if getattr(connections['default'], 'introspection') is not None:
        logging.getLogger(__name__).info('INTROSPECTION IS OK')
    else:
        logging.getLogger(__name__).info('no introspection')
    myclass = connections['default'].introspection.__class__
    logging.getLogger(__name__).info('class is {}'.format(myclass.__name__))
    classdir = dir(myclass)
    logging.getLogger(__name__).info('classdir is {}'.format(classdir))

    property_names=[p for p in dir(myclass) if
                    callable(getattr(myclass,p))]
    logging.getLogger(__name__).info('properties: {}'.format(property_names))

    try:
        if callable(connections['default'].introspection.table_names):
            logging.getLogger(__name__).info('table_names IS CALLABLE')
    except Error as e:
        logging.getLogger(__name__).error('ERROR: {}'.format(e))


    try:
        connections['default'].introspection.table_names()
        logging.getLogger(__name__).info('after connections')
    except Error as e:
        logging.getLogger(__name__).info(
            'introspection exception db{}: {}'.format(database, e))

        return JsonResponse(
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
                data={'status': HTTPStatus.INTERNAL_SERVER_ERROR,
                      'payload': ['db "default" error: {}'.format(e)]}
            )
    else:
        logging.getLogger(__name__).info("after introspection")
        return JsonResponse(
            status=HTTPStatus.OK,
            data={'status': HTTPStatus.OK, 'payload': ['ok']}
        )




