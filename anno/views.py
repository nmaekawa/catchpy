from django.http import HttpResponse
from django.shortcuts import render

from anno.db_utils import create_db
from anno.db_utils import populate_docstore
from anno.db_utils import search_docstore


def index(request):
    return HttpResponse('Hello you. This is the annotation sample.')


def docstore(request):
    # populate_docstore('wa_sample.json')
    search_docstore()
    return(HttpResponse('Hi this is the docstore page.'))


def postgres(request):
    create_db('annotatorjs_sample.json')
    return(HttpResponse('OH! A postgres page!'))

