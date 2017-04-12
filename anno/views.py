from django.http import HttpResponse
from django.shortcuts import render

from anno.db_utils import create_db

def index(request):
    create_db('annotatorjs_sample.json')
    return HttpResponse('Hello you. This is the annotation sample.')
