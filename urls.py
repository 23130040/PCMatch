from django.contrib import admin
from django.urls import path
from users import views as user_views
from products import views as product_views  

urlpatterns = [
    path('django-admin/', admin.site.urls),

  
    path('staff/guest/', user_views.ListView, name='load_web'),
    path('staff/guest/<int:user_id>/toggle/', user_views.lockUser, name='lockUser'),

    
    path('staff/products/', product_views.load_products, name='load_products'),  
    path('staff/products/<int:product_id>/toggle/', product_views.showORhide_Product, name='showORhide_Product'),


    path('staff/order/', order_views.order_list, name='admin_order_list'),
    path('staff/order/<int:order_id>/update/', order_views.update_order_status, name='update_order_status'),
]
]