"""Файл со всеми путями приложения"""
from django.urls import path
from django.contrib.auth.views import LogoutView, LoginView

from core.forms import CustomLoginForm, CustomRegistrationForm
from .views import (query_search, url_search, product_offers, edit_profile, register,
                    FavoritesView, ProfileView, SettingsView,)


urlpatterns = [
    path('query_search', query_search, name='query_search'),
    path('url_search', url_search, name='url_search'),
    path('product/<slug:slug>/offers', product_offers, name='product_offers'),
    path('favorites/<int:offer_id>', FavoritesView.as_view(), name='favorites'),
    path('profile', ProfileView.as_view(), name='profile'),
    path('edit_profile', edit_profile, name='edit_profile'),
    path('settings', SettingsView.as_view(), name='settings'),
    path('login/', LoginView.as_view(
        template_name='core/auth.html',
        authentication_form=CustomLoginForm,
        extra_context={
            'login_form': CustomLoginForm(),
            'register_form': CustomRegistrationForm(),
            'register_mode': False,
        },
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', LogoutView.as_view(next_page='hunter'), name='logout'),
    path('register/', register, name='register'),
]

"""
    path('edit_password', edit_password, name='edit_password'),
    path('', index, name='hunter'),
    path('instruction', instruction, name='instruction')
    path('delete_user', delete_user, name='delete_user')"""
