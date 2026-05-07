"""Файл со всеми формами для core"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User


class EditProfileForm(forms.ModelForm):
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


class CustomLoginForm(AuthenticationForm):
    """Форма входа с кастомными CSS-классами и плейсхолдерами"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя пользователя',
            'id': 'InputUsername'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль',
            'id': 'InputPassword'
        })
    )


class CustomRegistrationForm(UserCreationForm):
    """Форма регистрации без лишней валидации уникальности email"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя пользователя',
            'id': 'InputName'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Электронная почта',
            'id': 'InputEmail'
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль',
            'id': 'InputPassword1'
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Подтверждение пароля',
            'id': 'InputPassword2'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        return self.cleaned_data.get('email')


class CustomPasswordChangeForm(PasswordChangeForm):
    """Форма смеены пароля"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Введите старый пароль',
            'autocomplete': 'current-password'
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Новый пароль (мин. 8 символов)',
            'autocomplete': 'new-password'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Подтвердите новый пароль',
            'autocomplete': 'new-password'
        })
