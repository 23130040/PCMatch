from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_GET, require_POST
from django.core.paginator import Paginator
from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.urls import reverse
from shops.models import Shop
from orders.models import Order

from users.views import buyer_required, staff_required
from payments.vnpay import configured, payment_url
from .services import confirm_order, create_order, retry_vnpay_payment

def orderList(request):
    search = request.GET.get('search', '').strip()
    locStatus = request.GET.get('status', '').strip()
    idOfShop = request.GET.get('shop', '').strip()
    page = request.GET.get('page', 1)

    allOrder = Order.objects.all().order_by('-created_at')

   
    if locStatus != '' and locStatus != 'ALL':
        allOrder = allOrder.filter(order_status=locStatus)

   
    if search != '':
        allOrder = allOrder.filter(order_code__icontains=search)

    
    if idOfShop != '':
        try:
            allOrder = allOrder.filter(items__shop_id=idOfShop).distinct()
        except Exception:
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


@require_POST
@staff_required
def changeStatus(request, orderid):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=orderid)
        newStatus = request.POST.get('order_status')
        valid = ['PENDING', 'COMFIRMED', 'PROCESSING', 'SHIPPING', 'DELIVERED', 'CANCELLED', 'RETURNED']
        
        if newStatus in valid:
            if newStatus == 'DELIVERED' and order.order_status != 'DELIVERED':
                items = getattr(order, 'items', getattr(order, 'order_items', None))
                if items:
                    for item in items.all():
                        item.product.sold_quantity += item.quantity
                        item.product.save()

            if newStatus == 'COMFIRMED':
                try:
                    confirm_order(order.pk, request.user)
                    messages.success(request, 'Đã xác nhận đơn hàng.')
                except ValidationError as error:
                    messages.error(request, error.messages[0])
                return redirect('loadOrder')

            order.order_status = newStatus
            order.save()
            messages.success(request, f'Đã cập nhật đơn hàng thành {newStatus}.')
            
    return redirect('loadOrder')

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


@require_POST
@buyer_required
def buyer_retry_vnpay_payment(request, order_id):
    if not configured():
        messages.error(request, 'VNPay chưa được cấu hình sandbox. Vui lòng thử lại sau.')
        return redirect('buyer_orders')
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    try:
        payment = retry_vnpay_payment(order.pk, request.user)
        return redirect(payment_url(payment, request.META.get('REMOTE_ADDR', '127.0.0.1')))
    except ValidationError as error:
        messages.error(request, error.messages[0])
    except DatabaseError:
        messages.error(request, 'Hệ thống đang bận. Vui lòng thử lại.')
    return redirect(f'{reverse("buyer_order")}?id={order.order_code}')


@require_GET
@buyer_required
def buyer_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('order_items__product').order_by('-created_at', '-pk')
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

