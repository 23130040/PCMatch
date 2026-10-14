from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Count, Q
from .forms import AdminProductFilterForm, CatalogFilterForm
from .models import Product

def load_products(request):
    selling = Q(status='ACTIVE', stock_quantity__gt=0)
    out_of_stock = Q(status='OUT_OF_STOCK') | Q(status='ACTIVE', stock_quantity__lte=0)
    status_filters = {
        'ACTIVE': selling, 'OUT_OF_STOCK': out_of_stock, 'INACTIVE': Q(status='INACTIVE'),
    }
    counts = {
        'total': Count('pk'),
        'selling': Count('pk', filter=selling),
        'out_of_stock': Count('pk', filter=out_of_stock),
        'hidden': Count('pk', filter=Q(status='INACTIVE')),
    }
    products = Product.objects.select_related('category', 'shop', 'brand')
    stats = products.aggregate(**counts)
    filter_form = AdminProductFilterForm(request.GET)
    selected_status = request.GET.get('status', '')
    if filter_form.is_valid():
        filters = filter_form.cleaned_data
        keyword = filters['search']
        if keyword:
            matches = Q(product_name__icontains=keyword) | Q(shop__shop_name__icontains=keyword)
            product_id = keyword.lstrip('#')
            if product_id.isascii() and product_id.isdigit() and len(product_id) <= 18:
                matches |= Q(product_id=product_id)
            products = products.filter(matches)
        for name in ['category', 'shop']:
            if filters[name] is not None:
                products = products.filter(**{name: filters[name]})
    else:
        products = products.none()

    tab_counts = products.aggregate(**counts)
    if selected_status in status_filters:
        products = products.filter(status_filters[selected_status])
    products = products.order_by('-created_at', '-product_id')
    show_product = Paginator(products, 10).get_page(request.GET.get('page'))
    query_params = request.GET.copy()
    query_params.pop('page', None)
    context = {
        'page_name': 'products', 'page_section': 'staff',
        'showProduct': show_product, 'filter_form': filter_form, 'stats': stats,
        'locStatus': selected_status, 'query_string': query_params.urlencode(),
        'status_tabs': [
            {'value': value, 'label': label, 'count': tab_counts[count_name]}
            for value, label, count_name in [
                ('', 'Tất cả', 'total'), ('ACTIVE', 'Đang bán', 'selling'),
                ('OUT_OF_STOCK', 'Hết hàng', 'out_of_stock'), ('INACTIVE', 'Tạm ẩn', 'hidden'),
            ]
        ],
    }
    return render(request, 'admin/products.html', context)

def showORhide_Product(request, product_id):
    product = Product.objects.filter(product_id=product_id).first()
    if not product:
        messages.error(request, 'Product not found.')
        return redirect('load_products')

    if product.status == 'ACTIVE':
        product.status = 'INACTIVE'
        messages.success(request, 'Product has been hidden.')
    else:
        product.status = 'ACTIVE'
        messages.success(request, 'Product has been shown.')

    product.save()
    return redirect('load_products')

def buyer_product_list(request):
    products = (
        Product.objects.select_related('category', 'shop', 'brand')
        .prefetch_related('specifications')
    )
    filter_form = CatalogFilterForm(request.GET)
    if filter_form.is_valid():
        filters = filter_form.cleaned_data
        keyword = filters['q']
        if keyword:
            products = products.filter(
                Q(product_name__icontains=keyword)
                | Q(brand__brand_name__icontains=keyword)
                | Q(slug__icontains=keyword)
            )
        for field in ['category', 'brand', 'shop']:
            if filters[field] is not None:
                products = products.filter(**{field: filters[field]})
        if filters['min'] is not None:
            products = products.filter(price__gte=filters['min'])
        if filters['max'] is not None:
            products = products.filter(price__lte=filters['max'])
        if filters['availability'] == 'in':
            products = products.filter(status='ACTIVE', stock_quantity__gt=0)
        elif filters['availability'] == 'out':
            products = products.filter(
                Q(status='OUT_OF_STOCK') | Q(status='ACTIVE', stock_quantity__lte=0)
            )
        elif filters['availability'] == 'paused':
            products = products.filter(status='INACTIVE')
        for name in filter_form.technical_names:
            if filters[name]:
                products = products.filter(
                    specifications__specification_name=name[5:],
                    specifications__specification_value=filters[name],
                )
        ordering = {
            'price': ('price', 'product_id'),
            'desc': ('-price', 'product_id'),
            'sold': ('-sold_quantity', 'product_id'),
            'name': ('product_name', 'product_id'),
        }.get(filters['sort'], ('category__category_name', '-created_at', '-product_id'))
        products = products.order_by(*ordering).distinct()
    else:
        products = products.none()

    pagination = Paginator(products, 6)
    page_obj = pagination.get_page(request.GET.get('p'))

    query_params = request.GET.copy()
    query_params.pop('p', None)
    context = {
        'page_name': 'search',
        'page_section': 'buyer',
        'page_obj': page_obj,
        'keyword': request.GET.get('q', '').strip(),
        'filter_form': filter_form,
        'technical_filters': [filter_form[name] for name in filter_form.technical_names],
        'query_string': query_params.urlencode(),
    }

    return render(request, 'buyer/search.html', context)


def buyer_product_compare(request):
    context = {'page_name': 'compare', 'page_section': 'buyer'}
    if request.GET.get('source') != 'database':
        return render(request, 'buyer/compare.html', context)

    ids = []
    for value in request.GET.get('products', '')[:100].split(','):
        if value.isascii() and value.isdigit() and len(value) <= 18:
            product_id = int(value)
            if product_id not in ids:
                ids.append(product_id)
        if len(ids) == 4:
            break
    found = {
        product.pk: product for product in Product.objects.filter(pk__in=ids)
        .select_related('category', 'brand', 'shop').prefetch_related('specifications')
    }
    products = [found[product_id] for product_id in ids if product_id in found]
    error = ''
    if len({product.category_id for product in products}) > 1:
        error = 'Chỉ so sánh sản phẩm cùng danh mục.'
        products = []

    rows = [
        {'label': 'Danh mục', 'values': [product.category.category_name for product in products]},
        {'label': 'Hãng', 'values': [product.brand.brand_name if product.brand else '—' for product in products]},
        {'label': 'Giá bán', 'kind': 'price', 'values': [product.price for product in products]},
        {'label': 'Shop bán', 'values': [product.shop.shop_name for product in products]},
        {'label': 'Tồn kho', 'values': [product.stock_quantity for product in products]},
        {'label': 'Tình trạng', 'values': [
            'Tạm ngừng bán' if product.status == 'INACTIVE' else
            'Hết hàng' if product.status == 'OUT_OF_STOCK' or product.stock_quantity <= 0 else 'Còn hàng'
            for product in products
        ]},
    ]
    specifications = {
        product.pk: {
            item.specification_name: item.specification_value
            for item in product.specifications.all()
        } for product in products
    }
    names = sorted({name for values in specifications.values() for name in values})
    rows += [
        {'label': name, 'values': [specifications[product.pk].get(name, '—') for product in products]}
        for name in names
    ]
    context.update({
        'catalog_source': 'database', 'compared_products': products,
        'comparison_rows': rows, 'comparison_error': error,
        'compare_items': [
            {'id': str(product.pk), 'category': str(product.category_id), 'name': product.product_name}
            for product in products
        ],
    })
    return render(request, 'buyer/compare.html', context)


def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand', 'shop').prefetch_related('specifications'),
        product_id=product_id,
    )

    context = {
        'page_name': 'model',
        'page_section': 'buyer',
        'catalog_source': 'database',
        'selected_product': product,
    }

    return render(request, 'buyer/model.html', context)
