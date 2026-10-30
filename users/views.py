from time import time
from datetime import timedelta
from smtplib import SMTPException
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect
from django.http import Http404
from django import forms
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from users.models import Address, BuyerEmailOTP, PasswordResetToken, User
from .address_services import save_address, set_default_address
from users.forms import (
    BuyerRegisterForm,
    BuyerEmailOTPForm,
    BuyerOTPEmailForm,
    BuyerAddressForm,
    BuyerForgotPasswordForm,
    BuyerSetPasswordForm,
    LoginForm,
    StaffForgotPasswordForm,
    StaffLoginForm,
    StaffSetPasswordForm,
)
from .otp_services import BuyerOTPDeliveryError, issue_buyer_email_otp, verify_buyer_email_otp


# Each portal has its own role, so one session never reaches another area.
BUYER_ROLES = {'BUYER', 'CUSTOMER'}
SELLER_ROLES = {'SELLER'}


def _is_live_account(user):
    return (
        user.is_authenticated
        and user.is_active
        and getattr(user, 'status', 'ACTIVE') == 'ACTIVE'
    )


def is_active_buyer(user):
    """Buyer portal. Staff and sellers must sign in through their own portals."""
    return _is_live_account(user) and getattr(user, 'role', '') in BUYER_ROLES


def is_active_seller(user):
    """Shop portal. Buyers and staff must sign in through their own portals."""
    return _is_live_account(user) and getattr(user, 'role', '') in SELLER_ROLES


buyer_required = user_passes_test(is_active_buyer, login_url=reverse_lazy('auth_login'))


def _buyer_address(user, identifier):
    try:
        address_id = forms.IntegerField(min_value=1, max_value=9223372036854775807).clean(identifier)
    except ValidationError:
        raise Http404('Địa chỉ không hợp lệ.')
    return get_object_or_404(Address, pk=address_id, user=user, is_archived=False)


@require_http_methods(['GET', 'POST'])
@buyer_required
def buyer_addresses(request):
    identifier = request.POST.get('address_id') if request.method == 'POST' else request.GET.get('edit')
    address = _buyer_address(request.user, identifier) if identifier else None
    form = BuyerAddressForm(request.POST if request.method == 'POST' else None, instance=address)
    if request.method == 'POST' and form.is_valid():
        try:
            save_address(request.user, form.cleaned_data, address.pk if address else None)
        except Address.DoesNotExist:
            raise Http404('Địa chỉ không còn tồn tại.')
        except DatabaseError:
            form.add_error(None, 'Chưa lưu được địa chỉ. Vui lòng thử lại.')
        else:
            messages.success(request, 'Đã cập nhật địa chỉ.' if address else 'Đã lưu địa chỉ nhận hàng.')
            return redirect('buyer_addresses')
    return render(request, 'buyer/addresses.html', {
        'page_name': 'addresses', 'page_section': 'buyer', 'form': form,
        'editing_address': address,
        'addresses': request.user.addresses.filter(is_archived=False).order_by('-is_default', 'pk'),
    })


@require_POST
@buyer_required
def buyer_address_default(request, address_id):
    _buyer_address(request.user, address_id)
    try:
        set_default_address(request.user, address_id)
    except Address.DoesNotExist:
        raise Http404('Địa chỉ không còn tồn tại.')
    except DatabaseError:
        messages.error(request, 'Chưa đổi được địa chỉ mặc định. Vui lòng thử lại.')
    else:
        messages.success(request, 'Đã đặt địa chỉ mặc định cho các đơn hàng tiếp theo.')
    return redirect('buyer_addresses')


def safe_auth_next(request, default='buyer_cart'):
    fallback = reverse(default)
    candidate = request.POST.get('next') or request.GET.get('next') or fallback
    auth_aliases = {'/shop/login', '/shop/register', '/shop/forgot', '/staff/login'}
    if (candidate.startswith(('/buyer/', '/shop/', '/staff/')) and not candidate.startswith('//')
            and candidate.split('?', 1)[0].split('#', 1)[0].rstrip('/') not in auth_aliases
            and url_has_allowed_host_and_scheme(candidate, {request.get_host()}, require_https=request.is_secure())):
        return candidate
    return fallback


def finish_auth_login(request, destination):
    from carts.services import add_product

    pending = request.session.pop('pending_cart_add', None)
    if pending and pending.get('expires', 0) > time():
        try:
            add_product(request.user, pending['product_id'], pending['quantity'])
            messages.success(request, 'Đã thêm sản phẩm vào giỏ hàng.')
        except ValidationError as error:
            messages.error(request, error.messages[0])
        return redirect('buyer_cart')
    return redirect(destination)


def auth_login(request, register=False):
    if register and request.method == 'GET':
        query = {'mode': 'register', 'next': safe_auth_next(request)}
        return redirect(reverse('auth_login') + '?' + urlencode(query))
    mode = 'register' if register else request.POST.get('mode') or request.GET.get('mode', 'login')
    mode = 'register' if mode == 'register' else 'login'
    destination = safe_auth_next(request)
    staff_destination = destination.startswith('/staff/')
    # Public registration creates ordinary accounts, not administrators.
    if mode == 'register' and staff_destination:
        destination = reverse('buyer_cart')
    form_class = BuyerRegisterForm if mode == 'register' else LoginForm
    form = form_class(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        if mode == 'register':
            try:
                with transaction.atomic():
                    account = form.save()
            except IntegrityError:
                form.add_error('email', 'Email đã được đăng ký.')
            else:
                request.session['buyer_otp_user_id'] = account.pk
                request.session['buyer_otp_next'] = destination
                try:
                    issue_buyer_email_otp(account)
                except BuyerOTPDeliveryError as error:
                    messages.error(request, str(error))
                else:
                    messages.success(request, 'Mã xác thực đã được gửi tới email của bạn.')
                return redirect('auth_verify_email')
        else:
            found = User.objects.filter(email__iexact=form.cleaned_data['email']).first()
            account = authenticate(request, username=found.username if found else form.cleaned_data['email'],
                                   password=form.cleaned_data['password'])
            if account is None:
                form.add_error(None, 'Email hoặc mật khẩu không đúng, hoặc tài khoản đã bị khóa.')
            elif is_staff_user(account):
                form.add_error(None, 'Đây là tài khoản quản trị, vui lòng đăng nhập tại trang quản trị.')
            elif getattr(account, 'role', '') not in BUYER_ROLES:
                form.add_error(None, 'Tài khoản không thuộc khu vực người mua.')
            elif account.status == 'INACTIVE' and not account.email_verified:
                form.add_error(None, 'Email chưa được xác thực. Hãy gửi mã OTP để tiếp tục.')
            elif not is_active_buyer(account):
                form.add_error(None, 'Tài khoản không thuộc khu vực người mua.')
            elif staff_destination:
                form.add_error(None, 'Tài khoản không có quyền quản trị hệ thống.')
            else:
                login(request, account)
                return finish_auth_login(request, destination)
    return render(request, 'auth/login.html', {
        'page_name': 'login', 'page_section': 'auth', 'form': form,
        'page_title': 'Đăng ký tài khoản' if mode == 'register' else 'Đăng nhập',
        'mode': mode, 'next': destination,
    })


@require_http_methods(['GET', 'POST'])
def buyer_verify_email(request):
    pending_user_id = request.session.get('buyer_otp_user_id')
    user = User.objects.filter(
        pk=pending_user_id,
        role__in=BUYER_ROLES,
        status='INACTIVE',
        email_verified=False,
    ).first() if pending_user_id else None
    otp = BuyerEmailOTP.objects.filter(user=user).first() if user else None
    code_form = BuyerEmailOTPForm()
    email_form = BuyerOTPEmailForm()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'request':
            email_form = BuyerOTPEmailForm(request.POST)
            if email_form.is_valid():
                candidate = User.objects.filter(
                    email__iexact=email_form.cleaned_data['email'],
                    role__in=BUYER_ROLES,
                    status='INACTIVE',
                    email_verified=False,
                    is_active=True,
                ).first()
                if candidate:
                    request.session['buyer_otp_user_id'] = candidate.pk
                    user = candidate
                    try:
                        issue_buyer_email_otp(candidate)
                    except BuyerOTPDeliveryError as error:
                        messages.error(request, str(error))
                    else:
                        messages.success(request, 'Mã OTP mới đã được gửi tới email của bạn.')
                        return redirect('auth_verify_email')
                else:
                    email_form.add_error(
                        'email',
                        'Không tìm thấy tài khoản buyer chưa xác thực với email này.',
                    )
            return render(request, 'auth/verify_email.html', {
                'page_name': 'verify-email',
                'page_section': 'auth',
                'page_title': 'Xác thực email',
                'email_form': email_form,
                'show_email_form': True,
            })

        if not user or not otp:
            request.session.pop('buyer_otp_user_id', None)
            messages.error(request, 'Phiên xác thực không còn hợp lệ. Hãy nhập lại email.')
            return redirect('auth_verify_email')

        if action == 'resend':
            try:
                issue_buyer_email_otp(user)
            except BuyerOTPDeliveryError as error:
                messages.error(request, str(error))
            else:
                messages.success(request, 'Mã OTP mới đã được gửi tới email của bạn.')
            return redirect('auth_verify_email')

        code_form = BuyerEmailOTPForm(request.POST)
        if code_form.is_valid():
            result = verify_buyer_email_otp(otp, code_form.cleaned_data['code'])
            if result == 'valid':
                user.email_verified = True
                user.status = 'ACTIVE'
                user.save(update_fields=['email_verified', 'status'])
                BuyerEmailOTP.objects.filter(user=user).delete()
                request.session.pop('buyer_otp_user_id', None)
                destination = request.session.pop('buyer_otp_next', reverse('buyer_cart'))
                messages.success(request, 'Xác thực email thành công. Bạn có thể đăng nhập.')
                return redirect(reverse('auth_login') + '?' + urlencode({'next': destination}))
            if result == 'locked':
                request.session.pop('buyer_otp_user_id', None)
                messages.error(request, 'Bạn đã nhập sai 5 lần. Hãy nhập lại email để nhận mã mới.')
                return redirect('auth_verify_email')
            if result == 'expired':
                code_form.add_error('code', 'Mã OTP đã hết hạn. Hãy gửi lại mã mới.')
            else:
                code_form.add_error('code', 'Mã OTP không đúng.')

    show_email_form = not user or not otp
    return render(request, 'auth/verify_email.html', {
        'page_name': 'verify-email',
        'page_section': 'auth',
        'page_title': 'Xác thực email',
        'email_form': email_form,
        'form': code_form,
        'show_email_form': show_email_form,
        'email': user.email if user else None,
    })


@require_http_methods(['GET', 'POST'])
def auth_logout(request):
    logout(request)
    return redirect('auth_login')


@require_http_methods(['GET', 'POST'])
def buyer_forgot_password(request):
    form = BuyerForgotPasswordForm(request.POST or None)
    submitted = False
    if request.method == 'POST' and form.is_valid():
        submitted = True
        matching_accounts = list(
            User.objects.filter(email__iexact=form.cleaned_data['email']).order_by('pk')[:2]
        )
        account = matching_accounts[0] if len(matching_accounts) == 1 else None
        if (account is not None and account.role in BUYER_ROLES
                and not account.is_staff and not account.is_superuser):
            token = get_random_string(48)
            reset_url = request.build_absolute_uri(
                reverse('buyer_reset_password', args=[token])
            )
            try:
                with transaction.atomic():
                    account = User.objects.select_for_update().filter(
                        pk=account.pk,
                        email__iexact=form.cleaned_data['email'],
                        role__in=BUYER_ROLES,
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
                        send_mail(
                            'Đặt lại mật khẩu PCMatch',
                            'Bạn đã yêu cầu đặt lại mật khẩu tài khoản PCMatch. '
                            'Truy cập liên kết sau trong vòng 1 giờ để đặt mật khẩu mới:\n'
                            f'{reset_url}\n\n'
                            'Nếu bạn không yêu cầu thay đổi này, hãy bỏ qua email.',
                            None,
                            [account.email],
                            fail_silently=False,
                        )
            except (OSError, SMTPException):
                submitted = False
                messages.error(
                    request,
                    'Không gửi được email khôi phục. Vui lòng kiểm tra cấu hình email và thử lại.',
                )
    return render(request, 'auth/buyer_forgot_password.html', {
        'page_name': 'forgot-password',
        'page_section': 'auth',
        'page_title': 'Khôi phục mật khẩu',
        'form': form,
        'submitted': submitted,
    })


@require_http_methods(['GET', 'POST'])
def buyer_reset_password(request, token):
    record = (
        PasswordResetToken.objects.filter(
            token=token,
            used=False,
            expires_at__gt=timezone.now(),
            user__role__in=BUYER_ROLES,
            user__is_staff=False,
            user__is_superuser=False,
        )
        .select_related('user')
        .first()
    )
    if record is None:
        messages.error(request, 'Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.')
        return redirect('auth_login')

    form = BuyerSetPasswordForm(request.POST or None, user=record.user)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            account = User.objects.select_for_update().filter(
                pk=record.user_id,
                role__in=BUYER_ROLES,
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
                return redirect('auth_login')
            account.set_password(form.cleaned_data['password1'])
            account.save(update_fields=['password'])
            PasswordResetToken.objects.filter(user=account, used=False).update(used=True)

        try:
            send_mail(
                'Mật khẩu PCMatch đã được thay đổi',
                'Mật khẩu tài khoản PCMatch của bạn vừa được thay đổi. '
                'Nếu bạn không thực hiện thay đổi này, hãy liên hệ bộ phận hỗ trợ ngay.',
                None,
                [account.email],
                fail_silently=False,
            )
        except (OSError, SMTPException):
            messages.error(
                request,
                'Mật khẩu đã được thay đổi nhưng chưa gửi được email thông báo. '
                'Vui lòng liên hệ bộ phận hỗ trợ nếu bạn không thực hiện thay đổi này.',
            )
        else:
            messages.success(request, 'Mật khẩu đã được thay đổi. Vui lòng đăng nhập lại.')
        return redirect('auth_login')

    return render(request, 'auth/buyer_reset_password.html', {
        'page_name': 'reset-password',
        'page_section': 'auth',
        'page_title': 'Đặt lại mật khẩu',
        'form': form,
    })


@require_http_methods(['GET', 'POST'])
def staff_logout(request):
    logout(request)
    return redirect('staff_login')


@require_http_methods(['GET', 'POST'])
def shop_logout(request):
    logout(request)
    return redirect('shop_login')


def is_staff_user(user):
    return (
        user.is_authenticated
        and user.is_active
        and getattr(user, 'status', 'ACTIVE') == 'ACTIVE'
        and (user.is_staff or getattr(user, 'role', '') == 'ADMIN')
    )

staff_required = user_passes_test(is_staff_user, login_url=reverse_lazy('staff_login'))


@require_GET
def legacy_auth(request, destination='shop_dashboard', mode='login'):
    """Old bookmarks redirect to auth without retaining a separate login form."""
    query = {'next': safe_auth_next(request, destination)}
    if mode == 'register':
        query['mode'] = 'register'
    return redirect(reverse('auth_login') + '?' + urlencode(query))


# --- Admin (staff) authentication -------------------------------------------------

STAFF_LOGIN_OTP_KEY = 'staff_login_otp'
STAFF_LOGIN_OTP_TTL = 300


def _apply_remember(request, remember):
    """Keep the session alive for 30 days when "Remember me" is checked."""
    request.session.set_expiry(60 * 60 * 24 * 30 if remember else 0)


@require_http_methods(['GET', 'POST'])
def staff_login(request):
    """Dedicated administrator sign-in at /staff/login/ (separate from the buyer form)."""
    destination = safe_auth_next(request, 'staff_dashboard')
    if is_staff_user(request.user):
        return redirect(destination)

    stage = 'credentials'
    dev_otp = None
    otp_error = None
    form = StaffLoginForm(request.POST or None)
    if request.method == 'POST':
        stage = request.POST.get('stage') or 'credentials'

    if request.method == 'POST' and stage == 'otp':
        pending = request.session.get(STAFF_LOGIN_OTP_KEY) or {}
        code = (request.POST.get('otp') or '').strip()
        if not pending or pending.get('expires', 0) <= time():
            request.session.pop(STAFF_LOGIN_OTP_KEY, None)
            messages.error(request, 'Phiên xác thực đã hết hạn, vui lòng đăng nhập lại.')
            stage = 'credentials'
        elif pending.get('code') != code:
            otp_error = 'Mã OTP không đúng hoặc đã hết hạn.'
            dev_otp = pending.get('code') if settings.DEBUG else None
        else:
            account = User.objects.filter(pk=pending.get('user_id')).first()
            request.session.pop(STAFF_LOGIN_OTP_KEY, None)
            if account is None or not is_staff_user(account):
                otp_error = 'Bạn không có quyền truy cập admin.'
                stage = 'credentials'
            else:
                login(request, account)
                _apply_remember(request, pending.get('remember'))
                return redirect(destination)
    elif request.method == 'POST':
        if form.is_valid():
            identifier = form.cleaned_data['username'].strip()
            found = User.objects.filter(
                Q(username__iexact=identifier) | Q(email__iexact=identifier)
            ).first()
            if found is None:
                form.add_error(None, 'Tài khoản không tồn tại.')
            else:
                account = authenticate(
                    request, username=found.username,
                    password=form.cleaned_data['password'],
                )
                if account is None:
                    form.add_error(None, 'Sai mật khẩu.')
                elif not is_staff_user(account):
                    form.add_error(None, 'Bạn không có quyền truy cập admin.')
                elif account.two_factor_enabled:
                    otp = {
                        'code': get_random_string(6, allowed_chars='0123456789'),
                        'expires': time() + STAFF_LOGIN_OTP_TTL,
                        'user_id': account.pk,
                        'remember': form.cleaned_data.get('remember_me', False),
                    }
                    request.session[STAFF_LOGIN_OTP_KEY] = otp
                    send_mail(
                        'Mã xác thực đăng nhập quản trị PCMatch',
                        f'Mã OTP đăng nhập admin của bạn là: {otp["code"]}\n'
                        f'Mã có hiệu lực trong {STAFF_LOGIN_OTP_TTL // 60} phút.',
                        None, [account.email], fail_silently=True,
                    )
                    stage = 'otp'
                    dev_otp = otp['code'] if settings.DEBUG else None
                else:
                    login(request, account)
                    _apply_remember(request, form.cleaned_data.get('remember_me', False))
                    return redirect(destination)

    return render(request, 'staff/login.html', {
        'page_name': 'login',
        'page_section': 'staff',
        'page_title': 'Đăng nhập quản trị',
        'form': form,
        'stage': stage,
        'otp_error': otp_error,
        'dev_otp': dev_otp,
        'next': destination,
    })


def staff_forgot_password(request):
    """Step 1 of admin password recovery: email a reset link to a staff account."""
    form = StaffForgotPasswordForm(request.POST or None)
    reset_link = None
    submitted = False
    if request.method == 'POST' and form.is_valid():
        submitted = True
        email = form.cleaned_data['email'].strip().lower()
        account = User.objects.filter(email__iexact=email).first()
        # Only staff accounts can recover access; existence is never revealed.
        if account is not None and is_staff_user(account):
            token = PasswordResetToken.objects.create(
                user=account,
                token=get_random_string(48),
                expires_at=timezone.now() + timedelta(hours=1),
            )
            reset_link = request.build_absolute_uri(
                reverse('staff_reset_password', args=[token.token])
            )
            send_mail(
                'Đặt lại mật khẩu quản trị PCMatch',
                'Bạn đã yêu cầu đặt lại mật khẩu quản trị. Truy cập liên kết sau '
                f'(hiệu lực 1 giờ):\n{reset_link}',
                None, [account.email], fail_silently=True,
            )
    return render(request, 'staff/forgot_password.html', {
        'page_name': 'forgot-password',
        'page_section': 'staff',
        'page_title': 'Khôi phục mật khẩu quản trị',
        'form': form,
        'submitted': submitted,
        'reset_link': reset_link if settings.DEBUG else None,
    })


@require_http_methods(['GET', 'POST'])
def staff_reset_password(request, token):
    """Step 2 of admin password recovery: choose a new password from the emailed link."""
    record = (PasswordResetToken.objects
              .filter(token=token, used=False)
              .select_related('user')
              .first())
    if record is None or record.expires_at < timezone.now():
        messages.error(request, 'Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.')
        return redirect('staff_login')
    form = StaffSetPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        account = record.user
        account.set_password(form.cleaned_data['password1'])
        account.save(update_fields=['password'])
        record.used = True
        record.save(update_fields=['used'])
        messages.success(request, 'Mật khẩu đã được cập nhật. Vui lòng đăng nhập lại.')
        return redirect('staff_login')
    return render(request, 'staff/reset_password.html', {
        'page_name': 'reset-password',
        'page_section': 'staff',
        'page_title': 'Đặt lại mật khẩu quản trị',
        'form': form,
        'token': token,
    })


def guest_list(request):
    danhSach = User.objects.exclude(is_superuser=True).exclude(role='ADMIN').order_by('-date_joined', '-id')

    search = request.GET.get('search', '').strip()

    if search != '':
        danhSach = (danhSach.filter(full_name__icontains=search) | danhSach.filter(email__icontains=search) | danhSach.filter(phone__icontains=search))

    dividePage = Paginator(danhSach, 10)
    numPage = request.GET.get('page')
    showUser = dividePage.get_page(numPage)

    box = {
        'page_name': 'guest',
        'page_section': 'staff',
        'showUser': showUser,
        'search': search,
    }
    return render(request, 'admin/guest.html', box)

def toggle_user_lock(request, user_id):
    user = User.objects.filter(id=user_id).first()
    if (not user):
        messages.error(request, 'User not found.')
        return redirect('staff_guest')
    if user.is_superuser or user.role == 'ADMIN':
        messages.error(request, 'You cannot lock this user.')
        return redirect('staff_guest')

    if user.is_active:
        user.is_active = False
        messages.success(request, 'User has been locked.')
    else:
        user.is_active = True
        messages.success(request, 'User has been unlocked.')

    user.save()
    return redirect('staff_guest')
