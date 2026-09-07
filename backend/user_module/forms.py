from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="نام کاربری",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-dark',
            'placeholder': 'نام کاربری خود را وارد کنید',
            'autofocus': True,
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        label="کلمه عبور",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-dark',
            'placeholder': 'کلمه عبور خود را وارد کنید',
            'autocomplete': 'current-password',
        })
    )

    error_messages = {
        'invalid_login': 'نام کاربری یا کلمه عبور وارد شده نادرست است.',
        'inactive': 'این حساب کاربری غیرفعال است.',
    }
