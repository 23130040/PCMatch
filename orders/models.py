from django.conf import settings
from django.db import models

class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('VNPAY', 'VNPay'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    ORDER_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMFIRMED', 'Comfirmed'),
        ('PROCESSING', 'Processing'),
        ('SHIPPING', 'Shipping'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('RETURNED', 'Returned'),
    ]

    order_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey('users.Address', on_delete=models.CASCADE, related_name='orders')
    order_code = models.CharField(max_length=50, unique=True)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    order_status = models.CharField(max_length=30, choices=ORDER_STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order_id} | {self.address} | {self.order_code}"

class OrderItem(models.Model):
    order_item_id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='order_items')
    shop = models.ForeignKey('shops.Shop', on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    item_status = models.CharField(max_length=30)

    def __str__(self):
        return f"{self.product} x {self.quantity}"

class OrderStatusHistory(models.Model):
    history_id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='order_status_changes')
    old_status = models.CharField(max_length=30, null=True, blank=True)
    new_status = models.CharField(max_length=30)
    note = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order} | {self.old_status} -> {self.new_status}"

class Return(models.Model):
    STATUS_CHOICES = [
        ('REQUESTED', 'Requested'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('REFUNDED', 'Refunded'),
    ]

    return_id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='returns')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='returns')
    reason = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='REQUESTED')
    refund_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Return #{self.return_id} - {self.status}"