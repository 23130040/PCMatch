"""
URL configuration for PCMatch project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

from .pages import PAGE_GROUPS, route_name

urlpatterns = [
    path('django-admin/', admin.site.urls),

    path('', TemplateView.as_view(
        template_name='index.html',
        extra_context={'page_name': 'index', 'page_section': 'sitemap'},
    ), name='index'),
]

for section, pages in PAGE_GROUPS.items():
    for page, template in pages.items():
        urlpatterns.append(path(
            f'{section}/{page}/',
            TemplateView.as_view(
                template_name=template,
                extra_context={'page_name': page, 'page_section': section},
            ),
            name=route_name(section, page),
        ))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
