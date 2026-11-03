from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image, UnidentifiedImageError

from users.forms import BuyerSetPasswordForm

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


class SellerForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label='Email đăng ký',
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}),
    )

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()


class SellerSetPasswordForm(BuyerSetPasswordForm):
    pass


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

class SellerVerificationEmailForm(forms.Form):
    email = forms.EmailField(
        label='Email đăng ký',
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )


class ShopProfileForm(forms.ModelForm):
    """Step 3: shop profile. Shop name must be unique."""

    phone = forms.RegexField(
        regex=r'\A0[0-9]{9}\Z',
        label='Số điện thoại',
        error_messages={'invalid': 'Nhập số điện thoại Việt Nam gồm 10 chữ số, bắt đầu bằng 0.'},
    )

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

    def clean_logo(self):
        return ShopLegalForm._validate_document(self.cleaned_data.get('logo'), allow_pdf=False)


class ShopSettingsForm(forms.ModelForm):
    phone = forms.RegexField(
        regex=r'\A0[0-9]{9}\Z',
        label='Số điện thoại liên hệ shop',
        error_messages={'invalid': 'Nhập số điện thoại Việt Nam gồm 10 chữ số, bắt đầu bằng 0.'},
    )

    class Meta:
        model = Shop
        fields = [
            'shop_name', 'slug', 'logo', 'cover_image', 'description',
            'business_categories', 'address', 'province', 'district', 'ward',
            'phone', 'contact_email', 'working_hours', 'warranty_policy',
            'return_policy', 'legal_entity_type', 'representative_name',
            'representative_birth_date', 'id_number', 'id_card_front',
            'id_card_back', 'id_card', 'tax_number', 'business_license',
            'bank_name', 'bank_account_number', 'bank_account_holder',
            'bank_branch', 'shipping_carriers', 'pickup_address',
            'return_address', 'processing_time_days', 'default_shipping_fee',
        ]
        labels = {
            'shop_name': 'Tên shop',
            'slug': 'Slug / đường dẫn',
            'logo': 'Logo shop',
            'cover_image': 'Ảnh bìa',
            'description': 'Mô tả giới thiệu',
            'business_categories': 'Danh mục kinh doanh (ví dụ: CPU, VGA, RAM)',
            'address': 'Số nhà, tên đường',
            'province': 'Tỉnh / thành phố',
            'district': 'Quận / huyện',
            'ward': 'Phường / xã',
            'phone': 'Số điện thoại liên hệ shop',
            'contact_email': 'Email liên hệ shop',
            'working_hours': 'Giờ làm việc',
            'warranty_policy': 'Chính sách bảo hành',
            'return_policy': 'Chính sách đổi trả',
            'legal_entity_type': 'Loại hình đăng ký',
            'representative_name': 'Họ tên người đại diện',
            'representative_birth_date': 'Ngày sinh người đại diện',
            'id_number': 'Số CCCD / CMND',
            'id_card_front': 'Ảnh mặt trước CCCD',
            'id_card_back': 'Ảnh mặt sau CCCD',
            'id_card': 'Giấy tờ định danh đã nộp',
            'tax_number': 'Mã số thuế',
            'business_license': 'Giấy phép đăng ký kinh doanh',
            'bank_name': 'Tên ngân hàng',
            'bank_account_number': 'Số tài khoản',
            'bank_account_holder': 'Tên chủ tài khoản',
            'bank_branch': 'Chi nhánh (không bắt buộc)',
            'shipping_carriers': 'Đơn vị vận chuyển hỗ trợ',
            'pickup_address': 'Địa chỉ lấy hàng',
            'return_address': 'Địa chỉ trả hàng',
            'processing_time_days': 'Thời gian xử lý đơn (ngày)',
            'default_shipping_fee': 'Phí giao hàng mặc định (đồng)',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'warranty_policy': forms.Textarea(attrs={'rows': 3}),
            'return_policy': forms.Textarea(attrs={'rows': 3}),
            'pickup_address': forms.Textarea(attrs={'rows': 2}),
            'return_address': forms.Textarea(attrs={'rows': 2}),
            'representative_birth_date': forms.DateInput(attrs={'type': 'date'}),
            'business_categories': forms.TextInput(attrs={'placeholder': 'CPU, VGA, RAM, mainboard, PC build sẵn'}),
            'shipping_carriers': forms.TextInput(attrs={'placeholder': 'Ví dụ: GHN, GHTK'}),
            'slug': forms.TextInput(attrs={'placeholder': 'duong-dan-shop'}),
            'logo': forms.FileInput(),
            'cover_image': forms.FileInput(),
            'id_card_front': forms.FileInput(),
            'id_card_back': forms.FileInput(),
            'id_card': forms.FileInput(),
            'business_license': forms.FileInput(),
        }

    def clean_shop_name(self):
        name = self.cleaned_data['shop_name'].strip()
        duplicates = Shop.objects.filter(shop_name__iexact=name).exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('Tên shop đã được sử dụng. Vui lòng chọn tên khác.')
        return name

    def clean_slug(self):
        slug = self.cleaned_data.get('slug', '').strip()
        if not slug:
            return ''
        slug = slugify(slug)
        duplicates = Shop.objects.filter(slug=slug).exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('Đường dẫn này đã được sử dụng.')
        return slug

    def clean_logo(self):
        return ShopLegalForm._validate_document(self.cleaned_data.get('logo'), allow_pdf=False)

    def clean_cover_image(self):
        return ShopLegalForm._validate_document(self.cleaned_data.get('cover_image'), allow_pdf=False)

    def clean_id_card_front(self):
        return ShopLegalForm._validate_document(self.cleaned_data.get('id_card_front'), allow_pdf=False)

    def clean_id_card_back(self):
        return ShopLegalForm._validate_document(self.cleaned_data.get('id_card_back'), allow_pdf=False)

    def clean_representative_birth_date(self):
        birth_date = self.cleaned_data.get('representative_birth_date')
        if birth_date and birth_date > timezone.localdate():
            raise forms.ValidationError('Ngày sinh không thể ở trong tương lai.')
        return birth_date

    def clean_processing_time_days(self):
        days = self.cleaned_data['processing_time_days']
        if not 1 <= days <= 30:
            raise forms.ValidationError('Thời gian xử lý phải từ 1 đến 30 ngày.')
        return days

    def clean_default_shipping_fee(self):
        fee = self.cleaned_data['default_shipping_fee']
        if fee < 0:
            raise forms.ValidationError('Phí giao hàng không thể âm.')
        return fee

    def clean_id_card(self):
        return ShopLegalForm._validate_document(self.cleaned_data.get('id_card'))

    def clean_business_license(self):
        return ShopLegalForm._validate_document(self.cleaned_data.get('business_license'))


class ShopLegalForm(forms.ModelForm):
    """Step 4: collect representative details and documents for shop review."""

    class Meta:
        model = Shop
        fields = [
            'legal_entity_type', 'representative_name', 'representative_birth_date',
            'id_number', 'id_card_front', 'id_card_back', 'id_card',
            'tax_number', 'business_license',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        entity_type = self.data.get('legal_entity_type') or getattr(self.instance, 'legal_entity_type', '')
        self.fields['legal_entity_type'].required = True
        self.fields['representative_name'].required = True
        self.fields['representative_birth_date'].required = True
        self.fields['id_number'].required = True
        if entity_type == 'INDIVIDUAL':
            self.fields['id_card_front'].required = True
            self.fields['id_card_back'].required = True
        elif entity_type in {'HOUSEHOLD', 'COMPANY'}:
            self.fields['id_card'].required = True
            self.fields['tax_number'].required = True
            self.fields['business_license'].required = True

        self.fields['legal_entity_type'].label = 'Loại hình đăng ký'
        self.fields['representative_name'].label = 'Họ tên người đại diện'
        self.fields['representative_birth_date'].label = 'Ngày sinh người đại diện'
        self.fields['id_number'].label = 'Số CCCD / CMND người đại diện'
        self.fields['id_card_front'].label = 'Ảnh mặt trước CCCD (cá nhân)'
        self.fields['id_card_back'].label = 'Ảnh mặt sau CCCD (cá nhân)'
        self.fields['id_card'].label = 'Giấy tờ định danh người đại diện (hộ kinh doanh / công ty)'
        self.fields['tax_number'].label = 'Mã số thuế (hộ kinh doanh / công ty)'
        self.fields['business_license'].label = 'Giấy phép đăng ký kinh doanh (hộ kinh doanh / công ty)'
        self.fields['representative_birth_date'].widget = forms.DateInput(attrs={'type': 'date'})
        for field_name in ('id_card_front', 'id_card_back', 'id_card', 'business_license'):
            self.fields[field_name].widget = forms.FileInput()

    def clean_representative_birth_date(self):
        birth_date = self.cleaned_data.get('representative_birth_date')
        if birth_date and birth_date > timezone.localdate():
            raise forms.ValidationError('Ngày sinh không thể ở trong tương lai.')
        return birth_date

    def clean_id_card_front(self):
        return self._validate_document(self.cleaned_data.get('id_card_front'), allow_pdf=False)

    def clean_id_card_back(self):
        return self._validate_document(self.cleaned_data.get('id_card_back'), allow_pdf=False)

    def clean_id_card(self):
        return self._validate_document(self.cleaned_data.get('id_card'))

    def clean_business_license(self):
        return self._validate_document(self.cleaned_data.get('business_license'))

    def clean(self):
        cleaned = super().clean()
        entity_type = cleaned.get('legal_entity_type')
        if entity_type == 'INDIVIDUAL' and not (
            cleaned.get('id_card_front') and cleaned.get('id_card_back')
        ):
            self.add_error(None, 'Cá nhân cần tải lên ảnh hai mặt CCCD.')
        return cleaned

    @staticmethod
    def _validate_document(upload, allow_pdf=True):
        if not isinstance(upload, UploadedFile):
            return upload
        if upload.size > 10 * 1024 * 1024:
            raise forms.ValidationError('Mỗi giấy tờ không được vượt quá 10 MB.')

        suffix = upload.name.rsplit('.', 1)[-1].lower() if '.' in upload.name else ''
        allowed_suffixes = {'jpg', 'jpeg', 'png'}
        if allow_pdf:
            allowed_suffixes.add('pdf')
        if suffix not in allowed_suffixes:
            raise forms.ValidationError('Chỉ chấp nhận ảnh JPG, PNG hoặc tài liệu PDF.')

        header = upload.read(8)
        upload.seek(0)
        if suffix == 'pdf':
            valid = header.startswith(b'%PDF-')
        else:
            try:
                image = Image.open(upload)
                valid = (
                    image.format in {'JPEG', 'PNG'}
                    and image.width * image.height <= 20_000_000
                )
                image.verify()
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
                valid = False
            finally:
                upload.seek(0)
        if not valid:
            raise forms.ValidationError('Nội dung tệp không khớp với định dạng được hỗ trợ.')
        return upload
