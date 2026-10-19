from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class SharedAuthenticationTests(TestCase):
    password = 'SharedAuth!82734'

    @classmethod
    def setUpTestData(cls):
        cls.buyer = get_user_model().objects.create_user(
            username='shared-buyer', email='sharedbuyer@example.test',
            password=cls.password, full_name='Người mua', status='ACTIVE',
        )
        cls.staff = get_user_model().objects.create_user(
            username='shared-staff', email='sharedstaff@example.test',
            password=cls.password, full_name='Quản trị', role='ADMIN', status='ACTIVE',
        )

    def test_registration_shares_login_template_and_preserves_destination(self):
        destination = reverse('buyer_checkout')
        for name, query in [('auth_register', {'next': destination}),
                            ('auth_login', {'mode': 'register', 'next': destination})]:
            response = self.client.get(reverse(name), query, follow=True)
            self.assertEqual(response.resolver_match.url_name, 'auth_login')
            self.assertTemplateUsed(response, 'auth/login.html')
            self.assertEqual(response.context['mode'], 'register')
            self.assertContains(response, f'action="{reverse("auth_login")}"')
            self.assertContains(response, 'name="mode" value="register"')
            self.assertContains(response, 'name="password2"')
            self.assertEqual(response.context['page_section'], 'auth')
            self.assertEqual(response.context['next'], destination)
        response = self.client.get(reverse('auth_login'), {'next': destination})
        self.assertContains(response, f'href="{reverse("auth_login")}?mode=register&amp;next={destination}"')
        self.assertNotContains(response, 'name="password2"')

    def test_legacy_urls_only_redirect_to_shared_auth(self):
        for old, destination in [
            ('shop_forgot', 'shop_dashboard'),
            ('staff_login', 'staff_dashboard'),
        ]:
            with self.subTest(route=old):
                response = self.client.get(reverse(old), follow=True)
                self.assertEqual(response.resolver_match.url_name, 'auth_login')
                self.assertEqual(response.context['next'], reverse(destination))
                self.assertEqual(response.context['mode'], 'login')
                self.assertEqual(self.client.post(reverse(old), {}).status_code, 405)

    def test_registration_cannot_grant_staff_access(self):
        response = self.client.post(reverse('auth_login'), {
            'mode': 'register', 'full_name': 'Tài khoản mới', 'email': 'newshared@example.test',
            'password1': self.password, 'password2': self.password,
            'next': reverse('staff_dashboard'), 'role': 'ADMIN', 'is_staff': '1',
        })
        self.assertRedirects(response, reverse('buyer_cart'))
        account = get_user_model().objects.get(email='newshared@example.test')
        self.assertEqual(account.role, 'BUYER')
        self.assertFalse(account.is_staff)
        self.assertFalse(account.is_superuser)
        self.assertTrue(account.check_password(self.password))
        self.assertRedirects(self.client.get(reverse('staff_dashboard')),
                             reverse('auth_login') + '?next=' + reverse('staff_dashboard'),
                             fetch_redirect_response=False)

    def test_registration_errors_are_visible_in_existing_layout(self):
        response = self.client.post(reverse('auth_login'), {
            'mode': 'register', 'full_name': 'Trùng email', 'email': self.buyer.email.upper(),
            'password1': self.password, 'password2': 'DifferentPass!1234',
        })
        self.assertTemplateUsed(response, 'auth/login.html')
        self.assertContains(response, 'Email đã được đăng ký.')
        self.assertContains(response, 'Mật khẩu nhập lại không khớp.')
        self.assertEqual(get_user_model().objects.count(), 2)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_shared_login_checks_staff_permission_and_accepts_username_or_email(self):
        dashboard = reverse('staff_dashboard')
        response = self.client.post(reverse('auth_login'), {
            'email': self.buyer.email, 'password': self.password, 'next': dashboard,
        })
        self.assertContains(response, 'không có quyền quản trị')
        self.assertNotIn('_auth_user_id', self.client.session)
        for identifier in [self.staff.username, self.staff.email.upper()]:
            self.client.logout()
            response = self.client.post(reverse('auth_login'), {
                'email': identifier, 'password': self.password, 'next': dashboard,
            })
            self.assertRedirects(response, dashboard)

    def test_shared_login_rejects_external_and_auth_loop_destinations(self):
        for destination in ['https://example.com/', '//example.com/shop/',
                            '/shop/login/', '/shop/login', '/shop/register/?mode=register', '/staff/login/']:
            self.client.logout()
            response = self.client.post(reverse('auth_login'), {
                'email': self.buyer.email, 'password': self.password, 'next': destination,
            })
            self.assertRedirects(response, reverse('buyer_cart'))

    def test_common_auth_forms_require_csrf(self):
        strict = Client(enforce_csrf_checks=True)
        for name in ['auth_login', 'auth_register', 'auth_logout']:
            self.assertEqual(strict.post(reverse(name), {}).status_code, 403)
