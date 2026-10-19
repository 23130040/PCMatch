from django.conf import settings
from django.core.mail import send_mail
from django.db import models


class Shop(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
    ]

    shop_id = models.BigAutoField(primary_key=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shop')
    shop_name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='shop_logo/', blank=True)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    platform_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    # Legal verification documents uploaded during onboarding.
    id_card = models.FileField(upload_to='shop_docs/', blank=True)
    business_license = models.FileField(upload_to='shop_docs/', blank=True)
    legal_submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.shop_name

    def save(self, *args, **kwargs):
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
