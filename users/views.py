from django.shortcuts import render, redirect
from user.models import User
from django.core.paginator import Paginator
from django.contrib import messages




    def ListView(request ):
        danhSach = User.objects.exclude(is_superuser=True).exclude(role='ADMIN')

        search = request.GET.get('search', '').strip()

        if search != '':
            danhSach = ( danhSach.filter(full_name__icontains=search) | danhSach.filter(email__icontains=search) | danhSach.filter(phone__icontains=search))

        dividePage = Paginator(danhSach, 10)
        numPage = request.GET.get('page')
        showUser = dividePage.get_page(numPage)

        box = {
            'showUser': showUser,
            'search': search,
        }
        return render(request, 'admin/guest.html', box)


def lockUser ( request , user_id):#
    user = User.objects.filter(id=user_id).first()
    if ( not user):
        messages.error(request, 'User not found.')
        return redirect('load_web')
    if user.is_superuser or user.role == 'ADMIN':
        messages.error(request, 'You cannot lock this user.')
        return redirect('load_web')

    if user.is_active:
        user.is_active = False
        messages.success(request, 'User has been locked.')
    else:
        user.is_active = True
        messages.success(request, 'User has been unlocked.')

    user.save()
    return redirect('load_web')