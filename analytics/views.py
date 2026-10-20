from django.shortcuts import render
from django.db.models import Sum, Count
from orders.models import Order
from products.models import Product  # 1. Thêm import Product


def bieudoTron():
   
    order_Pending = Order.objects.filter(order_status='PENDING').count()
    order_Comfirm = Order.objects.filter(order_status='COMFIRMED').count()
    order_Delivered = Order.objects.filter(order_status='DELIVERED').count()
    order_Cancelled = Order.objects.filter(order_status='CANCELLED').count()

    total_orders = order_Pending + order_Comfirm + order_Delivered + order_Cancelled
    listOrder = [order_Pending, order_Comfirm, order_Delivered, order_Cancelled]

    return {
        'total_orders': total_orders,
        'order_Pending': order_Pending,
        'order_Comfirm': order_Comfirm,
        'order_Delivered': order_Delivered,
        'order_Cancelled': order_Cancelled,
        'listOrder': listOrder
    }


def dashboard_view(request):
    data_cot = bieudoCot()
    data_tron = bieudoTron()

  
    top10SPsale = Product.objects.order_by('-sold_quantity')[:10]

   
    total_revenue = Order.objects.filter(order_status='DELIVERED').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_orders_count = Order.objects.count()
    total_products_count = Product.objects.count()

    box = {
        'list_DoanhThu_12Months': data_cot,
        'top10SPsale': top10SPsale,
        'total_revenue': total_revenue,             # 
        'total_orders_count': total_orders_count,   
        'total_products_count': total_products_count,
        **data_tron
    }

    return render(request, 'admin/dashboard.html', box)