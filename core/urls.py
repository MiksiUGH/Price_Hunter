"""Файл со всеми путями приложения"""
from django.urls import path
from .views import query_search, url_search


urlpatterns = [
    path('query_search', query_search, name='query_search'),
    path('url_search', url_search, name='url_search'),
]

"""path('<slug:slug>/offers', product_offers, name='product_offers'),
    path('profile', profile, name='profile'),
    path('favorites/<int:id>', favorites, name='favorites'),
    path('login', login, name='login'),
    path('logout', logout, name='logout'),
    path('register', register, name='register'),
    path('settings', settings, name='settings'),
    path('edit_password', edit_password, name='edit_password'),
    path('', index, name='hunter'),
    path('instruction', instruction, name='instruction')"""
