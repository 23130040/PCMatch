from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_GET, require_POST
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.urls import reverse
from shops.models import Shop
from orders.models import Order, OrderItem, OrderStatusHistory

from users.views import buyer_required, staff_required
from payments.vnpay import configured, payment_url
from .services import confirm_order, create_order

def orderList(request):
    search = request.GET.get('search', '').strip()
    locStatus = request.GET.get('status', '').strip()
    idOfShop = request.GET.get('shop', '').strip()
    page = request.GET.get('page', 1)

    allOrder = Order.objects.select_related('user', 'address').prefetch_related(
        Prefetch(
            'order_items',
            queryset=OrderItem.objects.select_related('product', 'shop'),
        ),
    ).order_by('-created_at', '-pk')

   
    if locStatus != '' and locStatus != 'ALL':
        allOrder = allOrder.filter(order_status=locStatus)

   
    if search != '':
        allOrder = allOrder.filter(order_code__icontains=search)

    
    if idOfShop != '':
        allOrder = allOrder.filter(order_items__shop_id=idOfShop).distinct()

    dividePage = Paginator(allOrder, 10)
    showOrder = dividePage.get_page(page)

    box = {
        'showOrder': showOrder,
        'locStatus': locStatus,
        'search': search,
        'idOfShop': idOfShop,
        'shops': Shop.objects.all(),
    }
    return render(request, 'admin/order.html', box)


@require_GET
@staff_required
def staff_order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('user', 'address').prefetch_related(
            Prefetch(
                'order_items',
                queryset=OrderItem.objects.select_related('product', 'shop').order_by('pk'),
            ),
            Prefetch(
                'status_history',
                queryset=OrderStatusHistory.objects.select_related('changed_by').order_by('changed_at', 'pk'),
            ),
        ),
        pk=order_id,
    )
    status_labels = dict(Order.ORDER_STATUS_CHOICES)
    history = list(order.status_history.all())
    for event in history:
        event.old_status_label = status_labels.get(event.old_status, event.old_status)
        event.new_status_label = status_labels.get(event.new_status, event.new_status)
    return render(request, 'admin/order_detail.html', {
        'order': order,
        'history': history,
        'can_confirm_order': (
            order.order_status == 'PENDING'
            and (order.payment_method != 'VNPAY' or order.payment_status == 'PAID')
        ),
    })


@require_POST
@staff_required
def changeStatus(request, order_id):
    get_object_or_404(Order, pk=order_id)
    try:
        if request.POST.get('status') != 'COMFIRMED':
            raise ValidationError('Admin chỉ xác nhận đơn; shop sẽ xử lý và giao hàng.')
        order = confirm_order(order_id, request.user)
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, f'Đã xác nhận đơn {order.order_code}. Shop có thể bắt đầu xử lý.')
    return redirect('load_ListOrder')

@require_POST
@buyer_required
def place_order(request):
    try:
        token = signing.loads(request.POST.get('checkout_token', ''), salt='checkout', max_age=86400)
        if token['user'] != request.user.pk:
            raise signing.BadSignature
        payment_method = request.POST.get('paymentMethod', '').strip()
        if payment_method == 'VNPAY' and not configured():
            raise ValidationError('VNPay chưa được cấu hình sandbox. Vui lòng chọn COD.')
        order = create_order(request.user, payment_method, token['nonce'])
        if order.payment_method == 'VNPAY' and order.order_status == 'AWAITING_PAYMENT':
            payment = order.payments.get(payment_method='VNPAY', status='PENDING')
            return redirect(payment_url(payment, request.META.get('REMOTE_ADDR', '127.0.0.1')))
    except (signing.BadSignature, KeyError, TypeError):
        messages.error(request, 'Phiên đặt hàng không hợp lệ hoặc đã hết hạn. Vui lòng tải lại trang.')
        return redirect('buyer_checkout')
    except ValidationError as error:
        messages.error(request, error.messages[0])
        return redirect('buyer_checkout')
    except DatabaseError:
        messages.error(request, 'Hệ thống đang bận. Vui lòng thử lại; đơn đã tạo sẽ không bị tạo trùng.')
        return redirect('buyer_checkout')
    return redirect(f'{reverse("buyer_order")}?id={order.order_code}')


@require_GET
@buyer_required
def buyer_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at', '-pk')
    query = request.GET.get('q', '').strip()
    if query:
        orders = orders.filter(order_code__icontains=query)
    return render(request, 'buyer/orders.html', {
        'page_name': 'orders', 'page_section': 'buyer', 'q': query,
        'orders_page': Paginator(orders, 10).get_page(request.GET.get('page')),
    })


@require_GET
@buyer_required
def buyer_order(request):
    order = get_object_or_404(
        Order.objects.select_related('address').prefetch_related('order_items__product', 'order_items__shop', 'status_history'),
        order_code=request.GET.get('id', ''), user=request.user,
    )
    return render(request, 'buyer/order.html', {'page_name': 'order', 'page_section': 'buyer', 'order': order})

@require_POST
@staff_required
def changeManyStatus(request):
    if request.method == 'POST':
        orderIds = request.POST.getlist('order_ids')
        actionStatus = request.POST.get('action_status')

        if orderIds and actionStatus:
            for orderId in orderIds:
                order = Order.objects.get(pk=orderId)

                if actionStatus == 'DELIVERED' and order.order_status != 'DELIVERED':
                    items = getattr(order, 'items', getattr(order, 'order_items', None))
                    if items:
                        for item in items.all():
                            item.product.sold_quantity += item.quantity
                            item.product.save()

                order.order_status = actionStatus
                order.save()

            messages.success(request, f"Đã cập nhật {len(orderIds)} đơn hàng.")

    return redirect('loadOrder')
