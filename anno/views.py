from django.db import transaction
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render

from anno.crud import CRUD
from anno.errors import AnnoError
from anno.import_anno import populate_db
from anno.search import queryset_username
from anno.search import queryset_userid
from anno.search import queryset_tags
from anno.search import queryset_target_medias
from anno.search import queryset_target_sources
from anno.models import Anno

import pdb

def index(request):
    # TODO: return info on the api
    return HttpResponse('Hello you. This is the annotation sample.')

@transaction.non_atomic_requests
def postgres(request):
    populate_db('wa2-dev-mille.json')
    return(HttpResponse('OH! A postgres page!'))


def make_response(data):
    return {
        'status': 200,
        'payload': data,
    }


def make_error_response(status, msg):
    return {
        'status': status,
        'payload': {'message': msg},
    }


method2function = {
    'GET': CRUD.read_anno,
    'POST': CRUD.create_anno,
    'PUT': CRUD.update_anno,
    'DELETE': CRUD.delete_anno,
}

error2status = {
    'AnnoError': 500,
    'DuplicateAnnotationIdError': 409,  # conflict
    'InvalidAnnotationBodyTypeError': 422,  # unprocessable entity
    'InvalidAnnotationPurposeError': 422,
    'InvalidAnnotationTargetTypeError': 422,
    'InvalidInputWebAnnotationError': 422,
    'InvalidTargetMediaTypeError': 422,
    'MissingAnnotationError': 404,
    'ParentAnnotationMissingError': 409,  # conflict
    'TargetAnnotationForReplyMissingError': 409,
}

def simple_api(request, anno_id):

    if request.method in method2function:
        try:
            a = method2function[request.method](anno_id, request=request)
            resp = make_response(a.raw)
        except AnnoError as e:
            error_name = e.__class__.__name__
            if error_name in error2status:
                status = error2status[error_name]
            else:
                status = 500
            resp = make_error_response(status, e.__str__())
        except Exception as e:
            resp = make_error_response(500, e.__str__())
        return JsonResponse(resp)
    else:
        return JsonResponse(make_error_response(
            405, 'method({}) not allowed'.format(request.method)))

# check what format the input is: webannotation, iiif, annotatorjs
# and transform, or validate

# check what format the response should be and transform



def search(request):

    #
    # TODO: error in any of these queries should cancel the search????
    #

    query = Anno.objects.all()

    usernames = request.GET.get('username', [])
    if usernames:
        query = query.filter(queryset_username(usernames))

    userids = request.GET.get('userid', [])
    if userids:
        query = query.filter(queryset_userid(userids))

    tags = request.GET.get('tags', [])
    if tags:
        query = query.filter(queryset_tags(tags))

    targets = request.GET.get('target_source', [])
    if targets:
        query = query.filter(queryset_target_sources(targets))

    medias = request.GET.get('media', [])
    if medias:
        query = query.filter(queryset_target_medias(medias))

    text = request.GET.get('text', [])
    if text:
        query = query.filter(body_text__search=text)

    # particular to each platform
    if 'platform' in request.GET:
        # TODO:
        # to check if method exists: http://stackoverflow.com/a/7580687
        # and check for exceptions...
        q = Anno.platform_manager.search_filter(request.GET)
        query = query.filter(q)
    """
    platform_name = request.GET.get('platform', [])
    if platform_name:
        query = query.filter(raw__platform__platform_name=platform_name)

        context_id = request.GET.get('contextId', [])
        if context_id:
            query = query.filter(raw__platform__context_id=context_id)

            collection_id = request.GET.get('collectionId', [])
            if collection_id:
                query = query.filter(raw__platform__collection_id=collection_id)

        target_source_id = request.GET.get('sourceId', [])
        if target_source_id:
            try:
                target_source_id = int(target_source_id)
            except ValueError:  # when source_id is an actual url
                target_source_d = str(target_source_id)
            query = query.filter(raw__platform__target_source_id=target_source_id)
    """


    return(HttpResponse(query))



