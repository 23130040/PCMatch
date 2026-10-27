from functools import partial

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

from analytics import views as analytics_views
from carts import views as cart_views
from orders import views as order_views
from payments import views as payment_views
from products import views as product_views
from shops import views as shop_views
from users import views as user_views
from users.views import staff_required

from .pages import PAGE_GROUPS, route_name

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('auth/logout/', user_views.auth_logout, name='auth_logout'),
    path('auth/register/', partial(user_views.auth_login, register=True), name='auth_register'),
    path('shop/register/', shop_views.shop_register, name='shop_register'),
    path('shop/verify/email/', shop_views.shop_verify_email, name='shop_verify_email'),
    path('shop/verify/email/<str:token>/', shop_views.shop_verify_email_confirm, name='shop_verify_email_confirm'),
    path('shop/verify/phone/', shop_views.shop_verify_phone, name='shop_verify_phone'),
    path('shop/onboarding/profile/', shop_views.shop_onboarding_profile, name='shop_onboarding_profile'),
    path('shop/onboarding/legal/', shop_views.shop_onboarding_legal, name='shop_onboarding_legal'),
    path('shop/onboarding/pending/', shop_views.shop_onboarding_pending, name='shop_onboarding_pending'),
    path('shop/notifications/', shop_views.shop_notifications, name='shop_notifications'),
    path('shop/forgot/', partial(user_views.legacy_auth, destination='shop_dashboard'), name='shop_forgot'),
    path('staff/login/', user_views.staff_login, name='staff_login'),
    path('staff/forgot/', user_views.staff_forgot_password, name='staff_forgot'),
    path('staff/reset/<str:token>/', user_views.staff_reset_password, name='staff_reset_password'),
    path('buyer/cart/add/<int:product_id>/', cart_views.cart_add, name='buyer_cart_add'),
    path('buyer/cart/items/<int:item_id>/update/', cart_views.cart_update, name='buyer_cart_update'),
    path('buyer/cart/items/<int:item_id>/remove/', cart_views.cart_remove, name='buyer_cart_remove'),
    path('buyer/compare/selection/', product_views.buyer_comparison_update, name='buyer_comparison_update'),

    path('staff/orders/', staff_required(order_views.orderList), name='loadOrder'),
    path('staff/orders/many/', staff_required(order_views.changeManyStatus), name='updateOrderStatus'),
    path('staff/order/<int:orderid>/update/', order_views.changeStatus, name='updateStatus'),
    path('staff/products/', staff_required(product_views.load_products), name='load_products'),
    path('staff/products/<int:product_id>/toggle/', product_views.showORhide_Product, name='showORhide_Product'),
    path('staff/order/<int:order_id>/update/', order_views.changeStatus, name='update_order_status'),
    path('staff/guest/<int:user_id>/toggle/', staff_required(user_views.toggle_user_lock), name='staff_guest_toggle'),

    path('', product_views.buyer_home, name='home'),
    path('buyer/products/<int:product_id>/', product_views.product_detail, name='buyer_product_detail'),
    path('buyer/products/<int:product_id>/questions/', product_views.product_question_create, name='buyer_product_question_create'),
    path('buyer/products/<int:product_id>/questions/<int:question_id>/reply/', product_views.product_question_followup, name='buyer_product_question_followup'),
    path('staff/logout/', user_views.auth_logout, name='staff_logout'),
    path('staff/shop/<int:shop_id>/approve/',
         staff_required(shop_views.staff_shop_approve),
         name='staff_shop_approve',
    ),
    path('staff/shop/<int:shop_id>/suspend/',
         staff_required(shop_views.staff_shop_suspend),
         name='staff_shop_suspend',
    ),

    path('staff/logout/',
         user_views.staff_logout,
         name='staff_logout',
    ),
    path('shop/logout/',
         user_views.shop_logout,
         name='shop_logout',
    ),

    path('shop/product/save/',
         shop_views.shop_required(shop_views.shop_product_save),
         name='shop_product_save',
    ),
    path('shop/product/<int:product_id>/toggle/',
         shop_views.shop_required(shop_views.shop_product_toggle),
         name='shop_product_toggle',
    ),
    path('shop/product/<int:product_id>/delete/',
         shop_views.shop_required(shop_views.shop_product_delete),
         name='shop_product_delete',
    ),
    path('shop/inventory/update/',
         shop_views.shop_required(shop_views.shop_inventory_update),
         name='shop_inventory_update',
    ),
    path('shop/order/<int:order_id>/status/',
         shop_views.shop_required(shop_views.shop_order_update_status),
         name='shop_order_update_status',
    ),
    path('shop/question/<int:question_id>/answer/',
         shop_views.shop_required(shop_views.shop_question_answer),
         name='shop_question_answer',
    ),
    path('shop/return/<int:return_id>/update/',
         shop_views.shop_required(shop_views.shop_return_update),
         name='shop_return_update',
    ),
    path('buyer/orders/create/', order_views.place_order, name='buyer_place_order',),
    path('buyer/addresses/<int:address_id>/default/', user_views.buyer_address_default, name='buyer_address_default'),
    path('payments/vnpay/ipn/', payment_views.vnpay_ipn, name='vnpay_ipn'),
    path('payments/vnpay/return/', payment_views.vnpay_return, name='vnpay_return'),
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
        elif section == 'buyer' and page == 'orders':
            view = order_views.buyer_orders
        elif section == 'buyer' and page == 'addresses':
            view = user_views.buyer_addresses
        elif section == 'buyer' and page in {'order', 'payment'}:
            view = order_views.buyer_order
            
        
        elif section == 'staff' and page == 'dashboard':
            view = staff_required(analytics_views.dashboard_view)
        elif section == 'staff' and (page == 'order' or page == 'orders'):
            staff_required(order_views.orderList)
        elif section == 'staff' and page == 'products':
            view = staff_required(product_views.load_products)
        elif section == 'staff' and page == 'guest':
            view = staff_required(user_views.guest_list)      

        elif section == 'staff' and page == 'shop':
            view = staff_required(shop_views.staff_shop_list)
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
