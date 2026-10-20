from django.shortcuts import render, redirect
from orders.models import Order
from django.core.paginator import Paginator
from django.contrib import messages


def order_list(request):
    allOrder = Order.objects.all().order_by('-created_at')

    locStatus = request.GET.get('status', '').strip()
    if locStatus != '':
        allOrder = allOrder.filter(order_status=locStatus)

    search = request.GET.get('search', '').strip()
    if search != '':
        allOrder = allOrder.filter(order_code__icontains=search)

    dividePage = Paginator(allOrder, 10)
    numPage = request.GET.get('page')
    showOrder = dividePage.get_page(numPage)

    box = {
        'showOrder': showOrder,
        'locStatus': locStatus,
        'search': search,
    }
    return render(request, 'admin/order.html', box)


def changeStatus(request, order_id):
    order = Order.objects.filter(order_id=order_id).first()
    if not order:
        messages.error(request, 'Order not found.') 
        
        return redirect('admin_order_list')

    newStatus = request.GET.get('status', '').strip()
    if newStatus != '':
        order.order_status = newStatus
        order.save()
        messages.success(request, f'Order status updated to {newStatus}.')
        

    return redirect('load_ListOrder')