from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^postgres/', views.postgres, name='postgres'),
    url(r'^docstore/', views.docstore, name='docstore'),
]
