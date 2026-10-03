from django.contrib import admin
from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    Return,
)

admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(OrderStatusHistory)
admin.register(Return)