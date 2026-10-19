from django import forms
from django.contrib.auth import get_user_model, password_validation

from .models import Shop

User = get_user_model()


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


class SellerRegisterForm(forms.Form):
    """Step 1: seller account. Username and email must be unique; password strong."""

    username = forms.CharField(
        label='Tên đăng nhập', max_length=150, required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'username', 'autofocus': True}),
    )
    email = forms.EmailField(
        label='Email', required=True,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )
    password1 = forms.CharField(
        label='Mật khẩu (ít nhất 8 ký tự)', required=True, min_length=8,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Xác nhận mật khẩu', required=True, min_length=8,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Tên đăng nhập đã được sử dụng.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email đã được đăng ký.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Mật khẩu xác nhận không khớp.')
        if p1:
            try:
                password_validation.validate_password(p1)
            except forms.ValidationError as error:
                self.add_error('password1', error)
        return cleaned

    def save(self):
        return User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1'],
            full_name=self.cleaned_data['username'],
            role='SELLER',
            status='ACTIVE',
        )


class PhoneOTPForm(forms.Form):
    """Step 2b: phone OTP. The code is stored in the session, not in the database."""

    phone = forms.CharField(
        label='Số điện thoại', max_length=20, required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'tel', 'inputmode': 'numeric'}),
    )
    code = forms.CharField(
        label='Mã OTP', max_length=6, required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'one-time-code', 'inputmode': 'numeric'}),
    )

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if not phone.replace(' ', '').isdigit():
            raise forms.ValidationError('Số điện thoại chỉ gồm chữ số.')
        return phone


class ShopProfileForm(forms.ModelForm):
    """Step 3: shop profile. Shop name must be unique."""

    class Meta:
        model = Shop
        fields = ['shop_name', 'address', 'phone', 'description', 'logo']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_shop_name(self):
        name = self.cleaned_data['shop_name'].strip()
        duplicates = Shop.objects.filter(shop_name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('Tên shop đã được sử dụng. Vui lòng chọn tên khác.')
        return name


class ShopLegalForm(forms.ModelForm):
    """Step 4: legal documents. Both files are required."""

    class Meta:
        model = Shop
        fields = ['id_card', 'business_license']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_card'].required = True
        self.fields['id_card'].label = 'CMND/CCCD'
        self.fields['business_license'].required = True
        self.fields['business_license'].label = 'Giấy phép kinh doanh'
