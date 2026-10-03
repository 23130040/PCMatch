from django.conf import settings
from django.db import models

class ProductView(models.Model):
    view_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='product_views')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='product_views')
    viewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.viewed_at}"

class UserProductInteraction(models.Model):
    INTERACTION_TYPE_CHOICES = [
        ('VIEW', 'View'),
        ('CART', 'Cart'),
        ('PURCHASE', 'Purchase'),
    ]

    interaction_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_interactions')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='user_interactions')
    interacted_type = models.CharField(max_length=30, choices=INTERACTION_TYPE_CHOICES)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.interacted_type} | {self.quantity}"
