
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from functools import partial

from .pages import PAGE_GROUPS, route_name

from products import views as product_views
from carts import views as cart_views
from users import views as user_views
from shops import views as shop_views
from users.views import staff_required
urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('auth/logout/', user_views.auth_logout, name='auth_logout'),
    path('auth/register/', partial(user_views.auth_login, register=True), name='auth_register'),
    path('shop/register/', partial(user_views.legacy_auth, destination='shop_dashboard', mode='register'), name='shop_register'),
    path('shop/forgot/', partial(user_views.legacy_auth, destination='shop_dashboard'), name='shop_forgot'),
    path('staff/login/', partial(user_views.legacy_auth, destination='staff_dashboard'), name='staff_login'),
    path('buyer/cart/add/<int:product_id>/', cart_views.cart_add, name='buyer_cart_add'),
    path('buyer/cart/items/<int:item_id>/update/', cart_views.cart_update, name='buyer_cart_update'),
    path('buyer/cart/items/<int:item_id>/remove/', cart_views.cart_remove, name='buyer_cart_remove'),
    path('buyer/compare/selection/', product_views.buyer_comparison_update, name='buyer_comparison_update'),

    path('', product_views.buyer_home, name='home'),

    path('buyer/products/<int:product_id>/',
         product_views.product_detail,
         name='buyer_product_detail',
    ),

    path('staff/guest/<int:user_id>/toggle/',
         staff_required(user_views.toggle_user_lock),
         name='staff_guest_toggle',
    ),

    path('staff/logout/',
         user_views.auth_logout,
         name='staff_logout',
    ),
]

for section, pages in PAGE_GROUPS.items():
    for page, template in pages.items():

        if section == 'auth':
            view = user_views.auth_login
        elif section == 'buyer' and page == 'home':
            view = product_views.buyer_home
        elif section == 'buyer' and page == 'model':
            view = product_views.buyer_model
        elif section == 'buyer' and page == 'shop':
            view = product_views.buyer_shop
        elif section == 'buyer' and page == 'cart':
            view = cart_views.cart_detail
        elif section == 'buyer' and page == 'search':
            view = product_views.buyer_product_list
        elif section == 'buyer' and page == 'compare':
            view = product_views.buyer_product_compare
        elif section == 'buyer' and page == 'checkout':
            view = cart_views.cart_checkout
        elif section == 'staff' and page == 'products':
            view = staff_required(product_views.load_products)
        elif section == 'staff' and page == 'guest':
            view = staff_required(user_views.guest_list)
        elif section == 'shop' and page == 'login':
            view = shop_views.shop_login
        elif section == 'shop':
            view = shop_views.shop_required(partial(shop_views.shop_page, page=page))
        elif section == 'staff':
            view = staff_required(TemplateView.as_view(
                template_name=template,
                extra_context={'page_name': page, 'page_section': section},
            ))
        else:
            view = TemplateView.as_view(
                template_name=template,
                extra_context={'page_name': page, 'page_section': section},
            )
            if (section == 'buyer' and page in {
                'checkout', 'payment', 'orders', 'order', 'account', 'addresses',
                'builds', 'consultation', 'requests', 'proposals', 'cases', 'notifications', 'chat',
            }):
                view = user_views.buyer_required(view)

        urlpatterns.append(path(
            f'{section}/{page}/',
            view,
            name=route_name(section, page),
        ))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
