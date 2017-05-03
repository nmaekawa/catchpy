
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render

from anno.db_utils import create_db
from anno.db_utils import populate_db
from anno.db_utils import queryset_username
from anno.db_utils import queryset_userid
from anno.db_utils import queryset_tags
from anno.db_utils import queryset_target_medias
from anno.db_utils import queryset_target_sources
from anno.models import Anno

import pdb

def index(request):
    return HttpResponse('Hello you. This is the annotation sample.')


def docstore(request):
    # populate_docstore('wa_sample.json')
    search_docstore()
    return(HttpResponse('Hi this is the docstore page.'))


def postgres(request):
    #create_db('annotatorjs_sample.json')
    populate_db('wa2-dev-mille.json')
    return(HttpResponse('OH! A postgres page!'))


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



