from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth import get_user_model

User = get_user_model()


class BuyerRegisterForm(forms.Form):
    full_name = forms.CharField(
        label='Họ tên', max_length=100, required=True,
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
            status='ACTIVE',
        )
        user.set_password(self.cleaned_data['password1'])
        user.save()
        return user


class BuyerLoginForm(forms.Form):
    email = forms.EmailField(
        label='Email', required=True,
        widget=forms.EmailInput(attrs={'autocomplete': 'username'}),
    )
    password = forms.CharField(
        label='Mật khẩu', required=True,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )
