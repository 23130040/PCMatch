from django.db import models

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('VNPAY', 'VNPay'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    payment_id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='payments')
    transaction_code = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.order_code} | {self.payment_method} | {self.status}"