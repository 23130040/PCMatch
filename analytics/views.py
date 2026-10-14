from django.shortcuts import render
from django.db.models import Sum
from orders.models import Order



def bieudoCot():
    list_DoanhThu_12Months = []

    for i in range(1, 13):
        someOrders = Order.objects.filter(
            created_at__year=2026,
            created_at__month=i
        ).exclude(order_status='CANCELLED')

        totalRevenue = someOrders.aggregate(Sum('total_amount'))
        outPutMoney = totalRevenue['total_amount__sum'] or 0

        list_DoanhThu_12Months.append(float(outPutMoney))

    return list_DoanhThu_12Months



def bieudoTron():
    order_Pending = Order.objects.filter(order_status='PENDING').count()
    order_Comfirm = Order.objects.filter(order_status='CONFIRMED').count()
    order_Delivered = Order.objects.filter(order_status='DELIVERED').count()
    order_Cancelled = Order.objects.filter(order_status='CANCELLED').count()

    total_orders = order_Pending + order_Comfirm + order_Delivered + order_Cancelled

    listOrder = [
        order_Pending,
        order_Comfirm,
        order_Delivered,
        order_Cancelled
    ]

    return {
        'listOrder': listOrder,
        'order_Pending': order_Pending,
        'order_Comfirm': order_Comfirm,
        'order_Delivered': order_Delivered,
        'order_Cancelled': order_Cancelled,
        'total_orders': total_orders,
    }



def dashboard_view(request):
    data_cot = bieudoCot()
    data_tron = bieudoTron()

    box = {
        'list_DoanhThu_12Months': data_cot,
        **data_tron
    }

    return render(request, 'admin/dashboard.html', box)