import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from carts.models import Cart, CartItem
from carts.services import validate_quantity
from notifications.models import Notification
from payments.models import Payment
from products.models import Product
from users.models import User
from .models import (
    CancellationRequest,
    CarrierWebhookEvent,
    Order,
    OrderItem,
    OrderStatusHistory,
    ShopOrder,
    ShopOrderHistory,
)

SHOP_CONFIRMATION_HOURS = 12
CANCELLATION_RESPONSE_HOURS = 12
BUYER_COMPLETION_DAYS = 3

BUYER_CANCEL_REASONS = dict(CancellationRequest.REASON_CHOICES)
SHOP_REJECTION_REASONS = {
    'OUT_OF_STOCK': 'Hết hàng',
    'DELIVERY_UNAVAILABLE': 'Không thể giao đến địa chỉ này',
    'PRODUCT_INFORMATION': 'Giá/thông tin sản phẩm sai',
    'OPERATIONS': 'Lý do vận hành khác',
}
SHOP_ORDER_RANK = {
    'PENDING': 0,
    'PROCESSING': 1,
    'SHIPPING': 2,
    'DELIVERED': 3,
    'COMPLETED': 4,
}


def checkout_token(user):
    return signing.dumps({'user': user.pk, 'nonce': uuid4().hex}, salt='checkout')


def _notify(user, title, message, notification_type):
    if user:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            type=notification_type,
        )


def _notify_admins(title, message, notification_type):
    for admin in User.objects.filter(
        Q(is_staff=True) | Q(role='ADMIN'),
        is_active=True,
        status='ACTIVE',
    ).only('pk'):
        _notify(admin, title, message, notification_type)


def history(order, actor, old_status, note=''):
    OrderStatusHistory.objects.create(
        order=order, changed_by=actor, old_status=old_status or '',
        new_status=order.order_status, note=note,
    )


def _shop_order_history(shop_order, actor, new_status, note, old_status=None):
    ShopOrderHistory.objects.create(
        shop_order=shop_order,
        changed_by=actor,
        old_status=old_status if old_status is not None else shop_order.status,
        new_status=new_status,
        note=note,
    )


def _restore_stock(shop_order):
    for item in OrderItem.objects.select_for_update().filter(
        order_id=shop_order.order_id,
        shop_id=shop_order.shop_id,
    ):
        Product.objects.filter(pk=item.product_id).update(
            stock_quantity=F('stock_quantity') + item.quantity,
        )


def _sync_item_status(shop_order, status):
    OrderItem.objects.filter(
        order_id=shop_order.order_id,
        shop_id=shop_order.shop_id,
    ).update(item_status=status)


def recompute_order_status(order, actor=None, note=''):
    shop_orders = list(order.shop_orders.order_by('pk'))
    if not shop_orders:
        return order.order_status

    active = [shop_order for shop_order in shop_orders if shop_order.status != 'CANCELLED']
    if not active:
        new_status = 'CANCELLED'
    else:
        new_status = min(
            (shop_order.status for shop_order in active),
            key=lambda status: SHOP_ORDER_RANK[status],
        )

    old_status = order.order_status
    has_partial_cancellation = len(active) != len(shop_orders)
    if old_status != new_status:
        order.order_status = new_status
        order.save(update_fields=['order_status', 'updated_at'])
        history(order, actor, old_status, note or f'Trạng thái đơn được cập nhật: {new_status}.')
    order.has_partial_cancellation = has_partial_cancellation
    return new_status


def _cancel_shop_order(shop_order, actor, reason, note='', *, system=False):
    if shop_order.status not in {'PENDING', 'PROCESSING'}:
        raise ValidationError('Chỉ có thể hủy phần hàng trước khi được giao thành công.')
    old_status = shop_order.status
    now = timezone.now()
    changed = ShopOrder.objects.filter(pk=shop_order.pk, status=old_status).update(
        status='CANCELLED', cancelled_at=now, updated_at=now,
    )
    if not changed:
        raise ValidationError('Trạng thái phần hàng vừa thay đổi. Vui lòng tải lại trang.')
    shop_order.status = 'CANCELLED'
    shop_order.cancelled_at = now
    _sync_item_status(shop_order, 'CANCELLED')
    _restore_stock(shop_order)
    _shop_order_history(
        shop_order, None if system else actor, 'CANCELLED',
        f'{reason}{": " + note if note else ""}',
        old_status=old_status,
    )
    return shop_order


@transaction.atomic
def ensure_shop_orders(order):
    if order.payment_method == 'VNPAY' and order.payment_status != 'PAID':
        return []
    created = []
    items = list(
        order.order_items.select_for_update().values_list('shop_id', flat=True).distinct()
    )
    deadline = order.created_at + timedelta(hours=SHOP_CONFIRMATION_HOURS)
    for shop_id in items:
        item_statuses = list(order.order_items.filter(shop_id=shop_id).values_list('item_status', flat=True))
        legacy_status = {
            'AWAITING_PAYMENT': 'PENDING',
            'COMFIRMED': 'PROCESSING',
            'DELIVERED': 'COMPLETED',
            'RETURNED': 'COMPLETED',
        }
        statuses = [legacy_status.get(status, status) for status in item_statuses]
        active_statuses = [status for status in statuses if status != 'CANCELLED']
        initial_status = (
            min(active_statuses, key=lambda status: SHOP_ORDER_RANK.get(status, 0))
            if active_statuses else 'CANCELLED'
        )
        if initial_status == 'SHIPPING':
            pass
        elif initial_status == 'DELIVERED':
            initial_status = 'COMPLETED'
        shop_order, was_created = ShopOrder.objects.get_or_create(
            order=order,
            shop_id=shop_id,
            defaults={
                'status': initial_status,
                'confirmation_deadline': deadline,
            },
        )
        if was_created:
            _shop_order_history(
                shop_order, order.user, initial_status,
                'Buyer đặt đơn; chờ shop xác nhận.' if initial_status == 'PENDING' else 'Khởi tạo từ trạng thái phần hàng hiện có.',
                old_status='',
            )
        created.append(shop_order)
    return created


@transaction.atomic
def create_order(user, payment_method, checkout_token):
    if payment_method not in dict(Order.PAYMENT_METHOD_CHOICES):
        raise ValidationError('Phương thức thanh toán không hợp lệ.')
    Cart.objects.filter(user=user).update(updated_at=timezone.now())
    existing = Order.objects.filter(user=user, checkout_token=checkout_token).first()
    if existing:
        return existing
    address = user.addresses.select_for_update().filter(is_archived=False).order_by('-is_default', 'pk').first()
    if not address:
        raise ValidationError('Vui lòng thêm địa chỉ nhận hàng trước khi đặt hàng.')
    cart_items = list(CartItem.objects.select_for_update().filter(cart__user=user).order_by('product_id'))
    if not cart_items:
        raise ValidationError('Giỏ hàng đang trống.')
    products = {
        product.pk: product for product in Product.objects.select_for_update()
        .filter(pk__in=[item.product_id for item in cart_items]).order_by('pk')
    }
    subtotal = Decimal('0')
    for item in cart_items:
        product = products[item.product_id]
        validate_quantity(product, item.quantity)
        if product.shop.status != 'ACTIVE' or product.price <= 0:
            raise ValidationError('Sản phẩm hoặc gian hàng không còn nhận đơn.')
        subtotal += product.price * item.quantity
    if subtotal > Decimal('9999999999999.99'):
        raise ValidationError('Giá trị đơn hàng vượt giới hạn cho phép.')
    if payment_method == 'VNPAY':
        if subtotal < Decimal('5000'):
            raise ValidationError('VNPay chỉ hỗ trợ thanh toán đơn hàng từ 5.000 ₫.')
        if subtotal != subtotal.to_integral_value() or subtotal * 100 > 999999999999:
            raise ValidationError('VNPay yêu cầu số tiền nguyên VND và trong giới hạn giao dịch.')
    initial_status = 'PENDING' if payment_method == 'COD' else 'AWAITING_PAYMENT'
    payment_status = 'UNPAID' if payment_method == 'COD' else 'PENDING'
    order = Order.objects.create(
        user=user, address=address, checkout_token=checkout_token,
        order_code=f'PCM-{uuid4().hex.upper()}', subtotal=subtotal, total_amount=subtotal,
        payment_method=payment_method,
        payment_status=payment_status,
        order_status=initial_status,
    )
    for item in cart_items:
        product = products[item.product_id]
        changed = Product.objects.filter(
            pk=product.pk, status='ACTIVE', stock_quantity__gte=item.quantity,
        ).update(stock_quantity=F('stock_quantity') - item.quantity)
        if not changed:
            raise ValidationError('Tồn kho đã thay đổi. Vui lòng kiểm tra lại giỏ hàng.')
        OrderItem.objects.create(
            order=order, product=product, shop_id=product.shop_id, quantity=item.quantity,
            unit_price=product.price, subtotal=product.price * item.quantity,
            item_status=initial_status,
        )
    if payment_method == 'COD':
        for shop_order in ensure_shop_orders(order):
            _notify(
                shop_order.shop.owner,
                'Bạn có đơn hàng mới',
                f'Đơn {order.order_code} có phần hàng của shop và đang chờ bạn xác nhận.',
                'ORDER_NEW',
            )
    Payment.objects.create(
        order=order, transaction_code=uuid4().hex, payment_method=payment_method,
        amount=order.total_amount, status=payment_status,
    )
    CartItem.objects.filter(pk__in=[item.pk for item in cart_items]).delete()
    history(order, user, None, 'Buyer đặt đơn; đang chờ shop xác nhận.')
    return order


@transaction.atomic
def retry_vnpay_payment(order_id, buyer):
    Order.objects.filter(pk=order_id, user=buyer).update(updated_at=timezone.now())
    order = Order.objects.select_for_update().get(pk=order_id, user=buyer)
    if not (
        order.payment_method == 'VNPAY'
        and order.payment_status == 'FAILED'
        and order.order_status == 'CANCELLED'
    ):
        raise ValidationError('Chỉ có thể thanh toán lại đơn VNPay đã thanh toán thất bại.')

    items = list(order.order_items.select_for_update().order_by('product_id'))
    products = {
        product.pk: product for product in Product.objects.select_for_update()
        .select_related('shop').filter(pk__in=[item.product_id for item in items]).order_by('pk')
    }
    for item in items:
        product = products.get(item.product_id)
        if product is None or product.shop.status != 'ACTIVE':
            raise ValidationError('Một hoặc nhiều sản phẩm không còn được bán.')
        validate_quantity(product, item.quantity)
        reserved = Product.objects.filter(
            pk=product.pk, status='ACTIVE', stock_quantity__gte=item.quantity,
        ).update(stock_quantity=F('stock_quantity') - item.quantity)
        if not reserved:
            raise ValidationError('Tồn kho đã thay đổi. Vui lòng kiểm tra lại đơn hàng.')

    old_status = order.order_status
    order.payment_status = 'PENDING'
    order.order_status = 'AWAITING_PAYMENT'
    order.save(update_fields=['payment_status', 'order_status', 'updated_at'])
    order.order_items.update(item_status='AWAITING_PAYMENT')
    payment = Payment.objects.create(
        order=order, transaction_code=uuid4().hex, payment_method='VNPAY',
        amount=order.total_amount, status='PENDING',
    )
    history(order, buyer, old_status, 'Người mua thanh toán lại đơn hàng qua VNPay.')
    return payment


def shop_status(order, items):
    if hasattr(order, 'shop_orders') and isinstance(items, list) and items and isinstance(items[0], ShopOrder):
        statuses = [item.status for item in items]
    else:
        statuses = [item.item_status for item in items]
    if not statuses:
        return order.order_status
    mapped = {
        'COMFIRMED': 'PROCESSING',
        'DELIVERED': 'COMPLETED',
    }
    statuses = [mapped.get(status, status) for status in statuses]
    return min(statuses, key=lambda status: SHOP_ORDER_RANK.get(status, 0))


@transaction.atomic
def update_shop_order(order_id, shop, actor, new_status, *, reason='', note='',
                      carrier_name='', tracking_code=''):
    shop_order = ShopOrder.objects.select_for_update().filter(
        order_id=order_id, shop=shop,
    ).first()
    if shop_order is None:
        raise ValidationError('Đơn hàng không thuộc gian hàng của bạn.')

    old_status = shop_order.status
    now = timezone.now()
    if old_status == 'PENDING' and shop_order.confirmation_deadline <= now:
        _cancel_shop_order(
            shop_order, None, 'Hệ thống tự hủy vì shop không xác nhận trong 12 giờ.',
            system=True,
        )
        recompute_order_status(
            shop_order.order, None,
            f'Hệ thống tự hủy phần hàng của {shop.shop_name} do shop không phản hồi.',
        )
        return shop_order
    if new_status == 'PROCESSING':
        if old_status != 'PENDING':
            raise ValidationError('Phần hàng này không còn chờ shop xác nhận.')
        changed = ShopOrder.objects.filter(pk=shop_order.pk, status='PENDING').update(
            status='PROCESSING', updated_at=now,
        )
        if not changed:
            raise ValidationError('Trạng thái đơn vừa thay đổi. Vui lòng tải lại trang.')
        shop_order.status = 'PROCESSING'
        _sync_item_status(shop_order, 'PROCESSING')
        _shop_order_history(shop_order, actor, 'PROCESSING', 'Shop xác nhận nhận đơn.', old_status=old_status)
        _notify(shop_order.order.user, 'Shop đã xác nhận đơn', f'{shop.shop_name} đang chuẩn bị đơn {shop_order.order.order_code}.', 'ORDER_STATUS')
    elif new_status == 'CANCELLED':
        if old_status != 'PENDING':
            raise ValidationError('Shop chỉ có thể từ chối phần hàng trước khi xác nhận.')
        if reason not in SHOP_REJECTION_REASONS:
            raise ValidationError('Vui lòng chọn lý do từ chối đơn hợp lệ.')
        _cancel_shop_order(
            shop_order, actor, SHOP_REJECTION_REASONS[reason], note,
        )
        _notify(shop_order.order.user, 'Shop không thể nhận đơn', f'{shop.shop_name} đã từ chối phần hàng của đơn {shop_order.order.order_code}.', 'ORDER_CANCELLED')
    elif new_status == 'SHIPPING':
        if old_status != 'PROCESSING':
            raise ValidationError('Chỉ phần hàng đang xử lý mới có thể bàn giao vận chuyển.')
        if shop_order.cancellation_requests.filter(status__in=['PENDING', 'ESCALATED']).exists():
            raise ValidationError('Đang có yêu cầu hủy chờ xử lý; hãy giải quyết trước khi bàn giao.')
        if not carrier_name.strip() or not tracking_code.strip():
            raise ValidationError('Vui lòng nhập đơn vị vận chuyển và mã vận đơn.')
        changed = ShopOrder.objects.filter(pk=shop_order.pk, status='PROCESSING').update(
            status='SHIPPING',
            carrier_name=carrier_name.strip()[:100],
            tracking_code=tracking_code.strip()[:100],
            updated_at=now,
        )
        if not changed:
            raise ValidationError('Trạng thái phần hàng vừa thay đổi. Vui lòng tải lại trang.')
        shop_order.status = 'SHIPPING'
        shop_order.carrier_name = carrier_name.strip()[:100]
        shop_order.tracking_code = tracking_code.strip()[:100]
        _sync_item_status(shop_order, 'SHIPPING')
        _shop_order_history(
            shop_order, actor, 'SHIPPING',
            f'Đã bàn giao cho {shop_order.carrier_name}; mã vận đơn {shop_order.tracking_code}.',
            old_status=old_status,
        )
        _notify(shop_order.order.user, 'Đơn hàng đang được giao', f'Đơn {shop_order.order.order_code} đã bàn giao cho {shop_order.carrier_name}.', 'ORDER_STATUS')
    else:
        raise ValidationError('Thao tác trạng thái không hợp lệ.')

    recompute_order_status(
        shop_order.order, actor,
        f'{shop.shop_name} cập nhật phần hàng: {shop_order.get_status_display()}.',
    )
    return shop_order


def fulfill_order(order_id, shop, actor, new_status, cod_collected=False, note='',
                  reason='', carrier_name='', tracking_code=''):
    if new_status == 'DELIVERED':
        raise ValidationError('Trạng thái giao thành công chỉ được cập nhật bởi hãng vận chuyển.')
    return update_shop_order(
        order_id, shop, actor, new_status,
        reason=reason,
        note=note,
        carrier_name=carrier_name,
        tracking_code=tracking_code,
    )


@transaction.atomic
def request_order_cancellation(order_id, buyer, reason, note=''):
    order = Order.objects.select_for_update().filter(pk=order_id, user=buyer).first()
    if order is None:
        raise ValidationError('Không tìm thấy đơn hàng.')
    if reason not in BUYER_CANCEL_REASONS:
        raise ValidationError('Vui lòng chọn lý do hủy đơn hợp lệ.')
    if reason == 'OTHER' and not note.strip():
        raise ValidationError('Vui lòng ghi chú khi chọn lý do khác.')
    ensure_shop_orders(order)
    shop_orders = list(order.shop_orders.select_for_update().select_related('shop'))
    if not shop_orders:
        raise ValidationError('Đơn hàng không có phần hàng để hủy.')
    now = timezone.now()
    if len(shop_orders) == 1 and shop_orders[0].status != 'PENDING':
        raise ValidationError('Không thể hủy trực tiếp sau khi shop đã xác nhận đơn.')

    changed = False
    request_created = False
    for shop_order in shop_orders:
        if shop_order.status == 'PENDING':
            _cancel_shop_order(shop_order, buyer, BUYER_CANCEL_REASONS[reason], note)
            _notify(shop_order.shop.owner, 'Buyer đã hủy phần hàng', f'Buyer đã hủy phần hàng của đơn {order.order_code} trước khi shop xác nhận.', 'ORDER_CANCELLED')
            changed = True
        elif len(shop_orders) > 1 and shop_order.status == 'PROCESSING':
            pending = shop_order.cancellation_requests.filter(
                requested_by=buyer, status__in=['PENDING', 'ESCALATED'],
            ).exists()
            if pending:
                continue
            cancellation = CancellationRequest.objects.create(
                shop_order=shop_order,
                requested_by=buyer,
                reason=reason,
                note=note.strip(),
                response_deadline=now + timedelta(hours=CANCELLATION_RESPONSE_HOURS),
            )
            _shop_order_history(
                shop_order, buyer, shop_order.status,
                f'Buyer gửi yêu cầu hủy ({cancellation.get_reason_display()}). {note}'.strip(),
            )
            _notify(shop_order.shop.owner, 'Yêu cầu hủy đơn cần xử lý', f'Buyer yêu cầu hủy phần hàng của đơn {order.order_code}. Vui lòng phản hồi trong 12 giờ.', 'ORDER_CANCELLATION_REQUEST')
            request_created = True
            changed = True

    if not changed:
        raise ValidationError('Không có phần hàng nào đủ điều kiện hủy hoặc đã có yêu cầu chờ xử lý.')
    recompute_order_status(order, buyer, 'Buyer yêu cầu hủy đơn hoặc một phần đơn.')
    return {'cancelled': True, 'request_created': request_created}


@transaction.atomic
def resolve_cancellation_request(request_id, shop, actor, approve, note=''):
    if not str(request_id).isascii() or not str(request_id).isdigit():
        raise ValidationError('Yêu cầu hủy không hợp lệ.')
    cancellation = CancellationRequest.objects.select_for_update().select_related(
        'shop_order__order', 'shop_order__shop', 'requested_by',
    ).filter(pk=request_id, shop_order__shop=shop).first()
    if cancellation is None:
        raise ValidationError('Yêu cầu hủy không thuộc gian hàng của bạn.')
    if cancellation.status != 'PENDING':
        raise ValidationError('Yêu cầu hủy này đã được xử lý hoặc chuyển admin.')
    if cancellation.response_deadline <= timezone.now():
        cancellation.status = 'ESCALATED'
        cancellation.save(update_fields=['status'])
        _shop_order_history(
            cancellation.shop_order, None, cancellation.shop_order.status,
            'Hệ thống chuyển yêu cầu hủy cho admin do shop không phản hồi trong 12 giờ.',
        )
        _notify_admins('Yêu cầu hủy đơn cần admin xử lý', f'Yêu cầu hủy đơn {cancellation.shop_order.order.order_code} đã quá hạn phản hồi của shop.', 'ORDER_CANCELLATION_ESCALATED')
        return cancellation

    shop_order = ShopOrder.objects.select_for_update().get(pk=cancellation.shop_order_id)
    if shop_order.status != 'PROCESSING':
        raise ValidationError('Phần hàng không còn ở trạng thái có thể xử lý yêu cầu hủy.')
    cancellation.status = 'APPROVED' if approve else 'REJECTED'
    cancellation.resolved_by = actor
    cancellation.resolved_at = timezone.now()
    cancellation.resolution_note = note.strip()
    cancellation.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_note'])
    if approve:
        _cancel_shop_order(
            shop_order, actor, cancellation.get_reason_display(), cancellation.note,
        )
        _notify(cancellation.requested_by, 'Yêu cầu hủy đã được chấp nhận', f'{shop.shop_name} đã chấp nhận hủy phần hàng trong đơn {shop_order.order.order_code}.', 'ORDER_CANCELLED')
    else:
        _shop_order_history(
            shop_order, actor, shop_order.status,
            f'Shop từ chối yêu cầu hủy: {note.strip() or "phần hàng tiếp tục được xử lý."}',
        )
        _notify(cancellation.requested_by, 'Yêu cầu hủy chưa được chấp nhận', f'{shop.shop_name} từ chối hủy phần hàng trong đơn {shop_order.order.order_code}.', 'ORDER_CANCELLATION')
    recompute_order_status(shop_order.order, actor, 'Shop xử lý yêu cầu hủy của buyer.')
    return cancellation


@transaction.atomic
def resolve_escalated_cancellation(request_id, actor, approve, note=''):
    if not str(request_id).isascii() or not str(request_id).isdigit():
        raise ValidationError('Yêu cầu hủy không hợp lệ.')
    cancellation = CancellationRequest.objects.select_for_update().select_related(
        'shop_order__order', 'shop_order__shop', 'requested_by',
    ).filter(pk=request_id, status='ESCALATED').first()
    if cancellation is None:
        raise ValidationError('Không tìm thấy yêu cầu hủy đang chờ admin.')
    shop_order = ShopOrder.objects.select_for_update().get(pk=cancellation.shop_order_id)
    if shop_order.status != 'PROCESSING':
        raise ValidationError('Phần hàng không còn ở trạng thái có thể hủy.')
    cancellation.status = 'ADMIN_APPROVED' if approve else 'ADMIN_REJECTED'
    cancellation.resolved_by = actor
    cancellation.resolved_at = timezone.now()
    cancellation.resolution_note = note.strip()
    cancellation.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_note'])
    if approve:
        _cancel_shop_order(shop_order, actor, cancellation.get_reason_display(), cancellation.note)
    else:
        _shop_order_history(
            shop_order, actor, shop_order.status,
            f'Admin từ chối yêu cầu hủy: {note.strip() or "phần hàng tiếp tục được xử lý."}',
        )
    _notify(cancellation.requested_by, 'Yêu cầu hủy đã được admin xử lý', f'Yêu cầu hủy phần hàng của đơn {shop_order.order.order_code} đã được xử lý.', 'ORDER_CANCELLATION')
    _notify(shop_order.shop.owner, 'Yêu cầu hủy đã được admin xử lý', f'Yêu cầu hủy phần hàng của đơn {shop_order.order.order_code} đã được admin xử lý.', 'ORDER_CANCELLATION')
    recompute_order_status(shop_order.order, actor, 'Admin xử lý yêu cầu hủy được chuyển cấp.')
    return cancellation


@transaction.atomic
def expire_unconfirmed_shop_orders(now=None):
    now = now or timezone.now()
    expired_ids = list(ShopOrder.objects.filter(
        status='PENDING',
        confirmation_deadline__lte=now,
    ).values_list('pk', flat=True))
    expired_count = 0
    for shop_order_id in expired_ids:
        shop_order = ShopOrder.objects.select_for_update().select_related(
            'order__user', 'shop',
        ).get(pk=shop_order_id)
        if shop_order.status != 'PENDING' or shop_order.confirmation_deadline > now:
            continue
        old_status = shop_order.status
        changed = ShopOrder.objects.filter(
            pk=shop_order.pk,
            status='PENDING',
            confirmation_deadline__lte=now,
        ).update(status='CANCELLED', cancelled_at=now, updated_at=now)
        if not changed:
            continue
        expired_count += 1
        shop_order.status = 'CANCELLED'
        shop_order.cancelled_at = now
        _sync_item_status(shop_order, 'CANCELLED')
        _restore_stock(shop_order)
        _shop_order_history(
            shop_order, None, 'CANCELLED',
            'Hệ thống tự hủy vì shop không xác nhận trong 12 giờ.',
            old_status=old_status,
        )
        _notify(shop_order.order.user, 'Đơn hàng tự hủy', f'{shop_order.shop.shop_name} không xác nhận đơn {shop_order.order.order_code} trong 12 giờ; phần hàng đã được hủy.', 'ORDER_CANCELLED')
        _notify(shop_order.shop.owner, 'Đơn hàng đã hết hạn xác nhận', f'Phần hàng của đơn {shop_order.order.order_code} đã tự hủy do hết thời gian xác nhận.', 'ORDER_CANCELLED')
        recompute_order_status(
            shop_order.order, None,
            f'Hệ thống tự hủy phần hàng của {shop_order.shop.shop_name} do shop không phản hồi.',
        )
    return expired_count


@transaction.atomic
def escalate_expired_cancellation_requests(now=None):
    now = now or timezone.now()
    request_ids = list(CancellationRequest.objects.filter(
        status='PENDING',
        response_deadline__lte=now,
    ).values_list('pk', flat=True))
    escalated_count = 0
    for request_id in request_ids:
        cancellation = CancellationRequest.objects.select_for_update().select_related(
            'shop_order__order', 'shop_order__shop',
        ).get(pk=request_id)
        if cancellation.status != 'PENDING' or cancellation.response_deadline > now:
            continue
        cancellation.status = 'ESCALATED'
        cancellation.save(update_fields=['status'])
        escalated_count += 1
        _shop_order_history(
            cancellation.shop_order, None, cancellation.shop_order.status,
            'Hệ thống chuyển yêu cầu hủy cho admin do shop không phản hồi trong 12 giờ.',
        )
        _notify_admins('Yêu cầu hủy đơn cần admin xử lý', f'Yêu cầu hủy đơn {cancellation.shop_order.order.order_code} của shop {cancellation.shop_order.shop.shop_name} đã quá hạn.', 'ORDER_CANCELLATION_ESCALATED')
    return escalated_count


@transaction.atomic
def mark_carrier_delivered(*, provider, event_id, tracking_code):
    try:
        with transaction.atomic():
            CarrierWebhookEvent.objects.create(
                provider=provider,
                event_id=event_id,
                tracking_code=tracking_code,
            )
    except IntegrityError:
        return 'duplicate'
    shop_order = ShopOrder.objects.select_for_update().select_related(
        'order__user', 'shop',
    ).filter(tracking_code=tracking_code).first()
    if shop_order is None:
        raise ValidationError('Không tìm thấy mã vận đơn.')
    if shop_order.status != 'SHIPPING':
        return 'ignored'
    now = timezone.now()
    old_status = shop_order.status
    changed = ShopOrder.objects.filter(pk=shop_order.pk, status='SHIPPING').update(
        status='DELIVERED', delivered_at=now, updated_at=now,
    )
    if not changed:
        return 'ignored'
    shop_order.status = 'DELIVERED'
    shop_order.delivered_at = now
    _sync_item_status(shop_order, 'DELIVERED')
    _shop_order_history(
        shop_order, None, 'DELIVERED',
        f'{provider} xác nhận giao hàng thành công; buyer có 3 ngày để xác nhận đã nhận.',
        old_status=old_status,
    )
    for item in OrderItem.objects.filter(order_id=shop_order.order_id, shop_id=shop_order.shop_id):
        Product.objects.filter(pk=item.product_id).update(
            sold_quantity=F('sold_quantity') + item.quantity,
        )
    _notify(shop_order.order.user, 'Đơn hàng đã giao thành công', f'Đơn {shop_order.order.order_code} đã được giao. Vui lòng xác nhận đã nhận hàng trong 3 ngày.', 'ORDER_DELIVERED')
    _notify(shop_order.shop.owner, 'Đơn hàng đã giao thành công', f'Đơn {shop_order.order.order_code} đã được đơn vị vận chuyển giao thành công.', 'ORDER_DELIVERED')
    recompute_order_status(shop_order.order, None, 'Đơn vị vận chuyển xác nhận giao thành công.')
    return 'delivered'


@transaction.atomic
def confirm_order_received(order_id, buyer):
    order = Order.objects.select_for_update().filter(pk=order_id, user=buyer).first()
    if order is None:
        raise ValidationError('Không tìm thấy đơn hàng.')
    shop_orders = list(order.shop_orders.select_for_update().filter(status='DELIVERED'))
    if not shop_orders:
        raise ValidationError('Không có phần hàng nào đang chờ xác nhận đã nhận.')
    now = timezone.now()
    for shop_order in shop_orders:
        changed = ShopOrder.objects.filter(pk=shop_order.pk, status='DELIVERED').update(
            status='COMPLETED', completed_at=now, updated_at=now,
        )
        if changed:
            _sync_item_status(shop_order, 'COMPLETED')
            _shop_order_history(
                shop_order, buyer, 'COMPLETED', 'Buyer xác nhận đã nhận hàng.',
                old_status='DELIVERED',
            )
            _notify(shop_order.shop.owner, 'Buyer xác nhận đã nhận hàng', f'Đơn {order.order_code} đã được buyer xác nhận.', 'ORDER_COMPLETED')
    recompute_order_status(order, buyer, 'Buyer xác nhận đã nhận hàng.')
    return order


@transaction.atomic
def complete_delivered_shop_orders(now=None):
    now = now or timezone.now()
    shop_order_ids = list(ShopOrder.objects.filter(
        status='DELIVERED',
        delivered_at__lte=now - timedelta(days=BUYER_COMPLETION_DAYS),
    ).values_list('pk', flat=True))
    completed_count = 0
    for shop_order_id in shop_order_ids:
        shop_order = ShopOrder.objects.select_for_update().select_related(
            'order__user', 'shop',
        ).get(pk=shop_order_id)
        if (
            shop_order.status != 'DELIVERED'
            or shop_order.delivered_at > now - timedelta(days=BUYER_COMPLETION_DAYS)
        ):
            continue
        changed = ShopOrder.objects.filter(pk=shop_order.pk, status='DELIVERED').update(
            status='COMPLETED', completed_at=now, updated_at=now,
        )
        if not changed:
            continue
        completed_count += 1
        shop_order.status = 'COMPLETED'
        shop_order.completed_at = now
        _sync_item_status(shop_order, 'COMPLETED')
        _shop_order_history(
            shop_order, None, 'COMPLETED',
            'Hệ thống tự hoàn thành sau 3 ngày vì buyer chưa xác nhận.',
            old_status='DELIVERED',
        )
        _notify(shop_order.order.user, 'Đơn hàng đã hoàn thành', f'Đơn {shop_order.order.order_code} tự hoàn thành sau 3 ngày kể từ khi giao thành công.', 'ORDER_COMPLETED')
        _notify(shop_order.shop.owner, 'Đơn hàng đã hoàn thành', f'Đơn {shop_order.order.order_code} đã được tự hoàn thành.', 'ORDER_COMPLETED')
        recompute_order_status(shop_order.order, None, 'Hệ thống tự hoàn thành sau thời hạn xác nhận của buyer.')
    return completed_count


def process_order_timeouts(now=None):
    now = now or timezone.now()
    return {
        'shop_orders': expire_unconfirmed_shop_orders(now),
        'cancellation_requests': escalate_expired_cancellation_requests(now),
        'delivered_shop_orders': complete_delivered_shop_orders(now),
    }


def verify_carrier_webhook(raw_body, timestamp, signature, *, now=None):
    secret = getattr(settings, 'CARRIER_WEBHOOK_SECRET', '')
    if not secret:
        raise ValidationError('Tích hợp vận chuyển chưa được cấu hình.')
    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError):
        raise ValidationError('Thiếu thời gian ký webhook hợp lệ.')
    now = now or timezone.now()
    if abs(int(now.timestamp()) - sent_at) > 300:
        raise ValidationError('Webhook đã hết hạn.')
    expected = hmac.new(
        secret.encode(),
        timestamp.encode() + b'.' + raw_body,
        hashlib.sha256,
    ).hexdigest()
    supplied = signature.removeprefix('sha256=')
    if not hmac.compare_digest(expected, supplied):
        raise ValidationError('Chữ ký webhook không hợp lệ.')
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValidationError('Nội dung webhook không phải JSON hợp lệ.')
    required = ('provider', 'event_id', 'tracking_code', 'status')
    if not isinstance(payload, dict) or any(
        not isinstance(payload.get(key), str) or not payload[key].strip()
        for key in required
    ):
        raise ValidationError('Webhook thiếu trường bắt buộc.')
    if payload['status'] != 'DELIVERED':
        raise ValidationError('Webhook chỉ chấp nhận trạng thái giao thành công.')
    return payload
