from decimal import Decimal
from uuid import uuid4

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from carts.models import Cart, CartItem
from carts.services import validate_quantity
from payments.models import Payment
from products.models import Product
from .models import Order, OrderItem, OrderStatusHistory


def checkout_token(user):
    return signing.dumps({'user': user.pk, 'nonce': str(uuid4())}, salt='checkout')


def history(order, actor, old_status, note=''):
    OrderStatusHistory.objects.create(
        order=order, changed_by=actor, old_status=old_status,
        new_status=order.order_status, note=note,
    )


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
    if payment_method == 'VNPAY' and (subtotal != subtotal.to_integral_value() or subtotal * 100 > 999999999999):
        raise ValidationError('VNPay yêu cầu số tiền nguyên VND và trong giới hạn giao dịch.')
    is_cod = payment_method == 'COD'
    order = Order.objects.create(
        user=user, address=address, checkout_token=checkout_token,
        order_code=f'PCM-{uuid4().hex.upper()}', subtotal=subtotal, total_amount=subtotal,
        payment_method=payment_method, payment_status='UNPAID' if is_cod else 'PENDING',
        order_status='PENDING' if is_cod else 'AWAITING_PAYMENT',
    )
    for item in cart_items:
        product = products[item.product_id]
        changed = Product.objects.filter(pk=product.pk, status='ACTIVE', stock_quantity__gte=item.quantity).update(
            stock_quantity=F('stock_quantity') - item.quantity,
        )
        if not changed:
            raise ValidationError('Tồn kho đã thay đổi. Vui lòng kiểm tra lại giỏ hàng.')
        OrderItem.objects.create(
            order=order, product=product, shop_id=product.shop_id, quantity=item.quantity,
            unit_price=product.price, subtotal=product.price * item.quantity,
            item_status=order.order_status,
        )
    Payment.objects.create(
        order=order, transaction_code=uuid4().hex, payment_method=payment_method,
        amount=order.total_amount, status=order.payment_status,
    )
    CartItem.objects.filter(pk__in=[item.pk for item in cart_items]).delete()
    history(order, user, None, 'Người mua đặt hàng.')
    return order


@transaction.atomic
def confirm_order(order_id, actor):
    Order.objects.filter(pk=order_id).update(updated_at=timezone.now())
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.order_status != 'PENDING':
        raise ValidationError('Chỉ xác nhận đơn đang chờ admin duyệt.')
    if order.payment_method == 'VNPAY' and order.payment_status != 'PAID':
        raise ValidationError('Đơn VNPay phải thanh toán thành công trước khi xác nhận.')
    old_status = order.order_status
    order.order_status = 'COMFIRMED'  # Keep the existing database status code.
    order.save(update_fields=['order_status', 'updated_at'])
    order.order_items.update(item_status='COMFIRMED')
    history(order, actor, old_status, 'Admin xác nhận và chuyển cho shop xử lý.')
    return order


FULFILLMENT_STATES = ['COMFIRMED', 'PROCESSING', 'SHIPPING', 'DELIVERED']


def shop_status(order, items):
    if order.order_status not in FULFILLMENT_STATES:
        return order.order_status
    statuses = [item.item_status for item in items]
    if statuses and all(status in FULFILLMENT_STATES for status in statuses):
        return min(statuses, key=FULFILLMENT_STATES.index)
    return order.order_status


@transaction.atomic
def fulfill_order(order_id, shop, actor, new_status, cod_collected=False, note=''):
    Order.objects.filter(pk=order_id).update(updated_at=timezone.now())
    order = Order.objects.select_for_update().get(pk=order_id)
    items = list(order.order_items.select_for_update().filter(shop=shop))
    if not items:
        raise ValidationError('Đơn hàng không thuộc gian hàng của bạn.')
    current = shop_status(order, items)
    transitions = {'COMFIRMED': 'PROCESSING', 'PROCESSING': 'SHIPPING', 'SHIPPING': 'DELIVERED'}
    if transitions.get(current) != new_status:
        raise ValidationError('Cần admin xác nhận trước và xử lý đúng thứ tự các bước.')
    if order.payment_method == 'VNPAY' and order.payment_status != 'PAID':
        raise ValidationError('Đơn VNPay chưa được thanh toán.')
    if new_status == 'DELIVERED' and order.payment_method == 'COD' and not cod_collected:
        raise ValidationError('Vui lòng xác nhận đã thu đủ tiền COD trước khi hoàn thành.')
    order.order_items.filter(shop=shop).update(item_status=new_status)
    if new_status == 'DELIVERED':
        for item in items:
            Product.objects.filter(pk=item.product_id).update(sold_quantity=F('sold_quantity') + item.quantity)
    old_status = order.order_status
    all_statuses = list(order.order_items.values_list('item_status', flat=True))
    order.order_status = min(all_statuses, key=FULFILLMENT_STATES.index)
    if order.order_status == 'DELIVERED' and order.payment_method == 'COD':
        order.payment_status = 'PAID'
        order.payments.filter(payment_method='COD').exclude(status='PAID').update(status='PAID', paid_at=timezone.now())
    order.save(update_fields=['order_status', 'payment_status', 'updated_at'])
    history(order, actor, old_status, f'{shop.shop_name}: {new_status}. {note}')
    return order
