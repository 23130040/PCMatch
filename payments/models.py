from django.db import models

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('VNPAY', 'VNPay'),
    ]
    STATUS_CHOICES = [
        ('UNPAID', 'Chưa thanh toán'),
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    payment_id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='payments')
    transaction_code = models.CharField(max_length=100, unique=True)
    gateway_transaction_no = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.order_code} | {self.payment_method} | {self.status}"

class Wallet(models.Model):
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='wallet',
    )

    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Ví của {self.user.username} - {self.balance} VND'

class WalletTransaction(models.Model):

    TRANSACTION_TYPES = [
        ('ORDER_REFUND', 'Hoàn tiền đơn hàng'),
        ('ORDER_PAYMENT', 'Thanh toán đơn hàng'),
    ]

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name='transactions',
    )

    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.PROTECT,
        related_name='wallet_transactions',
        null=True,
        blank=True,
    )

    transaction_type = models.CharField(
        max_length=30,
        choices=TRANSACTION_TYPES,
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    balance_after = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    description = models.CharField(
        max_length=255,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']

        constraints = [
            models.UniqueConstraint(
                fields=['order', 'transaction_type'],
                condition=models.Q(
                    order__isnull=False,
                    transaction_type='ORDER_REFUND',
                ),
                name='unique_order_wallet_refund',
            ),
        ]

    def __str__(self):
        return f'{self.transaction_type} - {self.amount} VND'
