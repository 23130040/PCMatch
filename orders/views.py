from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_GET, require_POST
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from shops.models import Shop
from orders.models import CancellationRequest, Order, OrderItem, OrderStatusHistory, ShopOrder
from orders.services import (
    confirm_order_received,
    ensure_shop_orders,
    mark_carrier_delivered,
    process_order_timeouts,
    recompute_order_status,
    request_order_cancellation,
    resolve_escalated_cancellation,
    verify_carrier_webhook,
)

from users.views import buyer_required, staff_required
from .services import create_order

def order_list(request):
    process_order_timeouts()
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
        'page_name': 'order' if request.resolver_match.url_name == 'staff_order' else 'orders',
        'page_section': 'staff',
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
    process_order_timeouts()
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
            'shop_orders__shop',
            'shop_orders__history__changed_by',
            'shop_orders__cancellation_requests__requested_by',
            'shop_orders__cancellation_requests__resolved_by',
        ),
        pk=order_id,
    )
    ensure_shop_orders(order)
    status_labels = dict(Order.ORDER_STATUS_CHOICES)
    history = list(order.status_history.all())
    for event in history:
        event.old_status_label = status_labels.get(event.old_status, event.old_status)
        event.new_status_label = status_labels.get(event.new_status, event.new_status)
    return render(request, 'admin/order_detail.html', {
        'order': order,
        'history': history,
        'shop_orders': ShopOrder.objects.filter(order=order).select_related('shop').prefetch_related('history__changed_by'),
        'escalated_cancellations': CancellationRequest.objects.filter(
            shop_order__order=order,
            status='ESCALATED',
        ).select_related('shop_order__shop', 'requested_by'),
    })

@require_POST
@buyer_required
def place_order(request):
    try:
        token = signing.loads(request.POST.get('checkout_token', ''), salt='checkout', max_age=86400)
        if token['user'] != request.user.pk:
            raise signing.BadSignature
        payment_method = request.POST.get('paymentMethod', '').strip()
        if payment_method != 'COD':
            raise ValidationError('Thanh toán VNPay chưa được triển khai. Vui lòng chọn COD.')
        order = create_order(request.user, payment_method, token['nonce'])
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
    process_order_timeouts()
    orders = Order.objects.filter(user=request.user).prefetch_related('shop_orders').order_by('-created_at', '-pk')
    query = request.GET.get('q', '').strip()
    if query:
        orders = orders.filter(order_code__icontains=query)
    orders_page = Paginator(orders, 10).get_page(request.GET.get('page'))
    for order in orders_page:
        order.has_partial_cancellation = any(
            shop_order.status == 'CANCELLED'
            for shop_order in order.shop_orders.all()
        ) and any(shop_order.status != 'CANCELLED' for shop_order in order.shop_orders.all())
    return render(request, 'buyer/orders.html', {
        'page_name': 'orders', 'page_section': 'buyer', 'q': query,
        'orders_page': orders_page,
    })


@require_GET
@buyer_required
def buyer_order(request):
    process_order_timeouts()
    order = get_object_or_404(
        Order.objects.select_related('address').prefetch_related(
            'order_items__product',
            'order_items__shop',
            'status_history',
            'shop_orders__shop',
            'shop_orders__history__changed_by',
            'shop_orders__cancellation_requests',
        ),
        order_code=request.GET.get('id', ''), user=request.user,
    )
    ensure_shop_orders(order)
    recompute_order_status(order)
    shop_orders = list(
        ShopOrder.objects.filter(order=order)
        .select_related('shop')
        .prefetch_related('history__changed_by', 'cancellation_requests')
    )
    for shop_order in shop_orders:
        shop_order.items = [
            item for item in order.order_items.all()
            if item.shop_id == shop_order.shop_id
        ]
    order.has_partial_cancellation = (
        any(shop_order.status == 'CANCELLED' for shop_order in shop_orders)
        and any(shop_order.status != 'CANCELLED' for shop_order in shop_orders)
    )
    can_cancel = any(shop_order.status == 'PENDING' for shop_order in shop_orders) or (
        len(shop_orders) > 1
        and any(shop_order.status == 'PROCESSING' for shop_order in shop_orders)
    )
    return render(request, 'buyer/order.html', {
        'page_name': 'order',
        'page_section': 'buyer',
        'order': order,
        'shop_orders': shop_orders,
        'cancel_reasons': CancellationRequest.REASON_CHOICES,
        'can_cancel': can_cancel,
        'can_confirm_received': any(shop_order.status == 'DELIVERED' for shop_order in shop_orders),
    })


@require_POST
@buyer_required
def buyer_cancel_order(request, order_id):
    process_order_timeouts()
    reason = request.POST.get('reason', '').strip()
    note = request.POST.get('note', '').strip()
    try:
        result = request_order_cancellation(order_id, request.user, reason, note)
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        if result['request_created']:
            messages.success(request, 'Đã gửi yêu cầu hủy đến shop để xử lý.')
        else:
            messages.success(request, 'Đã hủy phần hàng chưa được shop xác nhận.')
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return redirect(f'{reverse("buyer_order")}?id={order.order_code}')


@require_POST
@buyer_required
def buyer_confirm_received(request, order_id):
    try:
        order = confirm_order_received(order_id, request.user)
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, 'Đã xác nhận nhận các phần hàng đã giao.')
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return redirect(f'{reverse("buyer_order")}?id={order.order_code}')


@require_POST
@staff_required
def staff_resolve_cancellation(request, request_id):
    decision = request.POST.get('decision', '')
    if decision not in {'approve', 'reject'}:
        messages.error(request, 'Thao tác xử lý yêu cầu không hợp lệ.')
        return redirect('load_ListOrder')
    try:
        cancellation = resolve_escalated_cancellation(
            request_id,
            request.user,
            decision == 'approve',
            request.POST.get('note', '').strip(),
        )
    except ValidationError as error:
        messages.error(request, error.messages[0])
        return redirect('load_ListOrder')
    messages.success(request, f'Đã xử lý yêu cầu hủy đơn {cancellation.shop_order.order.order_code}.')
    return redirect('staff_order_detail', order_id=cancellation.shop_order.order_id)


@csrf_exempt
@require_POST
def carrier_delivery_webhook(request):
    try:
        payload = verify_carrier_webhook(
            request.body,
            request.headers.get('X-PCMatch-Timestamp', ''),
            request.headers.get('X-PCMatch-Signature', ''),
        )
        result = mark_carrier_delivered(
            provider=payload['provider'],
            event_id=payload['event_id'],
            tracking_code=payload['tracking_code'],
        )
    except ValidationError as error:
        return JsonResponse({'error': error.messages[0]}, status=400)
    return JsonResponse({'result': result    })
