import logging
import smtplib
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import get_connection, send_mail
from django.db import DatabaseError, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string

from users.models import EmailVerificationSend, EmailVerificationToken


logger = logging.getLogger(__name__)
EMAIL_SEND_WINDOW = timedelta(hours=1)
EMAIL_SEND_COOLDOWN = timedelta(seconds=60)
EMAIL_SEND_MAX_PER_WINDOW = 5
IP_SEND_MAX_PER_WINDOW = 20
EMAIL_TOKEN_TTL = timedelta(days=1)


class SellerVerificationError(Exception):
    pass


class SellerPasswordResetError(Exception):
    pass


def send_seller_password_reset_email(email, link, *, changed=False):
    subject = (
        'Mật khẩu PCMatch đã được thay đổi'
        if changed else 'Đặt lại mật khẩu PCMatch'
    )
    body = (
        'Mật khẩu tài khoản seller PCMatch của bạn vừa được thay đổi. '
        'Nếu bạn không thực hiện thay đổi này, hãy liên hệ bộ phận hỗ trợ ngay.'
        if changed else
        'Bạn đã yêu cầu đặt lại mật khẩu tài khoản seller PCMatch. '
        'Truy cập liên kết sau trong vòng 1 giờ để đặt mật khẩu mới:\n'
        f'{link}\n\n'
        'Nếu bạn không yêu cầu thay đổi này, hãy bỏ qua email.'
    )
    try:
        sent_count = send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
            connection=get_connection(backend=settings.EMAIL_BACKEND),
        )
    except (
        AttributeError,
        ImportError,
        ImproperlyConfigured,
        OSError,
        ValueError,
        smtplib.SMTPException,
    ) as error:
        logger.exception('Could not send seller password recovery email.')
        raise SellerPasswordResetError(
            'Chưa gửi được email. Vui lòng kiểm tra cấu hình SMTP và thử lại.'
        ) from error

    if sent_count != 1:
        logger.error('SMTP did not accept a seller password recovery email.')
        raise SellerPasswordResetError(
            'Chưa gửi được email. Vui lòng kiểm tra địa chỉ email và thử lại.'
        )


def send_seller_draft_verification_email(email, token):
    link = (
        f'{settings.SHOP_PUBLIC_BASE_URL}'
        f'{reverse("shop_verify_email_confirm", args=[token])}'
    )
    try:
        sent_count = send_mail(
            'Xác thực email đăng ký người bán PCMatch',
            f'Bấm vào liên kết sau để xác thực email và tiếp tục đăng ký shop:\n{link}\n'
            'Liên kết có hiệu lực trong 24 giờ và chỉ dùng một lần.',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
            connection=get_connection(backend=settings.EMAIL_BACKEND),
        )
    except (
        AttributeError,
        ImportError,
        ImproperlyConfigured,
        OSError,
        ValueError,
        smtplib.SMTPException,
    ) as error:
        logger.exception('Could not send seller draft verification email.')
        raise SellerVerificationError(
            'Chưa gửi được email xác thực. Vui lòng kiểm tra cấu hình SMTP và thử lại.'
        ) from error

    if sent_count != 1:
        logger.error('SMTP did not accept a seller draft verification email.')
        raise SellerVerificationError(
            'Chưa gửi được email xác thực. Vui lòng kiểm tra địa chỉ email và thử lại.'
        )


def send_seller_verification_email(request, account):
    email = account.email.strip().lower()
    now = timezone.now()
    window_start = now - EMAIL_SEND_WINDOW
    ip_address = request.META.get('REMOTE_ADDR') or None
    sends_by_email = EmailVerificationSend.objects.filter(
        email__iexact=email,
        created_at__gte=window_start,
    )
    # Development testing only: temporarily disable resend throttling.
    # Re-enable these checks before deploying or exposing this server publicly.
    # if sends_by_email.filter(created_at__gte=now - EMAIL_SEND_COOLDOWN).exists():
    #     raise SellerVerificationError(
    #         'Vui lòng chờ ít nhất 60 giây trước khi gửi lại email xác thực.'
    #     )
    # if sends_by_email.count() >= EMAIL_SEND_MAX_PER_WINDOW:
    #     raise SellerVerificationError(
    #         'Email này đã yêu cầu quá nhiều mã xác thực. Vui lòng thử lại sau.'
    #     )
    # if ip_address and EmailVerificationSend.objects.filter(
    #     ip_address=ip_address,
    #     created_at__gte=window_start,
    # ).count() >= IP_SEND_MAX_PER_WINDOW:
    #     raise SellerVerificationError(
    #         'Thiết bị này đã yêu cầu quá nhiều email xác thực. Vui lòng thử lại sau.'
    #     )

    try:
        with transaction.atomic():
            EmailVerificationSend.objects.create(email=email, ip_address=ip_address)
            token = EmailVerificationToken.objects.create(
                user=account,
                token=get_random_string(48),
                expires_at=now + EMAIL_TOKEN_TTL,
            )
    except DatabaseError as error:
        logger.exception('Could not create seller verification token for user %s.', account.pk)
        raise SellerVerificationError(
            'Chưa tạo được liên kết xác thực. Vui lòng thử lại sau.'
        ) from error

    link = (
        f'{settings.SHOP_PUBLIC_BASE_URL}'
        f'{reverse("shop_verify_email_confirm", args=[token.token])}'
    )
    try:
        sent_count = send_mail(
            'Kích hoạt tài khoản người bán PCMatch',
            f'Vui lòng bấm vào liên kết sau để xác thực email người bán PCMatch:\n{link}\n'
            f'Liên kết có hiệu lực trong 24 giờ và chỉ dùng một lần.',
            settings.DEFAULT_FROM_EMAIL,
            [account.email],
            fail_silently=False,
            connection=get_connection(backend=settings.EMAIL_BACKEND),
        )
    except (
        AttributeError,
        ImportError,
        ImproperlyConfigured,
        OSError,
        ValueError,
        smtplib.SMTPException,
    ) as error:
        token.delete()
        logger.exception('Could not send seller verification email to user %s.', account.pk)
        raise SellerVerificationError(
            'Chưa gửi được email xác thực. Vui lòng kiểm tra cấu hình email và thử lại.'
        ) from error

    if sent_count != 1:
        token.delete()
        logger.error('SMTP did not accept seller verification email for user %s.', account.pk)
        raise SellerVerificationError(
            'Chưa gửi được email xác thực. Vui lòng kiểm tra địa chỉ email và thử lại.'
        )

    EmailVerificationToken.objects.filter(
        user=account,
        verified_at__isnull=True,
        invalidated_at__isnull=True,
    ).exclude(pk=token.pk).update(invalidated_at=timezone.now())
