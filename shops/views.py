"""Server-rendered Shop screens. Browser storage is never used as business data."""

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, render
from django.http import Http404
from django.utils import timezone
from django.views.decorators.http import require_GET

from orders.models import Order, OrderItem, Return
from products.models import Category, Product, ProductQuestion

from .models import Shop


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
    context = {'page_name': page, 'page_section': 'shop', 'page_title': TITLES[page]}

    # Every query starts from shops owned by this account. Query-string IDs cannot select another shop's data.
    shop = Shop.objects.filter(owner=request.user).order_by('pk').first()
    products = Product.objects.filter(shop=shop).select_related('brand', 'category').order_by('-created_at', '-pk') if shop else Product.objects.none()
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
