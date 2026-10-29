from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from orders.models import Order
from shops.models import Shop


MONTH_NAMES = (
    'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6',
    'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12',
)


def _parse_int(value, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if minimum <= parsed <= maximum else None


def _parse_year_month(value, minimum_year, maximum_year):
    try:
        year_value, month_value = (int(part) for part in value.split('-', 1))
    except (AttributeError, TypeError, ValueError):
        return None
    if not minimum_year <= year_value <= maximum_year or not 1 <= month_value <= 12:
        return None
    return year_value, month_value


def _month_starts(start, end):
    current = start.replace(day=1)
    final = end.replace(day=1)
    months = []
    while current <= final:
        months.append(current)
        current = date(current.year + 1, 1, 1) if current.month == 12 else date(current.year, current.month + 1, 1)
    return months


def _filter_period(request):
    today = timezone.localdate()
    current_year = today.year
    selected_year = _parse_int(request.GET.get('year'), 2000, current_year + 1) or current_year
    selected_month = _parse_int(request.GET.get('month'), 1, 12)
    selected_period_month = _parse_year_month(request.GET.get('period_month'), 2000, current_year + 1)
    if selected_period_month:
        selected_year, selected_month = selected_period_month
    has_year_selection = bool(request.GET.get('year'))
    requested_start = parse_date(request.GET.get('from_date', ''))
    requested_end = parse_date(request.GET.get('to_date', ''))
    preset = request.GET.get('preset', '').lower()

    if requested_start and requested_end and requested_start > requested_end:
        requested_start, requested_end = requested_end, requested_start

    if requested_start and requested_end:
        chart_start, chart_end = requested_start, requested_end
        start_date, end_date = chart_start, chart_end
        label = f'Từ {chart_start:%d/%m/%Y} đến {chart_end:%d/%m/%Y}'
        preset = ''
    elif preset == 'all':
        first_order = Order.objects.order_by('created_at').values_list('created_at', flat=True).first()
        chart_start = timezone.localdate(first_order).replace(day=1) if first_order else date(current_year, 1, 1)
        chart_end = today
        start_date = end_date = None
        label = 'Tất cả thời gian'
    elif preset == 'today':
        chart_start = chart_end = start_date = end_date = today
        label = f'Hôm nay · {today:%d/%m/%Y}'
    elif preset in {'7days', '30days'}:
        number_of_days = 7 if preset == '7days' else 30
        chart_start = start_date = today - timedelta(days=number_of_days - 1)
        chart_end = end_date = today
        label = f'{number_of_days} ngày qua'
    elif preset in {'month', 'quarter', 'year'}:
        if preset == 'month':
            chart_start = date(today.year, today.month, 1)
            label = f'Tháng này · {today:%m/%Y}'
        elif preset == 'quarter':
            quarter_start_month = ((today.month - 1) // 3) * 3 + 1
            chart_start = date(today.year, quarter_start_month, 1)
            label = f'Quý {(today.month - 1) // 3 + 1} · {today.year}'
        else:
            chart_start = date(today.year, 1, 1)
            label = f'Năm nay · {today.year}'
        chart_end = today
        start_date, end_date = chart_start, chart_end

    elif selected_month:
        chart_start = date(selected_year, selected_month, 1)
        chart_end = date(selected_year + (selected_month == 12), 1 if selected_month == 12 else selected_month + 1, 1) - timedelta(days=1)
        start_date, end_date = chart_start, chart_end
        label = f'{MONTH_NAMES[selected_month - 1]} {selected_year}'
    elif has_year_selection:
        chart_start, chart_end = date(selected_year, 1, 1), date(selected_year, 12, 31)
        start_date, end_date = chart_start, chart_end
        label = f'Năm {selected_year}'
    else:
        chart_start = chart_end = start_date = end_date = today
        preset = 'today'
        label = f'Hôm nay · {today:%d/%m/%Y}'

    return {
        'start_date': start_date,
        'end_date': end_date,
        'chart_start': chart_start,
        'chart_end': chart_end,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'month_input_value': f'{selected_year:04d}-{selected_month:02d}' if selected_month else f'{today:%Y-%m}',
        'active_preset': preset,
        'active_picker_tab': 'year' if has_year_selection and not selected_month and not preset else 'month',
        'requested_start': requested_start,
        'requested_end': requested_end,
        'label': label,
    }


def _filtered_orders(period):
    orders = Order.objects.all()
    if period['start_date']:
        orders = orders.filter(created_at__date__gte=period['start_date'])
    if period['end_date']:
        orders = orders.filter(created_at__date__lte=period['end_date'])
    return orders


def _order_fee(order):
    if order.platform_fee:
        return order.platform_fee
    return sum(
        (item.subtotal * item.shop.platform_fee_percent / Decimal('100') for item in order.order_items.all()),
        Decimal('0'),
    )


def _status_summary(orders):
    values = [
        orders.filter(order_status='PENDING').count(),
        orders.filter(order_status__in=('COMFIRMED', 'PROCESSING', 'SHIPPING')).count(),
        orders.filter(order_status='DELIVERED').count(),
        orders.filter(order_status__in=('CANCELLED', 'RETURNED')).count(),
    ]
    total = sum(values)
    overview = [
        {'label': 'Chờ xác nhận', 'count': values[0], 'color': '#ed8b0c'},
        {'label': 'Đang giao', 'count': values[1], 'color': '#2f6ee8'},
        {'label': 'Đã giao', 'count': values[2], 'color': '#747e88'},
        {'label': 'Hoàn trả', 'count': values[3], 'color': '#ef6c00'},
    ]
    for status in overview:
        status['percent'] = (status['count'] / total * 100) if total else 0
    return {
        'total_orders': total,
        'listOrder': values,
        'status_labels': [status['label'] for status in overview],
        'order_status_overview': overview,
    }


def _dashboard_data(orders, period):
    completed_orders = list(orders.filter(order_status='DELIVERED').prefetch_related('order_items__shop'))
    months = _month_starts(period['chart_start'], period['chart_end'])
    revenue_by_month = {month: Decimal('0') for month in months}
    fee_by_month = {month: Decimal('0') for month in months}
    total_fee = Decimal('0')

    for order in completed_orders:
        month = timezone.localdate(order.created_at).replace(day=1)
        if month not in revenue_by_month:
            continue
        revenue_by_month[month] += order.total_amount
        fee = _order_fee(order)
        fee_by_month[month] += fee
        total_fee += fee

    total_revenue = sum(revenue_by_month.values(), Decimal('0'))
    shop_sales = Shop.objects.filter(status='ACTIVE').annotate(
        delivered_revenue=Sum(
            'order_items__subtotal',
            filter=Q(order_items__order__in=orders, order_items__order__order_status='DELIVERED'),
            default=0,
        ),
        order_count=Count('order_items__order_id', filter=Q(order_items__order__in=orders), distinct=True),
    ).filter(order_count__gt=0)
    return {
        'chart_labels': [MONTH_NAMES[month.month - 1] for month in months],
        'list_DoanhThu_12Months': [float(revenue_by_month[month]) for month in months],
        'list_Phi_12Months': [float(fee_by_month[month]) for month in months],
        'chart_total_revenue': total_revenue,
        'chart_total_fee': total_fee,
        'chart_fee_rate': (total_fee / total_revenue * 100) if total_revenue else 0,
        'period_revenue': total_revenue,
        'period_fee': total_fee,
        'period_order_count': orders.count(),
        'period_active_shop_count': shop_sales.count(),
        'top_shops_by_revenue': list(shop_sales.order_by('-delivered_revenue', '-order_count', 'pk')[:10]),
        'top_shops_by_orders': list(shop_sales.order_by('-order_count', '-delivered_revenue', 'pk')[:10]),
    }


def dashboard_view(request):
    period = _filter_period(request)
    orders = _filtered_orders(period)
    pending_shops = list(
        Shop.objects.filter(status='PENDING').select_related('owner')
        .order_by('-legal_submitted_at', '-created_at', '-pk')[:4]
    )
    for shop in pending_shops:
        shop.document_count = int(bool(shop.id_card)) + int(bool(shop.business_license))

    available_years = {value.year for value in Order.objects.dates('created_at', 'year')}
    available_years.add(period['selected_year'])
    context = {}
    context.update(_dashboard_data(orders, period))
    context.update(_status_summary(orders))
    context.update({
        'current_year': timezone.localdate().year,
        'period_label': period['label'],
        'selected_year': period['selected_year'],
        'selected_month': period['selected_month'],
        'month_input_value': period['month_input_value'],
        'active_preset': period['active_preset'],
        'active_picker_tab': period['active_picker_tab'],
        'from_date': period['requested_start'].isoformat() if period['requested_start'] else '',
        'to_date': period['requested_end'].isoformat() if period['requested_end'] else '',
        'month_options': [(index, label) for index, label in enumerate(MONTH_NAMES, start=1)],
        'year_options': sorted(available_years, reverse=True),
        'dashboard_updated_at': timezone.localtime(),
        'pending_shops': pending_shops,
        'pending_shop_count': Shop.objects.filter(status='PENDING').count(),
    })
    return render(request, 'admin/dashboard.html', context)
