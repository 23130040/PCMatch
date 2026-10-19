"""Server-rendered Shop screens. Browser storage is never used as business data."""

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from time import time
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import user_passes_test
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.views.decorators.http import require_GET, require_POST

from orders.models import Order, OrderItem, Return
from products.models import Category, Product, ProductQuestion
from users.models import EmailVerificationToken, User
from users.views import finish_auth_login, is_active_seller, safe_auth_next

from .forms import PhoneOTPForm, SellerRegisterForm, ShopLegalForm, ShopLoginForm, ShopProfileForm
from .models import Shop


shop_required = user_passes_test(is_active_seller, login_url=reverse_lazy('shop_login'))

OTP_SESSION_KEY = 'shop_phone_otp'
OTP_TTL_SECONDS = 300


def _owned_shop(user):
    return Shop.objects.filter(owner=user).order_by('pk').first()


def shop_login(request):
    """Seller sign-in. Uses the shared Django account/session, not a separate one."""
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


def _send_verification_email(request, account, token):
    link = request.build_absolute_uri(reverse('shop_verify_email_confirm', args=[token.token]))
    send_mail(
        'Kích hoạt tài khoản người bán PCMatch',
        f'Vui lòng kiểm tra email và bấm vào liên kết sau để kích hoạt tài khoản người bán:\n{link}',
        None,
        [account.email],
        fail_silently=True,
    )


def shop_register(request):
    """Step 1: create a seller account (unique username/email, strong password)."""
    if is_active_seller(request.user) and _owned_shop(request.user):
        return redirect('shop_dashboard')
    form = SellerRegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        account = form.save()
        token = EmailVerificationToken.objects.create(
            user=account,
            token=get_random_string(48),
            expires_at=timezone.now() + timedelta(days=1),
        )
        _send_verification_email(request, account, token)
        login(request, account)
        return redirect('shop_verify_email')
    return render(request, 'shop/register.html', {
        'page_name': 'register',
        'page_section': 'shop',
        'page_title': 'Đăng ký tài khoản người bán',
        'form': form,
    })


@require_GET
def shop_verify_email(request):
    """Step 2a: ask the seller to confirm their email address."""
    if not is_active_seller(request.user):
        return redirect('shop_login')
    if request.user.email_verified:
        return redirect('shop_verify_phone')
    token = EmailVerificationToken.objects.filter(
        user=request.user, verified_at__isnull=True,
    ).order_by('-created_at').first()
    return render(request, 'shop/verify_email.html', {
        'page_name': 'verify-email',
        'page_section': 'shop',
        'page_title': 'Xác thực email',
        'activation_url': reverse('shop_verify_email_confirm', args=[token.token]) if token else None,
    })


@require_GET
def shop_verify_email_confirm(request, token):
    """Activation link target. Marks the account email as verified."""
    record = get_object_or_404(EmailVerificationToken, token=token)
    if record.verified_at is not None or record.expires_at < timezone.now():
        messages.error(request, 'Liên kết xác thực không hợp lệ hoặc đã hết hạn.')
        return redirect('shop_verify_email')
    record.verified_at = timezone.now()
    record.save(update_fields=['verified_at'])
    account = record.user
    account.email_verified = True
    account.save(update_fields=['email_verified'])
    if not request.user.is_authenticated:
        login(request, account)
    return redirect('shop_verify_phone')


def shop_verify_phone(request):
    """Step 2b: confirm the phone number with a one-time code."""
    if not is_active_seller(request.user):
        return redirect('shop_login')
    if not request.user.email_verified:
        return redirect('shop_verify_email')
    if request.user.phone_verified:
        return redirect('shop_onboarding_profile')

    otp = request.session.get(OTP_SESSION_KEY)
    form = PhoneOTPForm(request.POST or None, initial={'phone': request.user.phone})
    if request.method == 'POST' and form.is_valid():
        code = form.cleaned_data['code'].strip()
        if otp and otp.get('code') == code and otp.get('expires', 0) > time():
            request.user.phone = form.cleaned_data['phone']
            request.user.phone_verified = True
            request.user.save(update_fields=['phone', 'phone_verified'])
            request.session.pop(OTP_SESSION_KEY, None)
            return redirect('shop_onboarding_profile')
        form.add_error('code', 'Mã OTP không đúng hoặc đã hết hạn.')

    if not otp or otp.get('expires', 0) <= time():
        otp = {'code': get_random_string(6, allowed_chars='0123456789'), 'expires': time() + OTP_TTL_SECONDS}
        request.session[OTP_SESSION_KEY] = otp
    return render(request, 'shop/verify_phone.html', {
        'page_name': 'verify-phone',
        'page_section': 'shop',
        'page_title': 'Xác thực số điện thoại',
        'form': form,
        'dev_otp': otp['code'] if settings.DEBUG else None,
    })


def _onboarding_account_ready(request):
    """Return a redirect for the first incomplete step, or None when ready."""
    if not request.user.email_verified:
        return redirect('shop_verify_email')
    if not request.user.phone_verified:
        return redirect('shop_verify_phone')
    return None


def shop_onboarding_profile(request):
    """Step 3: create the shop profile (unique name, logo, contact info)."""
    if not is_active_seller(request.user):
        return redirect('shop_login')
    blocked = _onboarding_account_ready(request)
    if blocked:
        return blocked
    shop = _owned_shop(request.user)
    form = ShopProfileForm(request.POST or None, request.FILES or None, instance=shop)
    if request.method == 'POST' and form.is_valid():
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
    """Step 4: upload identity and business documents, then wait for approval."""
    if not is_active_seller(request.user):
        return redirect('shop_login')
    blocked = _onboarding_account_ready(request)
    if blocked:
        return blocked
    shop = _owned_shop(request.user)
    if shop is None:
        return redirect('shop_onboarding_profile')
    if shop.legal_submitted_at is not None:
        return redirect('shop_onboarding_pending')
    form = ShopLegalForm(request.POST or None, request.FILES or None, instance=shop)
    if request.method == 'POST' and form.is_valid():
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
    """Step 4 result: the shop is queued for admin review."""
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
        'page_title': 'Chờ xét duyệt',
        'shop': shop,
    })


@require_GET
def shop_notifications(request):
    """In-dashboard notifications, including the approval congratulations."""
    shop = _owned_shop(request.user)
    if shop is None or shop.status != 'ACTIVE':
        return redirect('shop_dashboard')
    return render(request, 'shop/notifications.html', {
        'page_name': 'notifications',
        'page_section': 'shop',
        'page_title': 'Thông báo',
        'shop': shop,
        'notifications': request.user.notifications.order_by('-created_at')[:50],
    })


ORDER_LABELS = {
    'PENDING': 'Chờ xác nhận', 'COMFIRMED': 'Đã xác nhận',
    'PROCESSING': 'Đang xử lý', 'SHIPPING': 'Đang giao',
    'DELIVERED': 'Đã giao', 'CANCELLED': 'Đã hủy', 'RETURNED': 'Đã hoàn hàng',
}
RETURN_LABELS = {'REQUESTED': 'Chờ xử lý', 'APPROVED': 'Đã duyệt', 'REJECTED': 'Từ chối', 'REFUNDED': 'Đã hoàn tiền'}
TITLES = {
    'dashboard': 'Tổng quan', 'offers': 'Quản lý sản phẩm', 'inventory': 'Quản lý tồn kho',
    'orders': 'Quản lý đơn hàng', 'order': 'Chi tiết đơn hàng', 'fulfillment': 'Quản lý giao nhận',
    'revenue': 'Báo cáo doanh thu', 'questions': 'Câu hỏi sản phẩm', 'aftersales': 'Hậu mãi',
    'build-requests': 'Yêu cầu cấu hình build', 'build-request-detail': 'Chi tiết yêu cầu build',
    'proposal-builder': 'Tạo báo giá', 'proposal-list': 'Báo giá đã gửi', 'proposal': 'Chi tiết báo giá',
}


def _orders(shop):
    if shop is None:
        return []
    own_items = OrderItem.objects.filter(shop=shop).select_related('product__category')
    queryset = Order.objects.filter(order_items__shop=shop).distinct().select_related('user', 'address').prefetch_related(
        Prefetch('order_items', queryset=own_items, to_attr='shop_items'), 'status_history',
    ).order_by('-created_at', '-pk')
    rows = list(queryset)
    for order in rows:
        order.shop_total = sum((item.subtotal for item in order.shop_items), Decimal('0'))
        order.status_label = ORDER_LABELS.get(order.order_status, order.get_order_status_display())
        order.status_css = 'success' if order.order_status == 'DELIVERED' else 'error' if order.order_status in {'CANCELLED', 'RETURNED'} else 'info'
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
    completed = [order for order in orders if order.order_status == 'DELIVERED' and start <= timezone.localdate(order.updated_at) <= today]
    daily = defaultdict(lambda: {'amount': Decimal('0'), 'count': 0})
    categories = defaultdict(Decimal)
    for order in completed:
        date = timezone.localdate(order.updated_at)
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
    # The seller dashboard is only available for an approved shop.
    shop = _owned_shop(request.user)
    if shop is None:
        return redirect('shop_onboarding_profile')
    if shop.status != 'ACTIVE':
        return redirect('shop_onboarding_pending')

    context = {'page_name': page, 'page_section': 'shop', 'page_title': TITLES[page]}

    # Every query starts from shops owned by this account. Query-string IDs cannot select another shop's data.
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
        'order_processing': sum(order.order_status in {'COMFIRMED', 'PROCESSING'} for order in orders),
        'order_delivered': sum(order.order_status == 'DELIVERED' for order in orders),
        'recent_orders': orders[:5], 'pending_orders': [order for order in orders if order.order_status in {'PENDING', 'COMFIRMED', 'PROCESSING'}][:5],
        'order_statuses': [{'code': code, 'label': label, 'count': sum(order.order_status == code for order in orders)} for code, label in ORDER_LABELS.items()],
        'revenue': _revenue(orders, 30), 'top_products': products.order_by('-sold_quantity', 'pk')[:5],
    })
    questions = ProductQuestion.objects.filter(product__shop=shop).select_related('product', 'user').prefetch_related('answers') if shop else ProductQuestion.objects.none()
    context['question_pending'] = questions.filter(status=False).count()
    context['recent_questions'] = questions.filter(status=False).order_by('-created_at')[:3]

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
        context['processing_orders'] = [order for order in orders if order.order_status in {'COMFIRMED', 'PROCESSING'}]
        context['shipping_orders'] = [order for order in orders if order.order_status == 'SHIPPING']
        context['order'] = None
        if page == 'order' and request.GET.get('id'):
            selected = _owned_object(Order.objects.filter(order_items__shop=shop).distinct(), request.GET['id'])
            context['order'] = next(order for order in orders if order.pk == selected.pk)
    elif page == 'questions':
        answered = request.GET.get('answered') == '1'
        context['answered'] = answered
        context['questions_page'] = Paginator(questions.filter(status=answered).order_by('-created_at'), 10).get_page(request.GET.get('page'))
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


# --- Staff shop management ----------------------------------------------------------

STAFF_SHOP_STATUSES = (
    ('PENDING', 'Chờ duyệt tham gia'),
    ('ACTIVE', 'Đang hoạt động'),
    ('SUSPENDED', 'Tạm ngưng'),
)
STAFF_SHOP_LABELS = dict(STAFF_SHOP_STATUSES)


@require_GET
def staff_shop_list(request):
    """Admin reviews every shop and the applications waiting for approval."""
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
    """Back to the staff list with the filters the admin was using."""
    query = {key: request.POST[key] for key in ('search', 'status', 'page') if request.POST.get(key)}
    url = reverse('staff_shop')
    return f'{url}?{urlencode(query)}' if query else url


@require_POST
def staff_shop_approve(request, shop_id):
    """Approve a shop so its seller can open the shop dashboard."""
    shop = get_object_or_404(Shop, pk=shop_id)
    if shop.status == 'ACTIVE':
        messages.info(request, f'Shop "{shop.shop_name}" đã được duyệt trước đó.')
    else:
        shop.status = 'ACTIVE'
        shop.save()  # Shop.save() notifies the owner and emails the approval.
        messages.success(request, f'Đã duyệt shop "{shop.shop_name}". Chủ shop đã được thông báo.')
    return redirect(_staff_shop_return(request))


@require_POST
def staff_shop_suspend(request, shop_id):
    """Suspend a shop; the seller loses the dashboard until it is approved again."""
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
