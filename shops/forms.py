from django import forms


class ShopLoginForm(forms.Form):
    """Sign-in form for the seller channel. Django handles the actual login."""

    username = forms.CharField(
        label='Tên tài khoản', max_length=254, required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'username', 'autofocus': True}),
    )
    password = forms.CharField(
        label='Mật khẩu', required=True,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )
