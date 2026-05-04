"""Файл со всеми формами для core"""
from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import User


class EditProfileForm(UserChangeForm):
    """Форма для изменения информации о пользователе"""
    username = forms.CharField(
        max_length=30,
        label='Никнейм/логин',
        required=True,
        help_text='Ваше имя в нашей системе',
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        label='Имя',
        help_text='Ваше имя(необязательно)',
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        label='Фамилия',
        help_text='Ваша фамилия(необязательно)',
    )
    email = forms.EmailField(
        label='Эл. почта',
        required=True,
        help_text='На нее будут приходить уведомления',
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
