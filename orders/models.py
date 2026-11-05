from django.conf import settings
from django.db import models

class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('VNPAY', 'VNPay'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('UNPAID', 'Chưa thanh toán'),
        ('PENDING', 'Chờ thanh toán'),
        ('PAID', 'Đã thanh toán'),
        ('FAILED', 'Thanh toán thất bại'),
        ('REFUNDED', 'Đã hoàn tiền'),
    ]
    ORDER_STATUS_CHOICES = [
        ('AWAITING_PAYMENT', 'Chờ thanh toán VNPay'),
        ('PENDING', 'Chờ shop xác nhận'),
        ('COMFIRMED', 'Admin đã xác nhận (cũ)'),
        ('PROCESSING', 'Shop đang xử lý'),
        ('SHIPPING', 'Đang giao hàng'),
        ('DELIVERED', 'Đã giao, chờ người mua xác nhận'),
        ('COMPLETED', 'Hoàn thành'),
        ('CANCELLED', 'Đã hủy'),
        ('RETURNED', 'Returned'),
    ]

    order_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey('users.Address', on_delete=models.CASCADE, related_name='orders')
    order_code = models.CharField(max_length=50, unique=True)
    checkout_token = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default='UNPAID')
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


class ShopOrder(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Chờ shop xác nhận'),
        ('PROCESSING', 'Đang xử lý'),
        ('SHIPPING', 'Đang giao'),
        ('DELIVERED', 'Đã giao, chờ người mua xác nhận'),
        ('COMPLETED', 'Hoàn thành'),
        ('CANCELLED', 'Đã hủy'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='shop_orders')
    shop = models.ForeignKey('shops.Shop', on_delete=models.CASCADE, related_name='shop_orders')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    confirmation_deadline = models.DateTimeField()
    carrier_name = models.CharField(max_length=100, blank=True)
    tracking_code = models.CharField(max_length=100, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['pk']
        constraints = [
            models.UniqueConstraint(fields=['order', 'shop'], name='uniq_order_shop_suborder'),
        ]

    def __str__(self):
        return f'{self.order.order_code} · {self.shop.shop_name}'


class ShopOrderHistory(models.Model):
    shop_order = models.ForeignKey(ShopOrder, on_delete=models.CASCADE, related_name='history')
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shop_order_changes',
    )
    old_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30)
    note = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['changed_at', 'pk']


class CancellationRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Chờ shop xử lý'),
        ('APPROVED', 'Đã chấp nhận'),
        ('REJECTED', 'Bị từ chối'),
        ('ESCALATED', 'Chờ admin xử lý'),
        ('ADMIN_APPROVED', 'Admin đã chấp nhận'),
        ('ADMIN_REJECTED', 'Admin đã từ chối'),
    ]
    REASON_CHOICES = [
        ('WRONG_ORDER', 'Đặt nhầm'),
        ('CHANGED_MIND', 'Đổi ý'),
        ('FOUND_ALTERNATIVE', 'Tìm được sản phẩm khác'),
        ('DELIVERY_TIME', 'Thời gian giao không phù hợp'),
        ('OTHER', 'Khác'),
    ]

    shop_order = models.ForeignKey(ShopOrder, on_delete=models.CASCADE, related_name='cancellation_requests')
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='order_cancellation_requests',
    )
    reason = models.CharField(max_length=40, choices=REASON_CHOICES)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    requested_at = models.DateTimeField(auto_now_add=True)
    response_deadline = models.DateTimeField()
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_order_cancellations',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        ordering = ['-requested_at', '-pk']


class CarrierWebhookEvent(models.Model):
    provider = models.CharField(max_length=100)
    event_id = models.CharField(max_length=150)
    tracking_code = models.CharField(max_length=100)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['provider', 'event_id'], name='uniq_carrier_provider_event'),
        ]


class OrderStatusHistory(models.Model):
    history_id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_status_changes',
    )
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
