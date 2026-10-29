import json
import re
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import resolve, reverse

from shops.models import Shop

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

class FrontendPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user(
            username='stafftest', email='stafftest@pcmatch.vn',
            password='StaffTest123!', full_name='Staff Test',
            role='ADMIN', status='ACTIVE', is_staff=True,
        )
        cls.buyer = get_user_model().objects.create_user(
            username='buyertest@pcmatch.vn', email='buyertest@pcmatch.vn',
            password='BuyerTest123!', full_name='Buyer Test',
            role='BUYER', status='ACTIVE',
        )
        cls.seller = get_user_model().objects.create_user(
            username='sellertest', email='sellertest@pcmatch.vn',
            password='SellerTest123!', full_name='Seller Test',
            role='SELLER', status='ACTIVE', email_verified=True, phone_verified=True,
        )
        cls.shop = Shop.objects.create(
            owner=cls.seller, shop_name='Gian hàng kiểm thử',
            phone='0900000000', address='Địa chỉ kiểm thử', status='ACTIVE',
        )

    def setUp(self):
        self.client.force_login(self.staff)

    def test_staff_pages_require_login(self):
        redirect_url = reverse('staff_login')
        dashboard = reverse('staff_dashboard')
        self.client.logout()
        response = self.client.get(dashboard)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(redirect_url))
        self.client.force_login(self.buyer)
        response = self.client.get(dashboard)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(redirect_url))
        login_url = reverse('auth_login')
        response = self.client.post(login_url, {'email': self.buyer.email, 'password': 'BuyerTest123!', 'next': dashboard})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'không có quyền quản trị')
        self.client.logout()
        response = self.client.post(login_url, {'email': 'stafftest', 'password': 'StaffTest123!', 'next': dashboard})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tài khoản quản trị')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.client.logout()
        response = self.client.post(reverse('staff_login'), {'username': 'stafftest', 'password': 'StaffTest123!'})
        self.assertRedirects(response, dashboard)
        self.client.logout()
        response = self.client.post(login_url, {'email': self.staff.email, 'password': 'sai', 'next': dashboard})
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        response = self.client.get(login_url)
        self.assertEqual(response.status_code, 200)

    def test_staff_logout(self):
        logout_url = reverse('staff_logout')
        self.assertEqual(self.client.post(logout_url).status_code, 302)
        self.assertRedirects(self.client.get(logout_url), reverse('staff_login'))
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_all_pages_render_with_resolvable_links_and_assets(self):
        pages = [('home', 'buyer', 'home')]
        pages += [
            (route_name(section, page), section, page)
            for section, group in PAGE_GROUPS.items()
            for page in group
        ]
        accounts = {'buyer': self.buyer, 'shop': self.seller, 'staff': self.staff}
        for name, section, page in pages:
            with self.subTest(page=name):
                self.client.force_login(accounts.get(section, self.buyer))
                path = reverse(name)
                response = self.client.get(path)
                if name in {'buyer_model', 'buyer_shop'}:
                    self.assertRedirects(response, reverse('buyer_search'))
                    continue
                self.assertEqual(response.status_code, 200)
                parser = PageParser()
                parser.feed(response.content.decode())
                self.assertEqual((parser.section, parser.page), (section, page))
                config = json.loads(parser.config)
                self.assertEqual(config['index'], reverse('home'))
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
        page_templates = set()
        page_templates.update(
            template for pages in PAGE_GROUPS.values() for template in pages.values()
        )
        partials = {
            'admin/header.html', 'admin/sidebar.html', 'includes/frontend_config.html',
            'includes/buyer_base.html',
            'includes/product_card.html',
            'includes/buyer_icon.html', 'includes/buyer_header.html', 'includes/buyer_account_links.html',
            'includes/admin_interface_controls.html',
            'includes/admin_product_drawers.html',
            'includes/admin_support_drawers.html',
            'includes/compare_button.html', 'includes/compare_tray.html',
            'shop/register.html', 'shop/verify_email.html', 'shop/verify_phone.html',
            'shop/onboarding_profile.html', 'shop/onboarding_legal.html',
            'shop/onboarding_pending.html', 'shop/notifications.html',
            'staff/login.html', 'staff/forgot_password.html', 'staff/reset_password.html',
        }
        root = settings.BASE_DIR / 'templates'
        partials.update(path.relative_to(root).as_posix() for path in (root / 'includes/shop').glob('*.html'))
        existing = {path.relative_to(root).as_posix() for path in root.rglob('*.html')}
        self.assertEqual(existing - partials, page_templates)

    def test_django_admin_and_unknown_pages(self):
        self.assertEqual(reverse('admin:index'), '/django-admin/')
        self.assertEqual(self.client.get('/buyer/not-a-page/').status_code, 404)

    def test_frontend_does_not_use_prototype_storage_or_transaction_handlers(self):
        scripts = settings.BASE_DIR / 'static' / 'js'
        for name in ['buyer.js', 'store.js', 'account.js', 'commerce.js', 'sitemap.js', 'profile.js', 'shop.js', 'shop-store.js', 'shop-data.js']:
            self.assertFalse((scripts / name).exists(), name)
        self.assertFalse((settings.BASE_DIR / 'templates' / 'index.html').exists())
        for path in scripts.glob('*.js'):
            content = path.read_text(encoding='utf-8')
            self.assertNotIn('document.body.innerHTML', content, path.name)
            for forbidden in ['localStorage', 'sessionStorage']:
                self.assertNotIn(forbidden, content, path.name)
            # Comparison enhances only its own backend POST forms.
            if path.name != 'comparison.js':
                for forbidden in ["addEventListener('submit'", 'addEventListener("submit"']:
                    self.assertNotIn(forbidden, content, path.name)
        for path in (settings.BASE_DIR / 'templates' / 'buyer').glob('*.html'):
            self.assertNotIn('<template data-page=', path.read_text(encoding='utf-8'), path.name)

    def test_only_backend_template_groups_remain(self):
        self.assertEqual(set(PAGE_GROUPS), {'buyer', 'shop', 'staff', 'auth'})
        self.assertEqual(self.client.get('/states/index/').status_code, 404)
        self.assertFalse((settings.BASE_DIR / 'templates/states').exists())

    def test_shop_content_is_in_the_server_response(self):
        self.client.force_login(self.seller)
        for page in PAGE_GROUPS['shop']:
            with self.subTest(page=page):
                response = self.client.get(reverse(route_name('shop', page)))
                content = response.content.decode()
                self.assertEqual(content.count('<head>'), 1)
                self.assertEqual(content.count('</head>'), 1)
                self.assertEqual(content.count('<title>'), 1)
                self.assertContains(response, '<h1>', count=1)
                self.assertContains(response, 'id="shop-main"', count=1)
                self.assertContains(response, 'js/shop-interface.js', count=1)
                for removed in ['shop-templates-', 'data-shop-template', '[[', 'Đang tải giao diện', 'js/shop.js']:
                    self.assertNotContains(response, removed)

    def test_shop_markup_is_in_html_templates(self):
        root = settings.BASE_DIR
        for path in list((root / 'templates/includes/shop').glob('*.html')) + list((root / 'templates/shop').glob('*.html')):
            content = path.read_text(encoding='utf-8')
            self.assertNotIn('data-shop-template', content, path.name)
            self.assertNotIn('shop_templates', content, path.name)
            self.assertNotIn('onclick=', content, path.name)
            self.assertNotIn('onsubmit=', content, path.name)
        for path in (root / 'static/js').glob('shop*.js'):
            content = path.read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'</?[A-Za-z][A-Za-z0-9:-]*[\s/>]', content), path.name)
            for forbidden in ['renderTemplate', 'innerHTML', 'insertAdjacentHTML', 'localStorage', 'sessionStorage']:
                self.assertNotIn(forbidden, content, path.name)
        self.assertFalse((root / 'static/js/routing.js').exists())
        self.assertFalse((root / 'static/js/shop-merchandising-data.js').exists())

    def test_private_layouts_use_django_authentication(self):
        self.client.logout()
        for name in ['buyer_account', 'buyer_orders', 'buyer_checkout']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith(reverse('auth_login') + '?next='))
        for name in ['shop_dashboard', 'shop_offers']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith(reverse('shop_login') + '?next='))
        response = self.client.post(reverse('shop_login'), {
            'username': self.buyer.email, 'password': 'BuyerTest123!',
        })
        self.assertContains(response, 'khu vực người bán')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.client.logout()
        response = self.client.post(reverse('shop_login'), {
            'username': self.seller.username, 'password': 'SellerTest123!',
        })
        self.assertRedirects(response, reverse('shop_dashboard'), fetch_redirect_response=False)

    def test_search_query_is_preserved_on_slash_redirect(self):
        response = self.client.get('/buyer/search?q=CPU&sort=price')
        self.assertRedirects(
            response, '/buyer/search/?q=CPU&sort=price',
            status_code=301, fetch_redirect_response=False,
        )
