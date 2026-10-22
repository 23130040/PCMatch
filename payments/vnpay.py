import hashlib
import hmac
from datetime import timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


def configured():
    return bool(settings.VNPAY_TMN_CODE and settings.VNPAY_HASH_SECRET and settings.VNPAY_RETURN_URL)


def signature(params):
    query = urlencode(sorted(params.items()))
    return hmac.new(settings.VNPAY_HASH_SECRET.encode(), query.encode(), hashlib.sha512).hexdigest()


def verify(query):
    if not configured():
        return False
    if any(len(query.getlist(key)) != 1 for key in query if key.startswith('vnp_')):
        return False
    params = {key: value for key, value in query.items() if key.startswith('vnp_') and key not in {'vnp_SecureHash', 'vnp_SecureHashType'}}
    return (
        params.get('vnp_TmnCode') == settings.VNPAY_TMN_CODE
        and hmac.compare_digest(signature(params), query.get('vnp_SecureHash', '').lower())
    )


def payment_url(payment, ip_address):
    if not configured():
        raise ValidationError('VNPay chưa được cấu hình. Vui lòng chọn COD hoặc liên hệ quản trị viên.')
    created = timezone.localtime(payment.created_at, ZoneInfo('Asia/Ho_Chi_Minh'))
    expires = created + timedelta(minutes=15)
    if timezone.now() >= expires:
        raise ValidationError('Liên kết VNPay đã hết hạn. Vui lòng liên hệ hỗ trợ để đối soát giao dịch.')
    params = {
        'vnp_Version': '2.1.0', 'vnp_Command': 'pay',
        'vnp_TmnCode': settings.VNPAY_TMN_CODE,
        'vnp_Amount': str(int(payment.amount * 100)), 'vnp_CurrCode': 'VND',
        'vnp_TxnRef': payment.transaction_code,
        'vnp_OrderInfo': f'Thanh toan {payment.order.order_code}',
        'vnp_OrderType': 'other', 'vnp_Locale': 'vn',
        'vnp_ReturnUrl': settings.VNPAY_RETURN_URL, 'vnp_IpAddr': ip_address,
        'vnp_CreateDate': created.strftime('%Y%m%d%H%M%S'),
        'vnp_ExpireDate': expires.strftime('%Y%m%d%H%M%S'),
    }
    return f'{settings.VNPAY_PAYMENT_URL}?{urlencode(sorted(params.items()))}&vnp_SecureHash={signature(params)}'
