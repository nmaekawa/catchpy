from django.conf.urls import url

from . import views

urlpatterns = [
    # these are for back-compat
    url(r'^search', views.search_back_compat_api, name='compat_search'),
    url(r'^create$', views.crud_compat_create, name='compat_create'),
    url(r'^update/(?P<anno_id>[0-9]+)$',
        views.crud_compat_update, name='compat_update'),
    url(r'^delete/(?P<anno_id>[0-9]+)$',
        views.crud_compat_delete, name='compat_delete'),
    url(r'^read/(?P<anno_id>[0-9]+)$',
        views.crud_compat_read, name='compat_read'),

    # these are for catchpy v2
    url(r'^copy', views.copy_api, name='copy_api'),
    url(r'^(?P<anno_id>[0-9a-zA-z-]+)$', views.crud_api, name='crud_api'),
    url(r'^$', views.create_or_search, name='create_or_search'),
]
