"""Файл со всеми путями приложения"""
from django.urls import path
from .views import query_search


urlpatterns = [
    path('query_search', query_search, name='query_search'),
]
