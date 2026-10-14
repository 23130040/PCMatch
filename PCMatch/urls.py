
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

from .pages import PAGE_GROUPS, route_name

from products import views as product_views
urlpatterns = [
    path('django-admin/', admin.site.urls),

    path('', TemplateView.as_view(
        template_name='index.html',
        extra_context={'page_name': 'index', 'page_section': 'sitemap',},
    ), name='index'),

    path('buyer/products/<int:product_id>/',
         product_views.product_detail,
         name='buyer_product_detail',
    ),
]

for section, pages in PAGE_GROUPS.items():
    for page, template in pages.items():

        if section == 'buyer' and page == 'search':
            view = product_views.buyer_product_list
        elif section == 'buyer' and page == 'compare':
            view = product_views.buyer_product_compare
        elif section == 'staff' and page == 'products':
            view = product_views.load_products
        else:
            view = TemplateView.as_view(
                template_name=template,
                extra_context={'page_name': page, 'page_section': section},
            )

        urlpatterns.append(path(
            f'{section}/{page}/',
            view,
            name=route_name(section, page),
        ))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
