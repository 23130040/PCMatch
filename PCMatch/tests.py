import json
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase
from django.urls import resolve, reverse

from .pages import PAGE_GROUPS, route_name


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.assets = []
        self.components = {'sidebar': 0, 'topbar': 0, 'service-bar': 0}
        self.page = None
        self.section = None
        self.config = ''
        self.in_config = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'html':
            self.page = attrs.get('data-page')
            self.section = attrs.get('data-section')
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag == 'form' and attrs.get('action'):
            self.links.append(attrs['action'])
        if tag in ('script', 'img') and attrs.get('src'):
            self.assets.append(attrs['src'])
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.assets.append(attrs['href'])
        for name in attrs.get('class', '').split():
            if name in self.components:
                self.components[name] += 1
        if tag == 'script' and attrs.get('id') == 'pcmatch-config':
            self.in_config = True

    def handle_data(self, data):
        if self.in_config:
            self.config += data

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_config = False


class FrontendPagesTests(SimpleTestCase):
    def test_all_pages_render_with_resolvable_links_and_assets(self):
        pages = [('index', 'sitemap', 'index')]
        pages += [
            (route_name(section, page), section, page)
            for section, group in PAGE_GROUPS.items()
            for page in group
        ]
        for name, section, page in pages:
            with self.subTest(page=name):
                path = reverse(name)
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                parser = PageParser()
                parser.feed(response.content.decode())
                self.assertEqual((parser.section, parser.page), (section, page))
                config = json.loads(parser.config)
                self.assertEqual(config['index'], reverse('index'))
                for group, urls in config['urls'].items():
                    for key, url in urls.items():
                        self.assertEqual(resolve(url).url_name, route_name(group, key))
                for link in parser.links:
                    url = urlsplit(link)
                    if url.scheme or url.netloc or link.startswith('#'):
                        continue
                    self.assertTrue(url.path.startswith('/'), link)
                    resolve(unquote(url.path))
                for asset in parser.assets:
                    url = urlsplit(asset)
                    if url.scheme or url.netloc:
                        continue
                    self.assertTrue(url.path.startswith(settings.STATIC_URL), asset)
                    asset_path = unquote(url.path[len(settings.STATIC_URL):])
                    self.assertIsNotNone(finders.find(asset_path), asset)
                if section == 'staff':
                    self.assertEqual(parser.components, {
                        'sidebar': 1, 'topbar': 1, 'service-bar': 1,
                    })
                    self.assertNotIn('data-sidebar-host', response.content.decode())
                    self.assertNotIn('initSharedComponent', response.content.decode())

    def test_registry_covers_every_existing_page(self):
        page_templates = {'index.html'}
        page_templates.update(
            template for pages in PAGE_GROUPS.values() for template in pages.values()
        )
        partials = {
            'admin/header.html', 'admin/sidebar.html', 'includes/frontend_config.html',
        }
        root = settings.BASE_DIR / 'templates'
        existing = {path.relative_to(root).as_posix() for path in root.rglob('*.html')}
        self.assertEqual(existing - partials, page_templates)

    def test_django_admin_and_unknown_pages(self):
        self.assertEqual(reverse('admin:index'), '/django-admin/')
        self.assertEqual(self.client.get('/buyer/not-a-page/').status_code, 404)

    def test_search_query_is_preserved_on_slash_redirect(self):
        response = self.client.get('/buyer/search?q=CPU&sort=price')
        self.assertRedirects(
            response, '/buyer/search/?q=CPU&sort=price',
            status_code=301, fetch_redirect_response=False,
        )
