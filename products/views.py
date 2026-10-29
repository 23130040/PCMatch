from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from urllib.parse import urlencode
from django.db.models import Count, Prefetch, Q
from django.db import DatabaseError
from .forms import AdminProductFilterForm, CatalogFilterForm, ProductFollowupForm, ProductQuestionForm
from .models import Category, Product, ProductQuestion
from .services import append_question_message, conversation_messages
from django.core.exceptions import ValidationError
from users.views import is_active_buyer
from shops.models import Shop
from .comparison import SESSION_KEY, comparison_products, parse_product_ids, session_products
from recommendations.services import get_recommended_products
from recommendations.services import get_frequently_bought_together

def buyer_home(request):
    products = (
        Product.objects
        .filter(status='ACTIVE')
        .select_related('category', 'brand', 'shop')
        .prefetch_related('specifications')
    )

    recommended_products = get_recommended_products(
        request.user,
        limit=8,
    )

    return render(request, 'buyer/home.html', {
        'page_name': 'home',
        'page_section': 'buyer',
        'categories': Category.objects.filter(
            status=True
        ).order_by('category_name'),
        'newest_products': products.order_by(
            '-created_at', '-pk'
        )[:4],
        'bestselling_products': products.order_by(
            '-sold_quantity', '-created_at', '-pk'
        )[:4],
        'recommended_products': recommended_products,
        'shops': Shop.objects.filter(
            status='ACTIVE'
        ).order_by('shop_name')[:6],
    })

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
    for product in show_product:
        product.current_sales_value = product.price * product.sold_quantity
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
        if request.user.is_authenticated:
            from interactions.models import FilterHistory

            filter_data = {
                'q': filters.get('q') or '',
                'category': (
                    str(filters['category'].pk)
                    if filters.get('category') else ''
                ),
                'brand': (
                    str(filters['brand'].pk)
                    if filters.get('brand') else ''
                ),
                'min': (
                    str(filters['min'])
                    if filters.get('min') is not None else ''
                ),
                'max': (
                    str(filters['max'])
                    if filters.get('max') is not None else ''
                ),
                'shop': (
                    str(filters['shop'].pk)
                    if filters.get('shop') else ''
                ),
                'availability': filters.get('availability') or '',
                'sort': filters.get('sort') or '',
                'technical': {
                    name[5:]: filters[name]
                    for name in filter_form.technical_names
                    if filters.get(name)
                },
            }

            has_filter = any([
                filter_data['q'],
                filter_data['category'],
                filter_data['brand'],
                filter_data['min'],
                filter_data['max'],
                filter_data['shop'],
                filter_data['availability'],
                filter_data['sort'],
                filter_data['technical'],
            ])

            if has_filter:
                FilterHistory.objects.create(
                    user=request.user,
                    filters=filter_data,
                )
        keyword = filters['q']
        if keyword:
            products = products.filter(
                Q(product_name__icontains=keyword)
                | Q(brand__brand_name__icontains=keyword)
                | Q(category__category_name__icontains=keyword)
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

    ids = parse_product_ids(request.GET.getlist('products')) if 'products' in request.GET else parse_product_ids(request.session.get(SESSION_KEY, []))
    products = comparison_products(ids)
    error = ''
    if len({product.category_id for product in products}) > 1:
        error = 'Chỉ so sánh sản phẩm cùng danh mục.'
        products = []
    request.session[SESSION_KEY] = [product.pk for product in products]

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


@require_POST
def buyer_comparison_update(request):
    products = session_products(request)
    action = request.POST.get('action')
    ids = parse_product_ids([request.POST.get('product_id', '')])
    error = ''
    message = ''
    if action == 'clear':
        products = []
        message = 'Đã xóa danh sách so sánh.'
    elif action == 'remove' and ids:
        products = [product for product in products if product.pk != ids[0]]
        message = 'Đã bỏ sản phẩm khỏi so sánh.'
    elif action == 'add' and ids:
        product = Product.objects.filter(pk=ids[0]).first()
        if product is None:
            error = 'Không tìm thấy sản phẩm.'
        elif any(item.pk == product.pk for item in products):
            message = 'Sản phẩm đã có trong danh sách so sánh.'
        elif any(item.category_id != product.category_id for item in products):
            error = 'Chỉ so sánh sản phẩm cùng danh mục. Xóa danh sách hiện tại để chọn danh mục khác.'
        elif len(products) >= 4:
            error = 'Chỉ được so sánh tối đa 4 sản phẩm.'
        else:
            products.append(product)
            message = f'Đã thêm {product.product_name} vào so sánh.'
    else:
        error = 'Thao tác so sánh không hợp lệ.'
    request.session[SESSION_KEY] = [product.pk for product in products]
    target = request.POST.get('return_to', '')
    if not (target.startswith(('/buyer/', '/?')) or target == '/') or not url_has_allowed_host_and_scheme(
        target, {request.get_host()}, require_https=request.is_secure(),
    ):
        target = reverse('buyer_search')
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'html': render_to_string('includes/compare_tray.html', {
                'comparison_products': products, 'compare_return_to': target,
            }, request=request),
            'selected': [product.pk for product in products],
            'message': error or message, 'error': bool(error),
        }, status=400 if error else 200)
    if error:
        messages.error(request, error)
    else:
        messages.success(request, message)
    return redirect(target)


def buyer_model(request):
    value = request.GET.get('id', '')
    if value.isascii() and value.isdigit() and len(value) <= 18:
        return redirect('buyer_product_detail', product_id=int(value))
    return redirect('buyer_search')


def buyer_shop(request):
    value = request.GET.get('id', '')
    if value.isascii() and value.isdigit() and len(value) <= 18:
        return redirect(reverse('buyer_search') + '?' + urlencode({'shop': value}))
    return redirect('buyer_search')

def _detail_product(product_id):
    return get_object_or_404(
        Product.objects.select_related('category', 'brand', 'shop').prefetch_related('specifications'),
        product_id=product_id,
    )


def _render_product_detail(request, product, question_form=None, status=200, reply_form=None, reply_question=None):
    questions = product.questions.select_related('user').prefetch_related(
        Prefetch('answers', queryset=conversation_messages(), to_attr='thread_messages'),
    ).order_by('-created_at', '-pk')
    page_number = _question_page(reply_question) if reply_question else request.GET.get('questions_page')
    questions_page = Paginator(questions, 10).get_page(page_number)
    for question in questions_page:
        question.reply_form = reply_form if reply_question and question.pk == reply_question.pk else ProductFollowupForm(auto_id=f'id_reply_{question.pk}_%s')
    context = {
        'page_name': 'model',
        'page_section': 'buyer',
        'catalog_source': 'database',
        'selected_product': product,
        'questions_page': questions_page,
        'question_form': question_form if question_form is not None else ProductQuestionForm(),
        'can_ask_question': is_active_buyer(request.user),
        'questions_open': product.status != 'INACTIVE' and product.shop.status == 'ACTIVE',
        'question_login_url': reverse('auth_login') + '?' + urlencode({
            'next': reverse('buyer_product_detail', args=[product.pk]) + '#product-questions',
        }),
        'frequently_bought_together': get_frequently_bought_together(
            product.pk,
            limit=4,
        ),
    }

    return render(request, 'buyer/model.html', context, status=status)


def _question_page(question):
    newer = Q(created_at__gt=question.created_at) | Q(created_at=question.created_at, pk__gt=question.pk)
    return ProductQuestion.objects.filter(newer, product_id=question.product_id).count() // 10 + 1


@require_GET
def product_detail(request, product_id):
    product = _detail_product(product_id)

    if request.user.is_authenticated:
        from interactions.models import ProductView

        ProductView.objects.create(
            user=request.user,
            product=product,
        )

    return _render_product_detail(request, product)


@require_POST
def product_question_create(request, product_id):
    product = _detail_product(product_id)
    if not is_active_buyer(request.user):
        messages.info(request, 'Vui lòng đăng nhập bằng tài khoản người mua để gửi câu hỏi.')
        target = reverse('buyer_product_detail', args=[product.pk]) + '#product-questions'
        return redirect(reverse('auth_login') + '?' + urlencode({'next': target}))
    form = ProductQuestionForm(request.POST)
    if not form.is_valid():
        return _render_product_detail(request, product, question_form=form, status=400)
    if product.status == 'INACTIVE' or product.shop.status != 'ACTIVE':
        form.add_error(None, 'Sản phẩm hoặc gian hàng hiện không nhận câu hỏi mới.')
        return _render_product_detail(request, product, question_form=form, status=400)
    try:
        ProductQuestion.objects.create(product=product, user=request.user, question=form.cleaned_data['question'])
    except DatabaseError:
        form.add_error(None, 'Chưa gửi được câu hỏi. Vui lòng thử lại.')
        return _render_product_detail(request, product, question_form=form, status=503)
    messages.success(request, 'Đã gửi câu hỏi. Shop sẽ trả lời tại phần hỏi đáp sản phẩm.')
    return redirect(reverse('buyer_product_detail', args=[product.pk]) + '#product-questions')


@require_POST
def product_question_followup(request, product_id, question_id):
    product = _detail_product(product_id)
    question = get_object_or_404(ProductQuestion, pk=question_id, product=product)
    target = reverse('buyer_product_detail', args=[product.pk]) + f'?questions_page={_question_page(question)}#product-question-{question.pk}'
    if not is_active_buyer(request.user):
        messages.info(request, 'Vui lòng đăng nhập bằng tài khoản người mua để tham gia trao đổi.')
        return redirect(reverse('auth_login') + '?' + urlencode({'next': target}))
    form = ProductFollowupForm(request.POST, auto_id=f'id_reply_{question.pk}_%s')
    if not form.is_valid():
        return _render_product_detail(request, product, status=400, reply_form=form, reply_question=question)
    try:
        append_question_message(question.pk, request.user, form.cleaned_data['reply'], is_shop_reply=False)
    except ValidationError as error:
        form.add_error(None, error.messages[0])
        return _render_product_detail(request, product, status=400, reply_form=form, reply_question=question)
    except DatabaseError:
        form.add_error(None, 'Chưa gửi được phản hồi. Vui lòng thử lại.')
        return _render_product_detail(request, product, status=503, reply_form=form, reply_question=question)
    messages.success(request, 'Đã gửi nội dung hỏi thêm. Shop sẽ tiếp tục trả lời trong cuộc trao đổi này.')
    return redirect(target)
