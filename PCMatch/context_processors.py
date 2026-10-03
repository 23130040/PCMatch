from django.templatetags.static import static
from django.urls import reverse

from .pages import PAGE_GROUPS, route_name

def frontend(request):
    return {
        'frontend_config': {
            'index': reverse('index'),
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
