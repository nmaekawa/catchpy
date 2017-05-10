from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^(?P<anno_id>[0-9a-zA-z-]+)$', views.simple_api, name='api'),
    url(r'^postgres/', views.postgres, name='postgres'),
    url(r'^search/', views.search, name='search'),
]
