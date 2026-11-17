from datetime import datetime
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import F

from orders.models import Order
from orders.services import _notify, ensure_shop_orders, history
from products.models import Product
from django.core.exceptions import ValidationError
from .models import Payment, Wallet, WalletTransaction

@transaction.atomic
def process_notification(params):
    candidate = Payment.objects.filter(transaction_code=params.get('vnp_TxnRef'), payment_method='VNPAY').first()
    if candidate is None:
        return '01', 'Order not found'
    Order.objects.filter(pk=candidate.order_id).update(order_status=F('order_status'))
    order = Order.objects.select_for_update().get(pk=candidate.order_id)
    payment = Payment.objects.select_for_update().get(pk=candidate.pk)
    try:
        amount = int(params.get('vnp_Amount', ''))
    except (TypeError, ValueError):
        return '04', 'Invalid amount'

    if (
            (
                    'vnp_CurrCode' in params
                    and params.get('vnp_CurrCode') != 'VND'
            )
            or payment.payment_method != 'VNPAY'
            or order.payment_method != 'VNPAY'
            or amount != payment.amount * 100
            or payment.amount != order.total_amount
    ):
        return '04', 'Invalid amount'

    if payment.status != 'PENDING' or order.order_status != 'AWAITING_PAYMENT':
        return '02', 'Order already confirmed'
    success = params.get('vnp_ResponseCode') == '00' and params.get('vnp_TransactionStatus') == '00'
    paid_at = None
    if success:
        try:
            paid_at = datetime.strptime(params.get('vnp_PayDate', ''), '%Y%m%d%H%M%S').replace(tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))
        except (TypeError, ValueError):
            return '99', 'Invalid payment date'
        if not params.get('vnp_TransactionNo'):
            return '99', 'Missing transaction number'
    elif not params.get('vnp_ResponseCode') or not params.get('vnp_TransactionStatus'):
        return '99', 'Missing transaction result'
    elif params.get('vnp_TransactionStatus') != '02' or params.get('vnp_ResponseCode') in {'00', '07'}:
        return '99', 'Transaction requires reconciliation'
    old_status = order.order_status
    payment.status = order.payment_status = 'PAID' if success else 'FAILED'
    payment.paid_at = paid_at
    payment.gateway_transaction_no = params.get('vnp_TransactionNo', '')
    payment.save(update_fields=['status', 'paid_at', 'gateway_transaction_no'])
    order.order_status = 'PENDING' if success else 'CANCELLED'
    if not success:
        for item in order.order_items.order_by('product_id'):
            Product.objects.filter(pk=item.product_id).update(stock_quantity=F('stock_quantity') + item.quantity)
    order.order_items.update(item_status=order.order_status)
    order.save(update_fields=['payment_status', 'order_status', 'updated_at'])
    if success:
        for shop_order in ensure_shop_orders(order):
            _notify(
                shop_order.shop.owner,
                'Bạn có đơn hàng mới',
                f'Đơn {order.order_code} có phần hàng của shop và đang chờ bạn xác nhận.',
                'ORDER_NEW',
            )
    history(order, order.user, old_status, 'VNPay IPN: thanh toán thành công.' if success else 'VNPay IPN: thanh toán thất bại; đã hoàn tồn kho.')
    return '00', 'Confirm success'

@transaction.atomic
def refund_order_to_wallet(order):

    if (
        order.payment_method != 'VNPAY'
        or order.payment_status != 'PAID'
        or order.order_status != 'CANCELLED'
    ):
        return None

    from orders.models import Order

    order = Order.objects.select_for_update().get(
        pk=order.pk
    )

    if (
        order.payment_method != 'VNPAY'
        or order.payment_status != 'PAID'
        or order.order_status != 'CANCELLED'
    ):
        return None

    existing = WalletTransaction.objects.filter(
        order=order,
        transaction_type='ORDER_REFUND',
    ).first()

    if existing:
        return existing

    payment = Payment.objects.select_for_update().filter(
        order=order,
        payment_method='VNPAY',
        status='PAID',
    ).order_by('-created_at').first()

    if payment is None:
        raise ValidationError(
            'Không tìm thấy giao dịch VNPay đã thanh toán thành công.'
        )

    refund_amount = payment.amount

    if refund_amount <= 0 or refund_amount != order.total_amount:
        raise ValidationError(
            'Số tiền hoàn không hợp lệ.'
        )

    wallet, created = Wallet.objects.get_or_create(
        user=order.user
    )

    wallet = Wallet.objects.select_for_update().get(
        pk=wallet.pk
    )

    wallet.balance += refund_amount
    wallet.save(update_fields=['balance', 'updated_at'])

    transaction_record = WalletTransaction.objects.create(
        wallet=wallet,
        order=order,
        transaction_type='ORDER_REFUND',
        amount=refund_amount,
        balance_after=wallet.balance,
        description=(
            f'Hoàn tiền đơn hàng {order.order_code} '
            'do đơn hàng đã được hủy thành công.'
        ),
    )

    payment.status = 'REFUNDED'
    payment.save(update_fields=['status'])

    order.payment_status = 'REFUNDED'
    order.save(update_fields=['payment_status', 'updated_at'])

    return transaction_record
