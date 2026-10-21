from django.shortcuts import render
from django.db.models import Sum
from django.db.models.functions import ExtractMonth
from django.utils import timezone
from products.models import Product
from orders.models import Order

# 1. Hàm tính doanh thu 12 tháng & top sản phẩm
def bieudoCot():
    currentYear = timezone.now().year
    
    # Mảng 12 tháng mặc định bằng 0
    moneyMonthly = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    
    monthlyMoney = (
        Order.objects.filter(order_status='DELIVERED', created_at__year=currentYear)
        .annotate(month=ExtractMonth('created_at'))
        .values('month')
        .annotate(total=Sum('total_amount'))
        .order_by('month')
    )
    
    for item in monthlyMoney:
        monthNumber = item['month']
        monthIndex = monthNumber - 1
        
        moneyItem = item['total']
        if moneyItem is None:
            moneyItem = 0
            
        if monthIndex >= 0 and monthIndex < 12:
            moneyMonthly[monthIndex] = float(moneyItem)

    top10SPsale = Product.objects.order_by('-sold_quantity')[:10]

    totalMoney = Order.objects.filter(order_status='DELIVERED').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    totalOrdersCount = Order.objects.count()
    totalProductsCount = Product.objects.count()

    return {
        'list_DoanhThu_12Months': moneyMonthly,
        'top10SPsale': top10SPsale,
        'total_revenue': totalMoney,
        'total_orders_count': totalOrdersCount,
        'total_products_count': totalProductsCount,
    }


def bieudoTron():
    orderPending    = Order.objects.filter(order_status='PENDING').count()
    orderComfirm    = Order.objects.filter(order_status='COMFIRMED').count()
    orderProcessing = Order.objects.filter(order_status='PROCESSING').count()
    orderShipping   = Order.objects.filter(order_status='SHIPPING').count()
    orderDelivered  = Order.objects.filter(order_status='DELIVERED').count()
    orderCancelled  = Order.objects.filter(order_status='CANCELLED').count()
    orderReturned   = Order.objects.filter(order_status='RETURNED').count()

    listOrder = [
        orderPending,
        orderComfirm,
        orderProcessing,
        orderShipping,
        orderDelivered,
        orderCancelled,
        orderReturned
    ]

    totalOrders = sum(listOrder)

    return {
        'total_orders': totalOrders,
        'order_Pending': orderPending,
        'order_Comfirm': orderComfirm,
        'order_Processing': orderProcessing,
        'order_Shipping': orderShipping,
        'order_Delivered': orderDelivered,
        'order_Cancelled': orderCancelled,
        'order_Returned': orderReturned,
        'listOrder': listOrder,
        'status_labels': ['Chờ xác nhận', 'Đã xác nhận', 'Đang xử lý', 'Đang giao', 'Đã giao', 'Đã hủy', 'Trả hàng']
    }


def dashboard_view(request):
    context = {}
    context.update(bieudoCot())
    context.update(bieudoTron())
    return render(request, 'admin/dashboard.html', context)