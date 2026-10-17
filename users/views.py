from time import time
from urllib.parse import urlencode

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from users.models import User
from users.forms import LoginForm, BuyerRegisterForm


def is_active_buyer(user):
    return user.is_authenticated and user.is_active and user.status == 'ACTIVE'


buyer_required = user_passes_test(is_active_buyer, login_url=reverse_lazy('auth_login'))


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
                login(request, account)
                return finish_auth_login(request, destination)
        else:
            found = User.objects.filter(email__iexact=form.cleaned_data['email']).first()
            account = authenticate(request, username=found.username if found else form.cleaned_data['email'],
                                   password=form.cleaned_data['password'])
            if account is None or not is_active_buyer(account):
                form.add_error(None, 'Email hoặc mật khẩu không đúng, hoặc tài khoản đã bị khóa.')
            elif staff_destination and not is_staff_user(account):
                form.add_error(None, 'Tài khoản không có quyền quản trị hệ thống.')
            else:
                login(request, account)
                return finish_auth_login(request, destination)
    return render(request, 'auth/login.html', {
        'page_name': 'login', 'page_section': 'auth', 'form': form,
        'page_title': 'Đăng ký tài khoản' if mode == 'register' else 'Đăng nhập',
        'mode': mode, 'next': destination,
    })


@require_POST
def auth_logout(request):
    logout(request)
    return redirect('auth_login')


def is_staff_user(user):
    return (
        user.is_authenticated
        and user.is_active
        and getattr(user, 'status', 'ACTIVE') == 'ACTIVE'
        and (user.is_staff or getattr(user, 'role', '') == 'ADMIN')
    )

staff_required = user_passes_test(is_staff_user, login_url=reverse_lazy('auth_login'))


@require_GET
def legacy_auth(request, destination='shop_dashboard', mode='login'):
    """Old bookmarks redirect to auth without retaining a separate login form."""
    query = {'next': safe_auth_next(request, destination)}
    if mode == 'register':
        query['mode'] = 'register'
    return redirect(reverse('auth_login') + '?' + urlencode(query))


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
