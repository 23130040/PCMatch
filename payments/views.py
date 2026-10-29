import logging

from django.contrib import messages
from django.db import DatabaseError
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET

from users.views import buyer_required
from .models import Payment
from .services import process_notification
from .vnpay import verify

logger = logging.getLogger(__name__)


@require_GET
def vnpay_ipn(request):
    if not verify(request.GET):
        return JsonResponse({'RspCode': '97', 'Message': 'Invalid signature'})
    try:
        code, message = process_notification(request.GET)
    except DatabaseError:
        logger.exception('VNPay IPN could not be persisted')
        code, message = '99', 'Please retry'
    return JsonResponse({'RspCode': code, 'Message': message})


@require_GET
@buyer_required
def vnpay_return(request):
    if not verify(request.GET):
        return HttpResponseBadRequest('Kết quả VNPay có chữ ký không hợp lệ.')
    payment = get_object_or_404(
        Payment.objects.select_related('order'), transaction_code=request.GET.get('vnp_TxnRef'),
        payment_method='VNPAY', order__user=request.user,
    )
    try:
        code, message = process_notification(request.GET)

        if code != '00':
            logger.warning(
                'VNPay RETURN not processed: code=%s, message=%s, '
                'txn_ref=%s, response_code=%s, transaction_status=%s',
                code,
                message,
                request.GET.get('vnp_TxnRef'),
                request.GET.get('vnp_ResponseCode'),
                request.GET.get('vnp_TransactionStatus'),
            )
        else:
            logger.info(
                'VNPay RETURN processed successfully: txn_ref=%s',
                request.GET.get('vnp_TxnRef'),
            )

    except DatabaseError:
        logger.exception('VNPay return could not be persisted')
    payment.refresh_from_db()
    payment.order.refresh_from_db()
    if payment.status == 'PAID':
        messages.success(request, 'Thanh toán thành công. Đơn hàng đang chờ admin xác nhận.')
    elif payment.status == 'FAILED':
        messages.error(request, 'Thanh toán thất bại. Đơn hàng đã được hủy và hoàn tồn kho.')
    else:
        messages.info(request, 'Đang chờ VNPay xác nhận giao dịch. Vui lòng tải lại chi tiết đơn sau ít phút.')
    return redirect(f'{reverse("buyer_order")}?id={payment.order.order_code}')
