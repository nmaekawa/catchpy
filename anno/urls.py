from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.crud_create, name='crud_create'),
    url(r'^info$', views.index, name='index'),
    url(r'^search', views.search_api, name='search_api'),
    url(r'^create$', views.crud_create, name='compat_create'),
    url(r'^update/(?P<anno_id>[0-9a-zA-z-]+)$',
        views.crud_compat_update, name='compat_update'),
    url(r'^delete/(?P<anno_id>[0-9a-zA-z-]+)$', views.crud_api, name='compat_delete'),
    url(r'^(?P<anno_id>[0-9a-zA-z-]+)$', views.crud_api, name='crud_api'),
    url(r'^.+$', views.search_api, name='search_api_clear'),
]
