from django.templatetags.static import static
from django.urls import reverse
from django.middleware.csrf import get_token
from carts.models import CartItem
from products.models import Category
from products.comparison import session_products
from shops.models import Shop
from users.views import is_staff_user
from decimal import Decimal

from .pages import PAGE_GROUPS, route_name

def frontend(request):
    selected_products = session_products(request)
    cart_count = 0
    session_user = None
    cart_items = []
    cart_subtotal = Decimal('0')
    if request.user.is_authenticated:
        cart_items = list(CartItem.objects.filter(cart__user=request.user).select_related('product__shop').order_by('added_at', 'pk'))
        cart_count = sum(item.quantity for item in cart_items)
        for item in cart_items:
            item.line_total = item.quantity * item.product.price
            cart_subtotal += item.line_total
        session_user = {'id': request.user.pk, 'name': request.user.full_name or request.user.username}
    # Only staff sessions pay for the shop counters shown in the admin sidebar.
    staff_shops = {'total': 0, 'pending': 0}
    if is_staff_user(request.user):
        staff_shops = {
            'total': Shop.objects.count(),
            'pending': Shop.objects.filter(status='PENDING').count(),
        }
    return {
        'comparison_products': selected_products,
        'comparison_ids': [product.pk for product in selected_products],
        'compare_return_to': request.get_full_path(),
        'database_cart_count': cart_count,
        'database_cart_items': cart_items[:6],
        'database_cart_subtotal': cart_subtotal,
        'navigation_categories': Category.objects.filter(status=True).order_by('category_name'),
        'staff_shops': staff_shops,
        'frontend_config': {
            'cartCount': cart_count,
            'sessionUser': session_user,
            'csrfToken': get_token(request),
            'logoutUrl': reverse('auth_logout'),
            'index': reverse('home'),
            'staticUrl': static(''),
            'urls': {
                section: {
                    page: reverse(route_name(section, page))
                    for page in pages
                }
                for section, pages in PAGE_GROUPS.items()
            },
        },
    }
