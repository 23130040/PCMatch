from time import time

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from users.models import User
from users.forms import BuyerLoginForm, BuyerRegisterForm


def is_active_buyer(user):
    return user.is_authenticated and user.is_active and user.status == 'ACTIVE'


buyer_required = user_passes_test(is_active_buyer, login_url=reverse_lazy('auth_login'))


def safe_buyer_next(request):
    candidate = request.POST.get('next') or request.GET.get('next') or reverse('buyer_cart')
    if (candidate.startswith(('/buyer/', '/shop/')) and not candidate.startswith('//')
            and url_has_allowed_host_and_scheme(candidate, {request.get_host()}, require_https=request.is_secure())):
        return candidate
    return reverse('buyer_cart')


def finish_buyer_login(request):
    from carts.services import add_product

    pending = request.session.pop('pending_cart_add', None)
    if pending and pending.get('expires', 0) > time():
        try:
            add_product(request.user, pending['product_id'], pending['quantity'])
            messages.success(request, 'Đã thêm sản phẩm vào giỏ hàng.')
        except ValidationError as error:
            messages.error(request, error.messages[0])
        return redirect('buyer_cart')
    return redirect(safe_buyer_next(request))


def buyer_login(request):
    mode = request.POST.get('mode') or request.GET.get('mode', 'login')
    mode = 'register' if mode == 'register' else 'login'
    form_class = BuyerRegisterForm if mode == 'register' else BuyerLoginForm
    form = form_class(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        if mode == 'register':
            try:
                with transaction.atomic():
                    account = form.save()
            except IntegrityError:
                form.add_error('email', 'Email đã được đăng ký.')
            else:
                login(request, account)
                return finish_buyer_login(request)
        else:
            found = User.objects.filter(email__iexact=form.cleaned_data['email']).first()
            account = authenticate(request, username=found.username if found else form.cleaned_data['email'],
                                   password=form.cleaned_data['password'])
            if account is None or not is_active_buyer(account):
                form.add_error(None, 'Email hoặc mật khẩu không đúng, hoặc tài khoản đã bị khóa.')
            else:
                login(request, account)
                return finish_buyer_login(request)
    return render(request, 'auth/login.html', {
        'page_name': 'login', 'page_section': 'auth', 'form': form,
        'mode': mode, 'next': safe_buyer_next(request),
    })


@require_POST
def buyer_logout(request):
    logout(request)
    return redirect('auth_login')

def is_staff_user(user):
    return (
        user.is_authenticated
        and user.is_active
        and getattr(user, 'status', 'ACTIVE') == 'ACTIVE'
        and (user.is_staff or getattr(user, 'role', '') == 'ADMIN')
    )

staff_required = user_passes_test(is_staff_user, login_url=reverse_lazy('staff_login'))

def safe_staff_next(request, default='staff_dashboard'):
    fallback = reverse(default)
    candidate = request.POST.get('next') or request.GET.get('next') or fallback
    if (
        url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()})
        and candidate.startswith('/staff/')
    ):
        return candidate
    return fallback

def staff_login(request):
    if is_staff_user(request.user):
        return redirect(safe_staff_next(request))
    context = {
        'page_name': 'login',
        'page_section': 'staff',
        'next': request.GET.get('next', ''),
    }
    if request.method != 'POST':
        return render(request, 'admin/login.html', context)

    identifier = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    context['username'] = identifier
    if not identifier or not password:
        context['form_error'] = 'Vui lòng nhập email/tên đăng nhập và mật khẩu.'
        return render(request, 'admin/login.html', context)

    account = authenticate(request, username=identifier, password=password)
    if account is None and '@' in identifier:
        found = User.objects.filter(email__iexact=identifier).first()
        if found:
            account = authenticate(request, username=found.username, password=password)
    if account is None:
        context['form_error'] = 'Email/tên đăng nhập hoặc mật khẩu chưa đúng.'
        return render(request, 'admin/login.html', context)
    if not account.is_active or getattr(account, 'status', 'ACTIVE') != 'ACTIVE':
        context['form_error'] = 'Tài khoản đã bị khóa hoặc vô hiệu hóa.'
        return render(request, 'admin/login.html', context)
    if not (account.is_staff or getattr(account, 'role', '') == 'ADMIN'):
        context['form_error'] = 'Tài khoản không có quyền quản trị hệ thống.'
        return render(request, 'admin/login.html', context)

    login(request, account)
    return redirect(safe_staff_next(request))

def staff_logout(request):
    if request.method != 'POST':
        return redirect('staff_dashboard')
    logout(request)
    return redirect('staff_login')

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
