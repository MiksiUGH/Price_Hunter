"""Файл со всеми путями приложения"""
from django.urls import path
from .views import query_search, url_search, product_offers


urlpatterns = [
    path('query_search', query_search, name='query_search'),
    path('url_search', url_search, name='url_search'),
    path('product/<slug:slug>/offers', product_offers, name='product_offers'),
]

"""
    path('profile', ProfileView(), name='profile'),
    path('favorites/<int:offer_id>', FavoritesView(), name='favorites'),
    path('login', login, name='login'),
    path('logout', logout, name='logout'),
    path('register', register, name='register'),
    path('settings', SettingsView(), name='settings'),
    path('edit_password', edit_password, name='edit_password'),
    path('', index, name='hunter'),
    path('instruction', instruction, name='instruction')"""
