from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, InvalidOperation
import logging
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.hashers import check_password, make_password
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import DatabaseError, transaction
from django.db.models import Max, Prefetch, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from orders.models import CancellationRequest, Order, OrderItem, Return, ShopOrder, ShopOrderHistory
from orders.services import (
    ensure_shop_orders,
    process_order_timeouts,
    resolve_cancellation_request,
    update_shop_order,
)
from products.models import Brand, Category, Product, ProductQuestion
from products.forms import ProductAnswerForm
from products.services import append_question_message, conversation_messages
from django.db.models.functions import Coalesce
from users.models import EmailVerificationToken, PasswordResetToken, User
from users.views import finish_auth_login, is_active_seller, safe_auth_next
from users.forms import SellerAccountProfileForm

from .email_services import (
    SellerPasswordResetError,
    SellerVerificationError,
    send_seller_password_reset_email,
    send_seller_draft_verification_email,
    send_seller_verification_email,
)
from .forms import (
    SellerForgotPasswordForm,
    SellerRegisterForm,
    SellerSetPasswordForm,
    SellerVerificationEmailForm,
    ShopLegalForm,
    ShopLoginForm,
    ShopProfileForm,
    ShopSettingsForm,
)
from .models import Shop


shop_required = user_passes_test(is_active_seller, login_url=reverse_lazy('shop_login'))
logger = logging.getLogger(__name__)

SELLER_DRAFT_SESSION_KEY = 'shop_seller_registration'
SELLER_EMAIL_TOKEN_TTL = timedelta(hours=24)


def _owned_shop(user):
    return Shop.objects.filter(owner=user).order_by('pk').first()


def shop_login(request):
    destination = safe_auth_next(request, 'shop_dashboard')
    form = ShopLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        identifier = form.cleaned_data['username'].strip()
        found = User.objects.filter(email__iexact=identifier).first()
        account = authenticate(
            request,
            username=found.username if found else identifier,
            password=form.cleaned_data['password'],
        )
        if account is None:
            form.add_error(None, 'Tên tài khoản hoặc mật khẩu không đúng, hoặc tài khoản đã bị khóa.')
        elif account.role == 'SELLER' and not account.email_verified:
            form.add_error(None, 'Email chưa được xác thực. Vui lòng gửi lại liên kết kích hoạt.')
        elif not is_active_seller(account):
            form.add_error(None, 'Tài khoản không thuộc khu vực người bán.')
        else:
            login(request, account)
            return finish_auth_login(request, destination)
    return render(request, 'shop/login.html', {
        'page_name': 'login',
        'page_section': 'shop',
        'page_title': 'Đăng nhập',
        'form': form,
        'next': destination,
    })


@require_http_methods(['GET', 'POST'])
def shop_forgot_password(request):
    form = SellerForgotPasswordForm(request.POST or None)
    submitted = False
    if request.method == 'POST' and form.is_valid():
        submitted = True
        matching_accounts = list(
            User.objects.filter(
                email__iexact=form.cleaned_data['email'],
                role='SELLER',
                is_staff=False,
                is_superuser=False,
            ).order_by('pk')[:2]
        )
        account = matching_accounts[0] if len(matching_accounts) == 1 else None
        if account is not None:
            token = get_random_string(48)
            reset_url = request.build_absolute_uri(
                reverse('shop_reset_password', args=[token])
            )
            try:
                with transaction.atomic():
                    account = User.objects.select_for_update().filter(
                        pk=account.pk,
                        email__iexact=form.cleaned_data['email'],
                        role='SELLER',
                        is_staff=False,
                        is_superuser=False,
                    ).first()
                    if account is not None:
                        PasswordResetToken.objects.filter(
                            user=account, used=False,
                        ).update(used=True)
                        PasswordResetToken.objects.create(
                            user=account,
                            token=token,
                            expires_at=timezone.now() + timedelta(hours=1),
                        )
                        send_seller_password_reset_email(account.email, reset_url)
            except SellerPasswordResetError as error:
                submitted = False
                messages.error(request, str(error))
        return render(request, 'shop/forgot_password.html', {
            'page_name': 'forgot-password',
            'page_section': 'shop',
            'page_title': 'Khôi phục mật khẩu',
            'form': form,
            'submitted': submitted,
        })
    return render(request, 'shop/forgot_password.html', {
        'page_name': 'forgot-password',
        'page_section': 'shop',
        'page_title': 'Khôi phục mật khẩu',
        'form': form,
        'submitted': submitted,
    })


@require_http_methods(['GET', 'POST'])
def shop_reset_password(request, token):
    record = (
        PasswordResetToken.objects.filter(
            token=token,
            used=False,
            expires_at__gt=timezone.now(),
            user__role='SELLER',
            user__is_staff=False,
            user__is_superuser=False,
        )
        .select_related('user')
        .first()
    )
    if record is None:
        messages.error(request, 'Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.')
        return redirect('shop_login')

    form = SellerSetPasswordForm(request.POST or None, user=record.user)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            account = User.objects.select_for_update().filter(
                pk=record.user_id,
                role='SELLER',
                is_staff=False,
                is_superuser=False,
            ).first()
            record = None if account is None else (
                PasswordResetToken.objects.select_for_update()
                .filter(
                    pk=record.pk,
                    user=account,
                    used=False,
                    expires_at__gt=timezone.now(),
                )
                .first()
            )
            if record is None:
                messages.error(request, 'Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.')
                return redirect('shop_login')
            account.set_password(form.cleaned_data['password1'])
            account.save(update_fields=['password'])
            PasswordResetToken.objects.filter(user=account, used=False).update(used=True)

        try:
            send_seller_password_reset_email(account.email, '', changed=True)
        except SellerPasswordResetError as error:
            messages.error(
                request,
                f'Mật khẩu đã được thay đổi nhưng chưa gửi được email thông báo. {error}',
            )
        else:
            messages.success(request, 'Mật khẩu đã được thay đổi. Vui lòng đăng nhập lại.')
        return redirect('shop_login')

    return render(request, 'shop/reset_password.html', {
        'page_name': 'reset-password',
        'page_section': 'shop',
        'page_title': 'Đặt lại mật khẩu',
        'form': form,
    })


def shop_register(request):
    if is_active_seller(request.user) and _owned_shop(request.user):
        return redirect('shop_dashboard')
    form = SellerRegisterForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            request.session[SELLER_DRAFT_SESSION_KEY] = {
                'username': form.cleaned_data['username'],
                'email': form.cleaned_data['email'],
                'password': make_password(form.cleaned_data['password1']),
                'email_verified': False,
            }
            return redirect('shop_verify_email')
    return render(request, 'shop/register.html', {
        'page_name': 'register',
        'page_section': 'shop',
        'page_title': 'Đăng ký tài khoản người bán',
        'form': form,
    })


@require_http_methods(['GET', 'POST'])
def shop_verify_email(request):
    draft = request.session.get(SELLER_DRAFT_SESSION_KEY)
    if draft and draft.get('email_verified'):
        return redirect('shop_onboarding_profile')
    if is_active_seller(request.user) and request.user.email_verified:
        return redirect('shop_onboarding_profile')

    form = SellerVerificationEmailForm(
        request.POST or None,
        initial={'email': draft['email']} if draft else None,
    )
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].strip().lower()
        if draft:
            if email != draft['email'].lower():
                form.add_error('email', 'Email phải trùng với địa chỉ đã nhập ở bước đăng ký.')
            else:
                token = get_random_string(48)
                draft['email_token_hash'] = make_password(token)
                draft['email_token_expires'] = (
                    timezone.now() + SELLER_EMAIL_TOKEN_TTL
                ).timestamp()
                request.session[SELLER_DRAFT_SESSION_KEY] = draft
                try:
                    send_seller_draft_verification_email(email, token)
                except SellerVerificationError as error:
                    draft.pop('email_token_hash', None)
                    draft.pop('email_token_expires', None)
                    request.session[SELLER_DRAFT_SESSION_KEY] = draft
                    messages.error(request, str(error))
                else:
                    messages.success(request, 'Đã gửi liên kết xác thực. Vui lòng kiểm tra hộp thư đến.')
                return redirect('shop_verify_email')
        else:
            account = User.objects.filter(
                email__iexact=email,
                role='SELLER',
                status__in=['ACTIVE', 'INACTIVE'],
                email_verified=False,
                is_active=True,
            ).first()
            if account:
                try:
                    send_seller_verification_email(request, account)
                except SellerVerificationError as error:
                    messages.error(request, str(error))
                else:
                    messages.success(request, 'Nếu email thuộc tài khoản seller chưa xác thực, liên kết kích hoạt đã được gửi.')
            else:
                messages.success(request, 'Nếu email thuộc tài khoản seller chưa xác thực, liên kết kích hoạt đã được gửi.')
            return redirect('shop_verify_email')

    return render(request, 'shop/verify_email.html', {
        'page_name': 'verify-email',
        'page_section': 'shop',
        'page_title': 'Xác thực email',
        'form': form,
    })


@require_GET
def shop_verify_email_confirm(request, token):
    draft = request.session.get(SELLER_DRAFT_SESSION_KEY)
    if draft:
        token_hash = draft.get('email_token_hash')
        expires_at = draft.get('email_token_expires', 0)
        if (
            not token_hash
            or expires_at <= timezone.now().timestamp()
            or not check_password(token, token_hash)
        ):
            messages.error(request, 'Liên kết xác thực không hợp lệ hoặc đã hết hạn.')
            return redirect('shop_verify_email')
        draft['email_verified'] = True
        draft.pop('email_token_hash', None)
        draft.pop('email_token_expires', None)
        request.session[SELLER_DRAFT_SESSION_KEY] = draft
        messages.success(request, 'Email đã được xác thực. Hãy tiếp tục hoàn thiện hồ sơ shop.')
        return redirect('shop_onboarding_profile')

    record = EmailVerificationToken.objects.select_related('user').filter(
        token=token,
        user__role='SELLER',
    ).first()
    if record is None:
        messages.error(request, 'Liên kết xác thực không hợp lệ hoặc đã hết hạn.')
        return redirect('shop_verify_email')
    if (record.verified_at is not None or record.invalidated_at is not None
            or record.expires_at <= timezone.now()):
        messages.error(request, 'Liên kết xác thực đã hết hạn hoặc không còn sử dụng được.')
        return redirect('shop_verify_email')
    with transaction.atomic():
        account = User.objects.select_for_update().get(pk=record.user_id)
        locked_token = EmailVerificationToken.objects.select_for_update().get(pk=record.pk)
        if (locked_token.verified_at is not None or locked_token.invalidated_at is not None
                or locked_token.expires_at <= timezone.now() or account.email_verified):
            messages.error(request, 'Liên kết xác thực đã hết hạn hoặc đã được sử dụng.')
            return redirect('shop_verify_email')
        locked_token.verified_at = timezone.now()
        locked_token.save(update_fields=['verified_at'])
        account.email_verified = True
        account.status = 'ACTIVE'
        account.save(update_fields=['email_verified', 'status'])
    login(request, account)
    shop = _owned_shop(account)
    if shop and shop.legal_submitted_at:
        return redirect('shop_onboarding_pending')
    return redirect('shop_onboarding_profile')


def shop_verify_phone(request):
    draft = request.session.get(SELLER_DRAFT_SESSION_KEY)
    if draft:
        destination = (
            'shop_onboarding_profile'
            if draft.get('email_verified')
            else 'shop_verify_email'
        )
        return redirect(destination)
    if not is_active_seller(request.user):
        return redirect('shop_login')
    if not request.user.email_verified:
        return redirect('shop_verify_email')
    return redirect('shop_onboarding_profile')


def _onboarding_account_ready(request):
    draft = request.session.get(SELLER_DRAFT_SESSION_KEY)
    if draft:
        if not draft.get('email_verified'):
            return redirect('shop_verify_email')
        return None
    if not request.user.email_verified:
        return redirect('shop_verify_email')
    return None


def shop_onboarding_profile(request):
    draft = request.session.get(SELLER_DRAFT_SESSION_KEY)
    if not draft and not is_active_seller(request.user):
        return redirect('shop_login')
    blocked = _onboarding_account_ready(request)
    if blocked:
        return blocked
    shop = None if draft else _owned_shop(request.user)
    form = ShopProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=shop,
        initial=draft.get('profile', {}) if draft else None,
    )
    if request.method == 'POST' and form.is_valid():
        if draft:
            profile = {
                key: form.cleaned_data[key]
                for key in ('shop_name', 'address', 'phone', 'description')
            }
            uploaded_logo = form.cleaned_data.get('logo')
            if uploaded_logo:
                old_logo = draft.get('logo_path')
                if old_logo:
                    default_storage.delete(old_logo)
                logo_filename = uploaded_logo.name.replace('\\', '/').rsplit('/', 1)[-1]
                draft['logo_path'] = default_storage.save(
                    f'shop_onboarding/{get_random_string(24)}/{logo_filename}',
                    uploaded_logo,
                )
            draft['profile'] = profile
            request.session[SELLER_DRAFT_SESSION_KEY] = draft
            return redirect('shop_onboarding_legal')
        shop = form.save(commit=False)
        shop.owner = request.user
        shop.status = 'PENDING'
        shop.save()
        return redirect('shop_onboarding_legal')
    return render(request, 'shop/onboarding_profile.html', {
        'page_name': 'onboarding-profile',
        'page_section': 'shop',
        'page_title': 'Hồ sơ shop',
        'form': form,
        'shop': shop,
    })


def shop_onboarding_legal(request):
    draft = request.session.get(SELLER_DRAFT_SESSION_KEY)
    if not draft and not is_active_seller(request.user):
        return redirect('shop_login')
    blocked = _onboarding_account_ready(request)
    if blocked:
        return blocked
    shop = None if draft else _owned_shop(request.user)
    if shop is None and not draft:
        return redirect('shop_onboarding_profile')
    if shop and shop.legal_submitted_at is not None:
        return redirect('shop_onboarding_pending')
    form = ShopLegalForm(request.POST or None, request.FILES or None, instance=shop)
    if request.method == 'POST' and form.is_valid():
        if draft:
            profile = draft.get('profile')
            if not profile:
                return redirect('shop_onboarding_profile')
            try:
                with transaction.atomic():
                    if User.objects.filter(username__iexact=draft['username']).exists():
                        form.add_error(None, 'Tên đăng nhập đã được sử dụng. Vui lòng đăng ký lại.')
                        return render(request, 'shop/onboarding_legal.html', {
                            'page_name': 'onboarding-legal',
                            'page_section': 'shop',
                            'page_title': 'Xác thực pháp lý',
                            'form': form,
                            'shop': None,
                        })
                    if User.objects.filter(email__iexact=draft['email']).exists():
                        form.add_error(None, 'Email đã được đăng ký. Vui lòng đăng ký lại.')
                        return render(request, 'shop/onboarding_legal.html', {
                            'page_name': 'onboarding-legal',
                            'page_section': 'shop',
                            'page_title': 'Xác thực pháp lý',
                            'form': form,
                            'shop': None,
                        })
                    account = User(
                        username=draft['username'],
                        email=draft['email'],
                        password=draft['password'],
                        full_name=draft['username'],
                        phone=profile['phone'],
                        role='SELLER',
                        status='ACTIVE',
                        email_verified=True,
                    )
                    account.save()
                    shop = form.save(commit=False)
                    shop.owner = account
                    shop.shop_name = profile['shop_name']
                    shop.address = profile['address']
                    shop.phone = profile['phone']
                    shop.description = profile['description']
                    shop.logo.name = draft.get('logo_path', '')
                    shop.status = 'PENDING'
                    shop.legal_submitted_at = timezone.now()
                    shop.save()
            except DatabaseError:
                messages.error(request, 'Chưa lưu được hồ sơ đăng ký. Vui lòng thử lại.')
                return render(request, 'shop/onboarding_legal.html', {
                    'page_name': 'onboarding-legal',
                    'page_section': 'shop',
                    'page_title': 'Xác thực pháp lý',
                    'form': form,
                    'shop': None,
                })
            request.session.pop(SELLER_DRAFT_SESSION_KEY, None)
            login(request, account)
            messages.success(request, 'Hồ sơ đã được gửi và đang chờ admin xét duyệt.')
            return redirect('shop_onboarding_pending')
        shop = form.save(commit=False)
        shop.status = 'PENDING'
        shop.legal_submitted_at = timezone.now()
        shop.save()
        return redirect('shop_onboarding_pending')
    return render(request, 'shop/onboarding_legal.html', {
        'page_name': 'onboarding-legal',
        'page_section': 'shop',
        'page_title': 'Xác thực pháp lý',
        'form': form,
        'shop': shop,
    })


@require_GET
def shop_onboarding_pending(request):
    if not is_active_seller(request.user):
        return redirect('shop_login')
    shop = _owned_shop(request.user)
    if shop is None:
        return redirect('shop_onboarding_profile')
    # Approved while waiting: send the seller straight to the dashboard.
    if shop.status == 'ACTIVE':
        return redirect('shop_dashboard')
    return render(request, 'shop/onboarding_pending.html', {
        'page_name': 'onboarding-pending',
        'page_section': 'shop',
        'page_title': (
            'Hồ sơ shop cần cập nhật' if shop.status == 'REJECTED'
            else 'Shop đang tạm ngưng' if shop.status == 'SUSPENDED'
            else 'Chờ xét duyệt'
        ),
        'shop': shop,
    })


@require_http_methods(['GET', 'POST'])
@shop_required
def shop_notifications(request):
    shop = _owned_shop(request.user)
    if shop is None or shop.status != 'ACTIVE':
        return redirect('shop_dashboard')
    notifications = request.user.notifications.order_by('-created_at', '-pk')
    if request.method == 'POST':
        notification_id = request.POST.get('notification_id')
        if notification_id:
            if not notification_id.isascii() or not notification_id.isdigit() or len(notification_id) > 19:
                raise Http404
            notification = get_object_or_404(notifications, pk=notification_id)
            if not notification.is_read:
                notification.is_read = True
                notification.save(update_fields=['is_read'])
        else:
            notifications.filter(is_read=False).update(is_read=True)
        return redirect('shop_notifications')
    notification_page = Paginator(notifications, 20).get_page(request.GET.get('page'))
    return render(request, 'shop/notifications.html', {
        'page_name': 'notifications',
        'page_section': 'shop',
        'page_title': 'Thông báo',
        'shop': shop,
        'notifications': notification_page,
        'notifications_page': notification_page,
        'notification_total': notifications.count(),
        'unread_notification_count': notifications.filter(is_read=False).count(),
        'filter_query': '',
    })


@require_http_methods(['GET', 'POST'])
@shop_required
def shop_profile_settings(request):
    shop = _owned_shop(request.user)
    if shop is None:
        return redirect('shop_onboarding_profile')

    account_form = SellerAccountProfileForm(
        request.POST if request.method == 'POST' and request.POST.get('profile_section') == 'account' else None,
        request.FILES if request.method == 'POST' and request.POST.get('profile_section') == 'account' else None,
        instance=User.objects.get(pk=request.user.pk),
    )
    form = ShopSettingsForm(
        request.POST if request.method == 'POST' and request.POST.get('profile_section') != 'account' else None,
        request.FILES if request.method == 'POST' and request.POST.get('profile_section') != 'account' else None,
        instance=shop,
    )
    if request.method == 'POST' and request.POST.get('profile_section') == 'account' and account_form.is_valid():
        owner = account_form.save(commit=False)
        phone_changed = 'phone' in account_form.changed_data
        if phone_changed:
            owner.phone_verified = False
        try:
            with transaction.atomic():
                owner.save()
        except DatabaseError:
            logger.exception('Could not update seller account profile for user %s.', request.user.pk)
            account_form.add_error(None, 'Không thể lưu hồ sơ lúc này. Vui lòng thử lại.')
            messages.error(request, 'Không thể lưu hồ sơ lúc này. Vui lòng thử lại.')
        else:
            messages.success(request, 'Thông tin tài khoản đã được cập nhật.')
            if phone_changed:
                messages.warning(request, 'Số điện thoại đã đổi và cần được xác minh lại.')
            return redirect('shop_profile_settings')

    if request.method == 'POST' and request.POST.get('profile_section') != 'account' and form.is_valid():
        changed_fields = set(form.changed_data)
        legal_fields = {
            'legal_entity_type', 'representative_name', 'representative_birth_date',
            'id_number', 'id_card_front', 'id_card_back', 'id_card',
            'tax_number', 'business_license',
        }
        legal_details_changed = bool(changed_fields & legal_fields)
        contact_details_changed = bool(changed_fields & {'phone', 'contact_email'})
        was_identity_verified = shop.identity_verified
        previous_verification = (
            shop.identity_verified,
            shop.contact_phone_verified,
            shop.contact_email_verified,
            shop.admin_note,
        )
        updated_shop = form.save(commit=False)
        if 'phone' in changed_fields:
            updated_shop.contact_phone_verified = False
        if 'contact_email' in changed_fields:
            updated_shop.contact_email_verified = False
        if was_identity_verified and legal_details_changed:
            updated_shop.identity_verified = False
            updated_shop.admin_note = 'Hồ sơ pháp lý đã được chủ shop cập nhật; cần quản trị viên xác minh lại.'
        try:
            with transaction.atomic():
                updated_shop.save()
        except DatabaseError:
            logger.exception('Could not update shop profile for shop %s.', shop.pk)
            form.add_error(None, 'Không thể lưu hồ sơ shop lúc này. Vui lòng thử lại.')
            (
                shop.identity_verified,
                shop.contact_phone_verified,
                shop.contact_email_verified,
                shop.admin_note,
            ) = previous_verification
            messages.error(request, 'Không thể lưu hồ sơ shop lúc này. Vui lòng thử lại.')
        else:
            messages.success(request, 'Đã lưu thông tin trang cá nhân của shop.')
            if legal_details_changed and was_identity_verified:
                messages.warning(request, 'Thông tin pháp lý đã đổi và cần được quản trị viên xác minh lại.')
            if contact_details_changed:
                messages.warning(request, 'Thông tin liên hệ shop đã đổi và trạng thái xác minh đã được đặt lại.')
            return redirect('shop_profile_settings')

    orders = _orders(shop)
    shop_orders = Order.objects.filter(order_items__shop=shop).distinct()
    order_count = shop_orders.count()
    cancelled_count = shop_orders.filter(order_status='CANCELLED').count()
    returned_count = shop_orders.filter(order_status='RETURNED').count()
    delivered_count = shop_orders.filter(order_status__in=['DELIVERED', 'COMPLETED']).count()
    questions = ProductQuestion.objects.filter(product__shop=shop)
    question_count = questions.count()
    answered_questions = questions.filter(status=True).count()
    return render(request, 'shop/profile_settings.html', {
        'page_name': 'profile-settings',
        'page_section': 'shop',
        'page_title': 'Trang cá nhân',
        'shop': shop,
        'form': form,
        'account_form': account_form,
        'stats': {
            'product_count': Product.objects.filter(shop=shop).count(),
            'sold_quantity': Product.objects.filter(shop=shop).aggregate(total=Sum('sold_quantity'))['total'] or 0,
            'delivered_orders': delivered_count,
            'rating_average': None,
            'rating_count': None,
            'response_rate': round(answered_questions * 100 / question_count) if question_count else None,
            'cancel_rate': round(cancelled_count * 100 / order_count) if order_count else None,
            'return_rate': round(returned_count * 100 / order_count) if order_count else None,
        },
        'owner_phone': request.user.phone,
        'owner_email': request.user.email,
        'email_verified': request.user.email_verified,
        'phone_verified': request.user.phone_verified,
    })


@require_GET
def public_shop_profile(request, slug):
    shop = get_object_or_404(Shop, slug=slug, status='ACTIVE')
    products = Product.objects.filter(
        shop=shop,
        status='ACTIVE',
        stock_quantity__gt=0,
    ).select_related('category', 'brand').order_by('-created_at', '-pk')
    return render(request, 'buyer/shop_profile.html', {
        'page_name': 'shop-profile',
        'page_section': 'buyer',
        'shop': shop,
        'products': products[:24],
        'product_count': products.count(),
    })


ORDER_LABELS = {
    'PENDING': 'Chờ shop xác nhận',
    'PROCESSING': 'Đang xử lý',
    'SHIPPING': 'Đang giao',
    'DELIVERED': 'Chờ buyer xác nhận',
    'COMPLETED': 'Hoàn thành',
    'CANCELLED': 'Đã hủy',
}
RETURN_LABELS = {'REQUESTED': 'Chờ xử lý', 'APPROVED': 'Đã duyệt', 'REJECTED': 'Từ chối', 'REFUNDED': 'Đã hoàn tiền'}
TITLES = {
    'dashboard': 'Tổng quan', 'offers': 'Quản lý sản phẩm', 'inventory': 'Quản lý tồn kho',
    'orders': 'Quản lý đơn hàng', 'order': 'Chi tiết đơn hàng', 'fulfillment': 'Quản lý giao nhận',
    'revenue': 'Báo cáo doanh thu', 'questions': 'Câu hỏi sản phẩm', 'aftersales': 'Hậu mãi',
    'build-requests': 'Yêu cầu cấu hình build', 'build-request-detail': 'Chi tiết yêu cầu build',
    'proposal-builder': 'Tạo báo giá', 'proposal-list': 'Báo giá đã gửi', 'proposal': 'Chi tiết báo giá',
    'profile-settings': 'Trang cá nhân',
}


def _orders(shop):
    if shop is None:
        return []
    process_order_timeouts()
    legacy_orders = Order.objects.filter(
        order_items__shop=shop,
    ).exclude(
        shop_orders__shop=shop,
    ).distinct()
    for order in legacy_orders:
        ensure_shop_orders(order)

    own_items = OrderItem.objects.filter(shop=shop).select_related('product__category')
    queryset = ShopOrder.objects.filter(shop=shop).select_related(
        'order__user', 'order__address',
    ).prefetch_related(
        Prefetch('order__order_items', queryset=own_items, to_attr='shop_items'),
        Prefetch(
            'history',
            queryset=ShopOrderHistory.objects.select_related('changed_by'),
            to_attr='shop_history',
        ),
        Prefetch(
            'cancellation_requests',
            queryset=CancellationRequest.objects.select_related('requested_by', 'resolved_by'),
        ),
    ).order_by('-order__created_at', '-order_id')
    rows = []
    for shop_order in queryset:
        order = shop_order.order
        order.shop_order = shop_order
        order.order_status = shop_order.status
        order.shop_total = sum((item.subtotal for item in order.shop_items), Decimal('0'))
        order.status_label = ORDER_LABELS.get(order.order_status, order.get_order_status_display())
        order.status_css = 'success' if order.order_status == 'COMPLETED' else 'error' if order.order_status == 'CANCELLED' else 'info'
        rows.append(order)
    return rows


def _owned_object(queryset, identifier):
    if not identifier.isascii() or not identifier.isdigit() or len(identifier) > 19:
        raise Http404
    pk = int(identifier)
    if pk > 9223372036854775807:
        raise Http404
    return get_object_or_404(queryset, pk=pk)


def _revenue(orders, days):
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    completed = [order for order in orders if order.order_status == 'COMPLETED' and start <= timezone.localdate(order.shop_order.completed_at or order.updated_at) <= today]
    daily = defaultdict(lambda: {'amount': Decimal('0'), 'count': 0})
    categories = defaultdict(Decimal)
    for order in completed:
        date = timezone.localdate(order.shop_order.completed_at or order.updated_at)
        daily[date]['amount'] += order.shop_total
        daily[date]['count'] += 1
        for item in order.shop_items:
            categories[item.product.category.category_name] += item.subtotal
    maximum = max([row['amount'] for row in daily.values()] or [Decimal('1')]) or Decimal('1')
    rows = []
    for offset in range(days):
        date = start + timedelta(days=offset)
        amount = daily[date]['amount']
        rows.append({'date': date, 'amount': amount, 'percent': round(amount / maximum * 100), 'count': daily[date]['count']})
    total = sum((order.shop_total for order in completed), Decimal('0'))
    return {
        'total': total, 'count': len(completed), 'average': total / len(completed) if completed else 0,
        'days': rows, 'categories': [{'name': name, 'amount': value, 'percent': round(value / total * 100) if total else 0} for name, value in categories.items()],
    }


@require_GET
def shop_page(request, page):
    shop = _owned_shop(request.user)
    if shop is None:
        return redirect('shop_onboarding_profile')
    if shop.status != 'ACTIVE':
        return redirect('shop_onboarding_pending')

    context = {'page_name': page, 'page_section': 'shop', 'page_title': TITLES[page]}

    products = Product.objects.filter(shop=shop).select_related('brand', 'category').order_by('-created_at', '-pk')
    orders = _orders(shop)
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    filters = request.GET.copy()
    filters.pop('page', None)
    context.update({
        'shop': shop, 'q': q, 'status': status, 'filter_query': filters.urlencode(), 'categories': Category.objects.filter(status=True).order_by('category_name'),
        'product_total': products.count(), 'product_active': products.filter(status='ACTIVE', stock_quantity__gt=0).count(),
        'product_hidden': products.filter(status='INACTIVE').count(), 'product_out': products.exclude(status='INACTIVE').filter(stock_quantity=0).count(),
        'product_low': products.exclude(status='INACTIVE').filter(stock_quantity__lte=3).count(),
        'product_ok': products.filter(status='ACTIVE', stock_quantity__gt=3).count(),
        'order_total': len(orders), 'order_pending': sum(order.order_status == 'PENDING' for order in orders),
        'order_processing': sum(order.order_status in {'PROCESSING', 'SHIPPING'} for order in orders),
        'order_delivered': sum(order.order_status in {'DELIVERED', 'COMPLETED'} for order in orders),
        'recent_orders': orders[:5], 'pending_orders': [order for order in orders if order.order_status in {'PENDING', 'PROCESSING'}][:5],
        'order_statuses': [{'code': code, 'label': label, 'count': sum(order.order_status == code for order in orders)} for code, label in ORDER_LABELS.items()],
        'revenue': _revenue(orders, 30), 'top_products': products.order_by('-sold_quantity', 'pk')[:5],
    })
    questions = ProductQuestion.objects.filter(product__shop=shop).select_related('product', 'user').prefetch_related(
        Prefetch('answers', queryset=conversation_messages(), to_attr='thread_messages'),
    ).annotate(latest_activity=Coalesce(Max('answers__created_at'), 'created_at')) if shop else ProductQuestion.objects.none()
    context['question_pending'] = questions.filter(status=False).count()
    context['recent_questions'] = questions.filter(status=False).order_by('-latest_activity', '-pk')[:3]

    if page in {'offers', 'inventory'}:
        if q:
            products = products.filter(Q(product_name__icontains=q) | Q(brand__brand_name__icontains=q))
        category = request.GET.get('cat', '')
        if category:
            if category.isascii() and category.isdigit() and len(category) <= 19 and int(category) <= 9223372036854775807:
                products = products.filter(category_id=int(category))
            else:
                products = products.none()
        if status == 'active':
            products = products.filter(status='ACTIVE', stock_quantity__gt=0)
        elif status == 'out':
            products = products.exclude(status='INACTIVE').filter(stock_quantity=0)
        elif status == 'inactive':
            products = products.filter(status='INACTIVE')
        context['category_filter'] = category
        context['products_page'] = Paginator(products, 10).get_page(request.GET.get('page'))
        context['low_products'] = products.exclude(status='INACTIVE').filter(stock_quantity__lte=3)
        context['editing_product'] = _owned_object(Product.objects.filter(shop=shop), request.GET['edit']) if request.GET.get('edit') else None
        context['show_product_form'] = 'new' in request.GET or context['editing_product'] is not None
    elif page in {'orders', 'order', 'fulfillment'}:
        filtered = [order for order in orders if (not status or order.order_status == status) and (not q or q.lower() in order.order_code.lower() or q.lower() in order.user.full_name.lower())]
        context['orders_page'] = Paginator(filtered, 10).get_page(request.GET.get('page'))
        context['processing_orders'] = [order for order in orders if order.order_status == 'PROCESSING']
        context['shipping_orders'] = [order for order in orders if order.order_status == 'SHIPPING']
        context['order'] = None
        if page == 'order' and request.GET.get('id'):
            selected = _owned_object(Order.objects.filter(order_items__shop=shop).distinct(), request.GET['id'])
            context['order'] = next(order for order in orders if order.pk == selected.pk)
    elif page == 'questions':
        answered = request.GET.get('answered') == '1'
        context['answered'] = answered
        context['questions_page'] = Paginator(questions.filter(status=answered).order_by('-latest_activity', '-pk'), 10).get_page(request.GET.get('page'))
    elif page == 'aftersales':
        cases = Return.objects.filter(order__order_items__shop=shop).distinct().select_related('order', 'user').order_by('-created_at') if shop else Return.objects.none()
        if status in RETURN_LABELS:
            cases = cases.filter(status=status)
        context['cases_page'] = Paginator(cases, 10).get_page(request.GET.get('page'))
        context['case'] = _owned_object(cases, request.GET['id']) if request.GET.get('id') else None
        context['return_statuses'] = RETURN_LABELS.items()
    elif page == 'revenue':
        period = request.GET.get('period', '30')
        context['period'] = period if period in {'7', '14', '30'} else '30'
        context['revenue'] = _revenue(orders, int(context['period']))
    return render(request, f'shop/{page}.html', context)


@require_POST
def shop_product_save(request):
    shop = _owned_shop(request.user)
    if shop is None or shop.status != 'ACTIVE':
        return redirect('shop_dashboard')

    product_id = request.POST.get('product_id')
    category_id = request.POST.get('category')
    product_name = request.POST.get('product_name', '').strip()
    brand_name = request.POST.get('brand', '').strip()
    price_raw = request.POST.get('price', '0')
    stock_raw = request.POST.get('stock_quantity', '0')
    status = request.POST.get('status', 'ACTIVE')
    description = request.POST.get('description', '').strip()

    if not product_name:
        messages.error(request, 'Tên sản phẩm không được để trống.')
        return redirect('shop_offers')

    try:
        price = Decimal(price_raw)
    except (InvalidOperation, ValueError):
        price = Decimal('0')

    try:
        stock_quantity = int(stock_raw)
    except (ValueError, TypeError):
        stock_quantity = 0

    category = get_object_or_404(Category, pk=category_id)

    brand = None
    if brand_name:
        brand, _ = Brand.objects.get_or_create(brand_name=brand_name)

    base_slug = slugify(product_name, allow_unicode=True) or 'product'
    slug = base_slug
    counter = 1

    if product_id:
        product = get_object_or_404(Product, pk=product_id, shop=shop)
        product.category = category
        product.brand = brand
        product.product_name = product_name
        product.description = description
        product.price = price
        product.stock_quantity = stock_quantity
        product.status = status
        if product.slug != slug:
            while Product.objects.filter(slug=slug).exclude(pk=product.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            product.slug = slug
        if request.FILES.get('thumbnail'):
            product.thumbnail = request.FILES['thumbnail']
        product.save()
        messages.success(request, f'Đã cập nhật sản phẩm "{product_name}".')
    else:
        while Product.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1
        product = Product(
            shop=shop,
            category=category,
            brand=brand,
            product_name=product_name,
            slug=slug,
            description=description,
            price=price,
            stock_quantity=stock_quantity,
            status=status,
        )
        if request.FILES.get('thumbnail'):
            product.thumbnail = request.FILES['thumbnail']
        product.save()
        messages.success(request, f'Đã thêm sản phẩm "{product_name}".')

    return redirect('shop_offers')


@require_POST
def shop_product_toggle(request, product_id):
    shop = _owned_shop(request.user)
    if shop is None or shop.status != 'ACTIVE':
        return redirect('shop_dashboard')

    product = get_object_or_404(Product, pk=product_id, shop=shop)
    if product.status == 'INACTIVE':
        product.status = 'ACTIVE'
        messages.success(request, f'Đã hiện sản phẩm "{product.product_name}".')
    else:
        product.status = 'INACTIVE'
        messages.success(request, f'Đã ẩn sản phẩm "{product.product_name}".')
    product.save()
    return redirect('shop_offers')


@require_POST
def shop_product_delete(request, product_id):
    shop = _owned_shop(request.user)
    if shop is None or shop.status != 'ACTIVE':
        return redirect('shop_dashboard')

    product = get_object_or_404(Product, pk=product_id, shop=shop)
    name = product.product_name
    product.delete()
    messages.success(request, f'Đã xóa sản phẩm "{name}".')
    return redirect('shop_offers')


@require_POST
def shop_inventory_update(request):
    shop = _owned_shop(request.user)
    if shop is None or shop.status != 'ACTIVE':
        return redirect('shop_dashboard')

    product_id = request.POST.get('product_id')
    product = get_object_or_404(Product, pk=product_id, shop=shop)

    try:
        quantity = int(request.POST.get('quantity', 0))
    except (ValueError, TypeError):
        quantity = 0

    if quantity < 0:
        quantity = 0

    product.stock_quantity = quantity
    product.save(update_fields=['stock_quantity'])
    messages.success(request, f'Đã cập nhật tồn kho "{product.product_name}" thành {quantity}.')
    return redirect('shop_inventory')


@require_POST
def shop_order_update_status(request, order_id):
    shop = _owned_shop(request.user)
    if shop is None or shop.status != 'ACTIVE':
        return redirect('shop_dashboard')

    process_order_timeouts()
    order = get_object_or_404(Order.objects.filter(order_items__shop=shop).distinct(), pk=order_id)
    shop_order = get_object_or_404(ShopOrder, order=order, shop=shop)
    action = request.POST.get('action', '').strip()
    new_status = request.POST.get('new_status', '').strip()
    note = request.POST.get('note', '').strip()
    redirect_to = request.POST.get('redirect', '')

    try:
        if action in {'approve_cancellation', 'reject_cancellation'}:
            cancellation = resolve_cancellation_request(
                request.POST.get('cancellation_request_id', ''),
                shop,
                request.user,
                action == 'approve_cancellation',
                note,
            )
            if cancellation.status == 'ESCALATED':
                messages.warning(request, 'Yêu cầu đã quá hạn và được chuyển admin xử lý.')
            else:
                messages.success(
                    request,
                    'Đã xử lý yêu cầu hủy.' if action == 'approve_cancellation'
                    else 'Đã từ chối yêu cầu hủy; phần hàng tiếp tục được xử lý.',
                )
        else:
            if action == 'accept':
                new_status = 'PROCESSING'
            elif action == 'reject':
                new_status = 'CANCELLED'
            elif action == 'handoff':
                new_status = 'SHIPPING'
            updated = update_shop_order(
                order.pk, shop, request.user, new_status,
                reason=request.POST.get('reason', '').strip(),
                note=note,
                carrier_name=request.POST.get('carrier_name', '').strip(),
                tracking_code=request.POST.get('tracking_code', '').strip(),
            )
            if (
                updated.status == 'CANCELLED'
                and updated.confirmation_deadline <= timezone.now()
                and action != 'reject'
            ):
                messages.warning(request, 'Hạn xác nhận đã hết; hệ thống đã tự hủy phần hàng.')
            else:
                messages.success(request, f'Đã cập nhật phần hàng của đơn {order.order_code}.')
    except ValidationError as error:
        messages.error(request, error.messages[0])
        return redirect('shop_orders')
    except DatabaseError:
        messages.error(request, 'Chưa cập nhật được đơn hàng. Vui lòng thử lại.')
        return redirect('shop_orders')

    if redirect_to == 'fulfillment':
        return redirect('shop_fulfillment')
    return redirect(f'{reverse("shop_order")}?id={order.pk}')


@require_POST
def shop_question_answer(request, question_id):
    shop = _owned_shop(request.user)
    if shop is None or shop.status != 'ACTIVE':
        return redirect('shop_dashboard')

    owned_questions = ProductQuestion.objects.filter(product__shop=shop, pk=question_id)
    question = get_object_or_404(owned_questions)
    form = ProductAnswerForm(request.POST)
    if not form.is_valid():
        messages.error(request, form.errors['answer'][0])
        return redirect('shop_questions')
    try:
        append_question_message(question.pk, request.user, form.cleaned_data['answer'], is_shop_reply=True)
    except ValidationError as error:
        messages.error(request, error.messages[0])
        return redirect('shop_questions')
    except DatabaseError:
        messages.error(request, 'Chưa gửi được câu trả lời. Vui lòng thử lại.')
        return redirect('shop_questions')
    messages.success(request, 'Đã gửi câu trả lời.')
    return redirect(f'{reverse("shop_questions")}?answered=1')


@require_POST
def shop_return_update(request, return_id):
    shop = _owned_shop(request.user)
    if shop is None or shop.status != 'ACTIVE':
        return redirect('shop_dashboard')

    case = get_object_or_404(
        Return.objects.filter(order__order_items__shop=shop).distinct(),
        pk=return_id,
    )

    action = request.POST.get('action', '').strip()
    if action == 'approve':
        case.status = 'APPROVED'
        case.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'Đã duyệt yêu cầu đổi trả #{case.pk}.')
    elif action == 'reject':
        case.status = 'REJECTED'
        case.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'Đã từ chối yêu cầu đổi trả #{case.pk}.')
    else:
        messages.error(request, 'Hành động không hợp lệ.')

    return redirect('shop_aftersales')



STAFF_SHOP_STATUSES = (
    ('PENDING', 'Chờ duyệt tham gia'),
    ('ACTIVE', 'Đang hoạt động'),
    ('REJECTED', 'Bị từ chối'),
    ('SUSPENDED', 'Tạm ngưng'),
)
STAFF_SHOP_LABELS = dict(STAFF_SHOP_STATUSES)


@require_GET
def staff_shop_list(request):
    every = Shop.objects.select_related('owner')
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '').strip()
    if status not in STAFF_SHOP_LABELS:
        status = ''
    shops = every.filter(status=status) if status else every
    if search:
        shops = shops.filter(
            Q(shop_name__icontains=search)
            | Q(owner__full_name__icontains=search)
            | Q(owner__email__icontains=search)
            | Q(phone__icontains=search)
        )
    filter_query = request.GET.copy()
    filter_query.pop('page', None)
    counts = {code: every.filter(status=code).count() for code in STAFF_SHOP_LABELS}
    return render(request, 'admin/shop.html', {
        'page_name': 'shop',
        'page_section': 'staff',
        'shop_page': Paginator(shops.order_by('-created_at', '-pk'), 10).get_page(request.GET.get('page')),
        'search': search,
        'status': status,
        'filter_query': filter_query.urlencode(),
        'shop_total': every.count(),
        'shop_counts': counts,
        'shop_statuses': [(code, label, counts[code]) for code, label in STAFF_SHOP_STATUSES],
    })


def _staff_shop_return(request):
    query = {key: request.POST[key] for key in ('search', 'status', 'page') if request.POST.get(key)}
    url = reverse('staff_shop')
    return f'{url}?{urlencode(query)}' if query else url


@require_POST
def staff_shop_approve(request, shop_id):
    shop = get_object_or_404(Shop, pk=shop_id)
    if shop.status == 'ACTIVE':
        messages.info(request, f'Shop "{shop.shop_name}" đã được duyệt trước đó.')
    elif not shop.is_ready_for_approval():
        messages.error(
            request,
            f'Shop "{shop.shop_name}" cần xác thực email và nộp đủ hồ sơ pháp lý trước khi duyệt.',
        )
    else:
        shop.status = 'ACTIVE'
        shop.admin_note = ''
        shop.save()
        messages.success(request, f'Đã duyệt shop "{shop.shop_name}". Chủ shop đã được thông báo.')
    return redirect(_staff_shop_return(request))


@require_POST
def staff_shop_reject(request, shop_id):
    shop = get_object_or_404(Shop, pk=shop_id)
    note = request.POST.get('admin_note', '').strip()
    if not note:
        messages.error(request, f'Nhập lý do từ chối hồ sơ shop "{shop.shop_name}".')
    else:
        shop.status = 'REJECTED'
        shop.admin_note = note
        shop.save(update_fields=['status', 'admin_note', 'updated_at'])
        messages.success(request, f'Đã từ chối hồ sơ shop "{shop.shop_name}".')
    return redirect(_staff_shop_return(request))


@require_POST
def staff_shop_set_identity_verified(request, shop_id):
    shop = get_object_or_404(Shop, pk=shop_id)
    verify = request.POST.get('verified') == 'true'
    has_identity_document = bool(shop.id_card or (shop.id_card_front and shop.id_card_back))
    if verify and (not shop.legal_submitted_at or not has_identity_document):
        messages.error(request, 'Cần có hồ sơ định danh đã nộp trước khi xác minh shop.')
    else:
        shop.identity_verified = verify
        shop.save(update_fields=['identity_verified', 'updated_at'])
        if verify:
            messages.success(request, f'Đã xác minh danh tính shop "{shop.shop_name}".')
        else:
            messages.info(request, f'Đã gỡ xác minh danh tính shop "{shop.shop_name}".')
    return redirect(_staff_shop_return(request))


@require_GET
def staff_shop_document(request, shop_id, document_type):
    shop = get_object_or_404(Shop, pk=shop_id)
    document_fields = {
        'id-card': shop.id_card,
        'id-card-front': shop.id_card_front,
        'id-card-back': shop.id_card_back,
        'business-license': shop.business_license,
    }
    document = document_fields.get(document_type)
    if document is None or not document or not shop.legal_submitted_at:
        raise Http404('Không tìm thấy giấy tờ pháp lý.')
    try:
        file_handle = document.open('rb')
    except (OSError, ValueError) as error:
        raise Http404('Không thể mở giấy tờ pháp lý.') from error
    return FileResponse(
        file_handle,
        as_attachment=True,
        filename=document.name.rsplit('/', 1)[-1].rsplit('\\', 1)[-1],
        content_type='application/octet-stream',
    )


@require_GET
def public_shop_document_denied(request, path):
    raise Http404


@require_POST
def staff_shop_suspend(request, shop_id):
    shop = get_object_or_404(Shop, pk=shop_id)
    if shop.status == 'SUSPENDED':
        messages.info(request, f'Shop "{shop.shop_name}" đã ở trạng thái tạm ngưng.')
    else:
        shop.status = 'SUSPENDED'
        shop.save()
        from notifications.models import Notification
        Notification.objects.create(
            user=shop.owner,
            title='Shop đã bị tạm ngưng',
            message=f'Shop "{shop.shop_name}" đã bị tạm ngưng. Vui lòng liên hệ quản trị viên.',
            type='SHOP_SUSPENDED',
        )
        messages.success(request, f'Đã tạm ngưng shop "{shop.shop_name}".')
    return redirect(_staff_shop_return(request))
