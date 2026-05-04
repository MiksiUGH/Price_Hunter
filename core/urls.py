"""Файл со всеми путями приложения"""
from django.urls import path
from .views import query_search, url_search, product_offers, edit_profile, FavoritesView, ProfileView


urlpatterns = [
    path('query_search', query_search, name='query_search'),
    path('url_search', url_search, name='url_search'),
    path('product/<slug:slug>/offers', product_offers, name='product_offers'),
    path('favorites/<int:offer_id>', FavoritesView.as_view(), name='favorites'),
    path('profile', ProfileView.as_view(), name='profile'),
    path('edit_profile', edit_profile, name='edit_profile')
]

"""path('login', login, name='login'),
    path('logout', logout, name='logout'),
    path('register', register, name='register'),
    path('settings', SettingsView(), name='settings'),
    path('edit_password', edit_password, name='edit_password'),
    path('', index, name='hunter'),
    path('instruction', instruction, name='instruction')
    path('delete_user', delete_user, name='delete_user')"""
