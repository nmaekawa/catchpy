from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^import', views.stash, name='import'),
    url(r'^search', views.search_api, name='searchapi'),
    url(r'^(?P<anno_id>[0-9a-zA-z-]+)$', views.crud_api, name='crudapi'),
]
