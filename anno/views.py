from django.http import HttpResponse
from django.shortcuts import render

from anno.db_utils import create_db


def index(request):
    return HttpResponse('Hello you. This is the annotation sample.')


def mongo(request):
    return(HttpResponse('Hi this is the mongo page.'))


def postgres(request):
    create_db('annotatorjs_sample.json')
    return(HttpResponse('OH! A postgres page!'))

