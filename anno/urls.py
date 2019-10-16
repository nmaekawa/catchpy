from django.urls import path
from django.urls import re_path

from . import views

urlpatterns = [
    # these are for back-compat
    re_path(r'^search', views.search_back_compat_api, name='compat_search'),
    re_path(r'^create$', views.crud_compat_create, name='compat_create'),
    re_path(r'^update/(?P<anno_id>[0-9]+)$',
        views.crud_compat_update, name='compat_update'),
    re_path(r'^delete/(?P<anno_id>[0-9]+)$',
        views.crud_compat_delete, name='compat_delete'),
    re_path(r'^read/(?P<anno_id>[0-9]+)$',
        views.crud_compat_read, name='compat_read'),

    # these are for catchpy v2
    re_path(r'^copy', views.copy_api, name='copy_api'),
    re_path(r'^(?P<anno_id>[0-9a-zA-z-]+)/?$', views.crud_api, name='crud_api'),
    re_path(r'^$', views.create_or_search, name='create_or_search'),
]
