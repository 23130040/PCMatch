import logging
import smtplib
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import get_connection, send_mail
from django.utils import timezone
from django.utils.crypto import get_random_string

from .models import BuyerEmailOTP


logger = logging.getLogger(__name__)
BUYER_OTP_TTL = timedelta(minutes=3)
BUYER_OTP_MAX_ATTEMPTS = 5


class BuyerOTPDeliveryError(Exception):
    pass


def issue_buyer_email_otp(user):
    if not all((
        settings.EMAIL_HOST,
        settings.EMAIL_HOST_USER,
        settings.EMAIL_HOST_PASSWORD,
        settings.DEFAULT_FROM_EMAIL,
    )):
        raise BuyerOTPDeliveryError(
            'Email chưa được cấu hình. Vui lòng cấu hình SMTP rồi thử gửi lại.'
        )

    code = get_random_string(6, allowed_chars='0123456789')
    otp, _ = BuyerEmailOTP.objects.update_or_create(
        user=user,
        defaults={
            'code_hash': make_password(code),
            'expires_at': timezone.now() + BUYER_OTP_TTL,
            'failed_attempts': 0,
            'consumed_at': None,
        },
    )

    try:
        sent_count = send_mail(
            'Mã OTP xác thực tài khoản PCMatch',
            f'Mã xác thực email của bạn là {code}. Mã có hiệu lực trong 3 phút.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
            connection=get_connection(backend=settings.BUYER_OTP_EMAIL_BACKEND),
        )
        if sent_count != 1:
            otp.delete()
            logger.error('SMTP did not accept the buyer email OTP for user %s.', user.pk)
            raise BuyerOTPDeliveryError(
                'Chưa gửi được email xác thực. Vui lòng kiểm tra địa chỉ email và thử lại.'
            )
    except (OSError, smtplib.SMTPException) as error:
        otp.delete()
        logger.exception('Could not send buyer email OTP to user %s.', user.pk)
        raise BuyerOTPDeliveryError(
            'Chưa gửi được email xác thực. Vui lòng kiểm tra cấu hình email và thử lại.'
        ) from error


def verify_buyer_email_otp(otp, code):
    if otp.consumed_at is not None or otp.expires_at <= timezone.now():
        return 'expired'
    if not check_password(code, otp.code_hash):
        otp.failed_attempts += 1
        if otp.failed_attempts >= BUYER_OTP_MAX_ATTEMPTS:
            otp.delete()
            return 'locked'
        otp.save(update_fields=['failed_attempts', 'updated_at'])
        return 'invalid'

    otp.consumed_at = timezone.now()
    otp.save(update_fields=['consumed_at', 'updated_at'])
    return 'valid'
