from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth import get_user_model
from .models import Address

User = get_user_model()


class BuyerAddressForm(forms.ModelForm):
    receiver_name = forms.CharField(label='Người nhận', max_length=150, widget=forms.TextInput(attrs={'autocomplete': 'name'}))
    receiver_phone = forms.RegexField(
        label='Số điện thoại', regex=r'\A0[0-9]{9}\Z', max_length=10,
        error_messages={'invalid': 'Nhập số điện thoại gồm 10 chữ số, bắt đầu bằng 0.'},
        widget=forms.TextInput(attrs={'type': 'tel', 'autocomplete': 'tel-national', 'inputmode': 'tel', 'pattern': '0[0-9]{9}', 'placeholder': '0901234567'}),
    )
    province = forms.CharField(label='Tỉnh / thành phố', max_length=100, widget=forms.TextInput(attrs={'autocomplete': 'address-level1'}))
    district = forms.CharField(label='Quận / huyện (nếu có)', max_length=100, required=False)
    ward = forms.CharField(label='Phường / xã', max_length=100, widget=forms.TextInput(attrs={'autocomplete': 'address-level2'}))
    detail_address = forms.CharField(label='Số nhà, tên đường', max_length=255, widget=forms.TextInput(attrs={'autocomplete': 'street-address'}))
    is_default = forms.BooleanField(label='Đặt làm địa chỉ mặc định', required=False)

    class Meta:
        model = Address
        fields = ['receiver_name', 'receiver_phone', 'province', 'district', 'ward', 'detail_address', 'is_default']


class BuyerRegisterForm(forms.Form):
    full_name = forms.CharField(
        label='Username', max_length=100, required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'name', 'maxlength': '80'}),
    )
    email = forms.EmailField(
        label='Email', required=True,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )
    phone = forms.CharField(
        label='Số điện thoại (tùy chọn)', max_length=20, required=False,
        widget=forms.TextInput(attrs={'autocomplete': 'tel', 'pattern': '0[0-9]{9}', 'title': '10 chữ số, bắt đầu bằng 0'}),
    )
    password1 = forms.CharField(
        label='Mật khẩu (ít nhất 8 ký tự)', required=True, min_length=8,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Nhập lại mật khẩu', required=True, min_length=8,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )  
    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email đã được đăng ký.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Mật khẩu nhập lại không khớp.')
        if p1:
            try:
                password_validation.validate_password(p1)
            except forms.ValidationError as e:
                self.add_error('password1', e)
        phone = (cleaned.get('phone') or '').strip()
        if phone and not phone.replace(' ', '').isdigit():
            self.add_error('phone', 'Số điện thoại chỉ gồm chữ số.')
        return cleaned

    def save(self):
        email = self.cleaned_data['email'].strip().lower()
        user = User(
            username=email,  # dùng email làm username để tương thích AbstractUser
            email=email,
            full_name=self.cleaned_data['full_name'].strip(),
            phone=(self.cleaned_data.get('phone') or '').strip(),
            role='BUYER',
            status='INACTIVE',
        )
        user.set_password(self.cleaned_data['password1'])
        user.save()
        return user


class BuyerEmailOTPForm(forms.Form):
    code = forms.RegexField(
        label='Mã OTP',
        regex=r'\A[0-9]{6}\Z',
        max_length=6,
        error_messages={'invalid': 'Mã OTP phải gồm đúng 6 chữ số.'},
        widget=forms.TextInput(attrs={
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'maxlength': '6',
        }),
    )


class BuyerOTPEmailForm(forms.Form):
    email = forms.EmailField(
        label='Email đăng ký',
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )


class BuyerForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label='Email đăng ký',
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}),
    )

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()


class LoginForm(forms.Form):
    email = forms.CharField(
        label='Email', required=True, max_length=254,
        widget=forms.TextInput(attrs={'autocomplete': 'username'}),
    )
    password = forms.CharField(
        label='Mật khẩu', required=True,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )


class StaffLoginForm(forms.Form):
    """Admin sign-in form."""

    username = forms.CharField(
        label='Tên tài khoản', max_length=254, required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'username', 'autofocus': True}),
    )
    password = forms.CharField(
        label='Mật khẩu', required=True,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )
    remember_me = forms.BooleanField(label='Ghi nhớ đăng nhập', required=False)
    otp = forms.CharField(
        label='Mã OTP', max_length=6, required=False,
        widget=forms.TextInput(attrs={'autocomplete': 'one-time-code', 'inputmode': 'numeric', 'placeholder': '______'}),
    )


class StaffForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label='Email quản trị', required=True,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}),
    )


class StaffSetPasswordForm(forms.Form):
    password1 = forms.CharField(
        label='Mật khẩu mới (ít nhất 8 ký tự)', required=True, min_length=8,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'autofocus': True}),
    )
    password2 = forms.CharField(
        label='Nhập lại mật khẩu', required=True, min_length=8,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Mật khẩu nhập lại không khớp.')
        if p1:
            try:
                password_validation.validate_password(p1, user=self.user)
            except forms.ValidationError as error:
                self.add_error('password1', error)
        return cleaned


class BuyerSetPasswordForm(StaffSetPasswordForm):
    pass
