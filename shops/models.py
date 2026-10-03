from django.db import models
from django.conf import settings

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.shop_name