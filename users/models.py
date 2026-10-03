from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('LOCKED', 'Locked'),
    ]

    ROLE_CHOICES = [
        ('CUSTOMER', 'Customer'),
        ('BUYER', 'Buyer'),
        ('ADMIN', 'Admin'),
    ]

    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatar/', blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CUSTOMER')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email

class Address(models.Model):
    address_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    receiver_name = models.CharField(max_length=150)
    receiver_phone = models.CharField(max_length=20)
    province = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    ward = models.CharField(max_length=100)
    detail_address = models.CharField(max_length=255)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.receiver_name

class SocialAccount(models.Model):
    PROVIDER_CHOICES = [
        ('GOOGLE', 'Google'),
        ('FACEBOOK', 'Facebook'),
    ]

    social_account_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields = ['provider', 'provider_user_id'],
                name = 'unique_social_account',
            )
        ]

class PasswordResetToken(models.Model):
    token_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class EmailVerificationToken(models.Model):
    verification_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
