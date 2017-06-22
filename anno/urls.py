from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^search', views.search_api, name='search_api'),
    url(r'^create$', views.crud_compat_create, name='crud_create'),
    url(r'^update/(?P<anno_id>[0-9a-zA-z-]+)$', views.crud_api, name='crud_update'),
    url(r'^delete/(?P<anno_id>[0-9a-zA-z-]+)$', views.crud_api, name='crud_delete'),
    url(r'^(?P<anno_id>[0-9a-zA-z-]+)$', views.crud_api, name='crud_api'),
    url(r'^', views.search_api, name='search_api'),
]
