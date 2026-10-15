from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme

from users.models import User


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
