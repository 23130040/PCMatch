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

    def test_legacy_shop_forgot_redirects_to_shared_auth(self):
        response = self.client.get(reverse('shop_forgot'), follow=True)
        self.assertEqual(response.resolver_match.url_name, 'auth_login')
        self.assertEqual(response.context['next'], reverse('shop_dashboard'))
        self.assertEqual(response.context['mode'], 'login')
        self.assertEqual(self.client.post(reverse('shop_forgot'), {}).status_code, 405)

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
                             reverse('staff_login') + '?next=' + reverse('staff_dashboard'),
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

    def test_buyer_login_rejects_staff_and_seller_accounts(self):
        dashboard = reverse('staff_dashboard')
        response = self.client.post(reverse('auth_login'), {
            'email': self.buyer.email, 'password': self.password, 'next': dashboard,
        })
        self.assertContains(response, 'không có quyền quản trị')
        self.assertNotIn('_auth_user_id', self.client.session)
        # Staff cannot use the buyer portal at all.
        for identifier in [self.staff.username, self.staff.email.upper()]:
            self.client.logout()
            response = self.client.post(reverse('auth_login'), {
                'email': identifier, 'password': self.password, 'next': dashboard,
            })
            self.assertContains(response, 'tài khoản quản trị')
            self.assertNotIn('_auth_user_id', self.client.session)

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


class StaffLoginTests(TestCase):
    password = 'AdminLogin!9271'

    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(
            username='admin-user', email='admin@pcmatch.test', password=cls.password,
            full_name='Quản trị', role='ADMIN', status='ACTIVE',
        )
        cls.buyer = get_user_model().objects.create_user(
            username='plain-buyer', email='buyer@pcmatch.test', password=cls.password,
            full_name='Người mua', status='ACTIVE',
        )

    def test_login_page_renders_required_components(self):
        response = self.client.get(reverse('staff_login'))
        self.assertTemplateUsed(response, 'staff/login.html')
        self.assertEqual(response.context['page_section'], 'staff')
        self.assertContains(response, 'Đăng nhập quản trị')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'Ghi nhớ đăng nhập')
        self.assertContains(response, 'Quên mật khẩu?')
        self.assertNotContains(response, 'Về trang chủ')
        self.assertNotContains(response, 'PC Match')
        self.assertNotContains(response, 'name="captcha"')

    def test_unknown_account_shows_message(self):
        response = self.client.post(reverse('staff_login'), {
            'username': 'no-such-user', 'password': self.password,
        })
        self.assertContains(response, 'Tài khoản không tồn tại.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_wrong_password_shows_message(self):
        response = self.client.post(reverse('staff_login'), {
            'username': self.admin.username, 'password': 'wrong-password',
        })
        self.assertContains(response, 'Sai mật khẩu.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_non_admin_account_is_rejected(self):
        response = self.client.post(reverse('staff_login'), {
            'username': self.buyer.username, 'password': self.password,
        })
        self.assertContains(response, 'Bạn không có quyền truy cập admin.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_successful_login_redirects_to_dashboard(self):
        response = self.client.post(reverse('staff_login'), {
            'username': self.admin.username, 'password': self.password,
            'remember_me': 'on',
        })
        self.assertRedirects(response, reverse('staff_dashboard'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.admin.pk)

    def test_two_factor_login_requires_otp(self):
        self.admin.two_factor_enabled = True
        self.admin.save(update_fields=['two_factor_enabled'])
        response = self.client.post(reverse('staff_login'), {
            'username': self.admin.username, 'password': self.password,
        })
        self.assertContains(response, 'Xác thực hai lớp')
        self.assertNotIn('_auth_user_id', self.client.session)

        response = self.client.post(reverse('staff_login'), {
            'stage': 'otp', 'otp': '000000',
        })
        self.assertContains(response, 'Mã OTP không đúng hoặc đã hết hạn.')

        code = self.client.session['staff_login_otp']['code']
        response = self.client.post(reverse('staff_login'), {'stage': 'otp', 'otp': code})
        self.assertRedirects(response, reverse('staff_dashboard'))

    def test_authenticated_staff_is_sent_to_dashboard(self):
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.get(reverse('staff_login')), reverse('staff_dashboard'))
