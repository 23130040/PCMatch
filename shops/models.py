from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.utils.text import slugify


class Shop(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Chờ duyệt'),
        ('ACTIVE', 'Đã duyệt'),
        ('REJECTED', 'Bị từ chối'),
        ('SUSPENDED', 'Bị khóa / tạm ngưng'),
    ]
    LEGAL_ENTITY_CHOICES = [
        ('INDIVIDUAL', 'Cá nhân'),
        ('HOUSEHOLD', 'Hộ kinh doanh'),
        ('COMPANY', 'Công ty'),
    ]

    shop_id = models.BigAutoField(primary_key=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shop')
    shop_name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True, blank=True, null=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='shop_logo/', blank=True)
    cover_image = models.ImageField(upload_to='shop_cover/', blank=True)
    business_categories = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    province = models.CharField(max_length=120, blank=True)
    district = models.CharField(max_length=120, blank=True)
    ward = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone_verified = models.BooleanField(default=False)
    contact_email_verified = models.BooleanField(default=False)
    working_hours = models.CharField(max_length=255, blank=True)
    warranty_policy = models.TextField(blank=True)
    return_policy = models.TextField(blank=True)
    legal_entity_type = models.CharField(max_length=20, choices=LEGAL_ENTITY_CHOICES, blank=True)
    representative_name = models.CharField(max_length=150, blank=True)
    representative_birth_date = models.DateField(null=True, blank=True)
    id_number = models.CharField(max_length=30, blank=True)
    id_card_front = models.FileField(upload_to='shop_docs/', blank=True)
    id_card_back = models.FileField(upload_to='shop_docs/', blank=True)
    tax_number = models.CharField(max_length=50, blank=True)
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_account_holder = models.CharField(max_length=150, blank=True)
    bank_branch = models.CharField(max_length=150, blank=True)
    shipping_carriers = models.CharField(max_length=255, blank=True)
    pickup_address = models.TextField(blank=True)
    return_address = models.TextField(blank=True)
    processing_time_days = models.PositiveSmallIntegerField(default=1)
    default_shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    identity_verified = models.BooleanField(default=False)
    admin_note = models.TextField(blank=True)
    platform_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    # Legal verification documents uploaded during onboarding.
    id_card = models.FileField(upload_to='shop_docs/', blank=True)
    business_license = models.FileField(upload_to='shop_docs/', blank=True)
    legal_submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.shop_name

    def is_ready_for_approval(self):
        if not self.owner.email_verified or not self.legal_submitted_at:
            return False
        if not self.legal_entity_type:
            return bool(self.id_card and self.business_license)
        representative_details_complete = bool(
            self.representative_name
            and self.representative_birth_date
            and self.id_number
        )
        if not representative_details_complete:
            return False
        if self.legal_entity_type == 'INDIVIDUAL':
            return bool(self.id_card_front and self.id_card_back)
        return bool(
            self.id_card
            and self.business_license
            and self.tax_number
        )

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.shop_name) or 'shop'
            candidate = base_slug
            suffix = 2
            while type(self).objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f'{base_slug}-{suffix}'
                suffix += 1
            self.slug = candidate
        previous_status = None
        if self.pk:
            previous_status = type(self).objects.filter(pk=self.pk).values_list('status', flat=True).first()
        super().save(*args, **kwargs)
        if previous_status is not None and previous_status != 'ACTIVE' and self.status == 'ACTIVE':
            self.notify_approved()

    def notify_approved(self):
        """Admin approved the shop: record a notification and email the owner."""
        from notifications.models import Notification

        Notification.objects.create(
            user=self.owner,
            title='Shop đã được phê duyệt',
            message=f'Chúc mừng, shop "{self.shop_name}" của bạn đã được phê duyệt thành công. Bạn có thể bắt đầu kinh doanh!',
            type='SHOP_APPROVED',
        )
        send_mail(
            'Shop của bạn đã được phê duyệt thành công',
            f'Chúc mừng, shop "{self.shop_name}" của bạn đã được phê duyệt thành công trên PCMatch. '
            'Bạn có thể bắt đầu đăng bán sản phẩm ngay bây giờ.',
            None,
            [self.owner.email],
            fail_silently=True,
        )
