import re
from datetime import timedelta
from io import BytesIO
from smtplib import SMTPException
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .facebook_oauth import get_facebook_identity
from .models import BuyerEmailOTP, PasswordResetToken, SocialAccount


@override_settings(
    BUYER_OTP_EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST='smtp.example.test',
    EMAIL_HOST_USER='otp@pcmatch.test',
    EMAIL_HOST_PASSWORD='test-password',
    DEFAULT_FROM_EMAIL='otp@pcmatch.test',
)
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

    def test_shop_forgot_password_uses_seller_recovery_form(self):
        response = self.client.get(reverse('shop_forgot'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/forgot_password.html')
        self.assertContains(response, 'name="email"')
        self.assertEqual(self.client.post(reverse('shop_forgot'), {'email': 'invalid'}).status_code, 200)

    def test_registration_cannot_grant_staff_access(self):
        response = self.client.post(reverse('auth_login'), {
            'mode': 'register', 'full_name': 'Tài khoản mới', 'email': 'newshared@example.test',
            'password1': self.password, 'password2': self.password,
            'next': reverse('staff_dashboard'), 'role': 'ADMIN', 'is_staff': '1',
        })
        self.assertRedirects(response, reverse('auth_verify_email'))
        account = get_user_model().objects.get(email='newshared@example.test')
        self.assertEqual(account.role, 'BUYER')
        self.assertEqual(account.status, 'INACTIVE')
        self.assertFalse(account.email_verified)
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

    def test_registration_sends_otp_and_verification_returns_to_login(self):
        response = self.client.post(reverse('auth_login'), {
            'mode': 'register', 'full_name': 'Tài khoản mới', 'email': 'newbuyer@example.test',
            'password1': self.password, 'password2': self.password,
        })
        self.assertRedirects(response, reverse('auth_verify_email'))
        self.assertEqual(len(mail.outbox), 1)
        code = re.search(r'\b([0-9]{6})\b', mail.outbox[0].body).group(1)
        account = get_user_model().objects.get(email='newbuyer@example.test')
        otp = account.buyer_email_otp
        self.assertTrue(check_password(code, otp.code_hash))
        self.assertFalse(account.email_verified)
        self.assertEqual(account.status, 'INACTIVE')
        self.assertNotIn('_auth_user_id', self.client.session)

        response = self.client.post(reverse('auth_verify_email'), {'code': code})
        login_url = reverse('auth_login') + '?next=' + reverse('buyer_cart')
        self.assertRedirects(response, login_url, fetch_redirect_response=False)
        account.refresh_from_db()
        self.assertTrue(account.email_verified)
        self.assertEqual(account.status, 'ACTIVE')
        self.assertFalse(BuyerEmailOTP.objects.filter(user=account).exists())
        response = self.client.get(login_url)
        self.assertContains(response, 'Xác thực email thành công.')

    def test_five_wrong_codes_require_email_again_and_can_request_new_code(self):
        self.client.post(reverse('auth_login'), {
            'mode': 'register', 'full_name': 'Tài khoản OTP', 'email': 'otpbuyer@example.test',
            'password1': self.password, 'password2': self.password,
        })
        account = get_user_model().objects.get(email='otpbuyer@example.test')
        actual_code = re.search(r'\b([0-9]{6})\b', mail.outbox[0].body).group(1)
        wrong_code = '000001' if actual_code == '000000' else '000000'
        for attempt in range(4):
            response = self.client.post(reverse('auth_verify_email'), {'code': wrong_code})
            self.assertEqual(response.status_code, 200, msg=f'failed attempt {attempt + 1}')
        response = self.client.post(reverse('auth_verify_email'), {'code': wrong_code})
        self.assertRedirects(response, reverse('auth_verify_email'))
        self.assertNotIn('buyer_otp_user_id', self.client.session)
        self.assertFalse(BuyerEmailOTP.objects.filter(user=account).exists())
        response = self.client.get(reverse('auth_verify_email'))
        self.assertContains(response, 'name="email"')
        response = self.client.post(reverse('auth_verify_email'), {
            'action': 'request', 'email': account.email,
        })
        self.assertRedirects(response, reverse('auth_verify_email'))
        self.assertTrue(BuyerEmailOTP.objects.filter(user=account).exists())
        self.assertEqual(len(mail.outbox), 2)

    def test_resending_rotates_code_and_expiry_is_three_minutes(self):
        with patch('users.otp_services.get_random_string', side_effect=['123456', '654321']):
            self.client.post(reverse('auth_login'), {
                'mode': 'register', 'full_name': 'Tài khoản OTP', 'email': 'resend@example.test',
                'password1': self.password, 'password2': self.password,
            })
            response = self.client.post(reverse('auth_verify_email'), {'action': 'resend'})
        account = get_user_model().objects.get(email='resend@example.test')
        first_code = re.search(r'\b([0-9]{6})\b', mail.outbox[0].body).group(1)
        otp = account.buyer_email_otp
        self.assertAlmostEqual(
            (otp.expires_at - timezone.now()).total_seconds(),
            180,
            delta=5,
        )
        self.assertRedirects(response, reverse('auth_verify_email'))
        second_code = re.search(r'\b([0-9]{6})\b', mail.outbox[1].body).group(1)
        otp.refresh_from_db()
        self.assertFalse(check_password(first_code, otp.code_hash))
        self.assertTrue(check_password(second_code, otp.code_hash))
        self.assertEqual(otp.failed_attempts, 0)

        otp.expires_at = timezone.now() - timedelta(seconds=1)
        otp.save(update_fields=['expires_at'])
        response = self.client.post(reverse('auth_verify_email'), {'code': second_code})
        self.assertContains(response, 'Mã OTP đã hết hạn.')

    def test_unverified_new_buyer_cannot_log_in(self):
        self.client.post(reverse('auth_login'), {
            'mode': 'register', 'full_name': 'Tài khoản chờ', 'email': 'pending@example.test',
            'password1': self.password, 'password2': self.password,
        })
        self.client.post(reverse('auth_verify_email'), {'action': 'resend'})
        self.client.logout()
        response = self.client.post(reverse('auth_login'), {
            'email': 'pending@example.test', 'password': self.password,
        })
        self.assertContains(response, 'Email chưa được xác thực.')
        self.assertNotIn('_auth_user_id', self.client.session)

    @override_settings(
        EMAIL_HOST='',
        EMAIL_HOST_USER='',
        EMAIL_HOST_PASSWORD='',
        DEFAULT_FROM_EMAIL='',
    )
    def test_missing_smtp_configuration_is_reported_without_console_otp(self):
        response = self.client.post(reverse('auth_login'), {
            'mode': 'register', 'full_name': 'Chưa cấu hình', 'email': 'nosmtp@example.test',
            'password1': self.password, 'password2': self.password,
        })
        self.assertRedirects(response, reverse('auth_verify_email'), fetch_redirect_response=False)
        response = self.client.get(reverse('auth_verify_email'))
        self.assertContains(response, 'Email chưa được cấu hình.')
        self.assertFalse(mail.outbox)
        self.assertFalse(BuyerEmailOTP.objects.exists())

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
        for name in ['auth_login', 'auth_register', 'auth_verify_email', 'auth_logout']:
            self.assertEqual(strict.post(reverse(name), {}).status_code, 403)


@override_settings(
    FACEBOOK_APP_ID='test-facebook-app-id',
    FACEBOOK_APP_SECRET='test-facebook-app-secret',
    FACEBOOK_GRAPH_VERSION='v22.0',
    FACEBOOK_REDIRECT_URI='https://testserver/auth/facebook/callback/',
)
class FacebookLoginTests(TestCase):
    def setUp(self):
        self.buyer = get_user_model().objects.create_user(
            username='facebook-existing-buyer',
            email='facebook-buyer@example.test',
            password='FacebookBuyer!82734',
            full_name='Buyer Account',
            role='BUYER',
            status='ACTIVE',
            email_verified=True,
        )

    def start_login(self, **query):
        response = self.client.get(reverse('auth_facebook_login'), query)
        self.assertEqual(response.status_code, 302)
        parsed_url = urlparse(response.url)
        self.assertEqual(parsed_url.netloc, 'www.facebook.com')
        return parse_qs(parsed_url.query)

    def callback(self, state, **query):
        return self.client.get(
            reverse('auth_facebook_callback'),
            {'state': state, **query},
        )

    def test_login_button_starts_server_configured_oauth_without_exposing_secret(self):
        response = self.client.get(reverse('auth_login'))
        self.assertContains(response, f'href="{reverse("auth_facebook_login")}?next=')
        self.assertNotContains(response, 'data-backend-pending="facebook"')
        self.assertNotContains(response, 'test-facebook-app-secret')

        parameters = self.start_login(next=reverse('buyer_orders'))
        self.assertEqual(parameters['client_id'], ['test-facebook-app-id'])
        self.assertEqual(parameters['scope'], ['email,public_profile'])
        self.assertEqual(parameters['response_type'], ['code'])
        self.assertEqual(parameters['redirect_uri'], [
            'https://testserver/auth/facebook/callback/',
        ])
        self.assertTrue(parameters['state'][0])
        self.assertNotIn('test-facebook-app-secret', repr(parameters))

    @patch('users.views.get_facebook_identity')
    def test_facebook_email_links_to_existing_buyer_and_logs_in(self, get_identity):
        get_identity.return_value = {
            'id': 'facebook-user-1001',
            'name': 'Facebook Buyer',
            'email': self.buyer.email,
        }
        parameters = self.start_login(next=reverse('buyer_orders'))

        response = self.callback(parameters['state'][0], code='authorization-code')

        self.assertRedirects(response, reverse('buyer_orders'), fetch_redirect_response=False)
        get_identity.assert_called_once_with(
            code='authorization-code',
            redirect_uri='https://testserver/auth/facebook/callback/',
        )
        social_account = SocialAccount.objects.get(
            provider='FACEBOOK',
            provider_user_id='facebook-user-1001',
        )
        self.assertEqual(social_account.user, self.buyer)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.buyer.pk)

    @patch('users.views.get_facebook_identity')
    def test_existing_facebook_identity_is_loaded_from_database_on_next_sign_in(self, get_identity):
        get_identity.side_effect = [
            {
                'id': 'facebook-user-persisted',
                'name': 'Facebook Buyer',
                'email': self.buyer.email,
            },
            {
                'id': 'facebook-user-persisted',
                'name': 'Facebook Buyer',
                'email': 'changed-facebook-email@example.test',
            },
        ]
        first_state = self.start_login()['state'][0]
        self.callback(first_state, code='first-code')
        self.client.logout()

        second_state = self.start_login()['state'][0]
        response = self.callback(second_state, code='second-code')

        self.assertRedirects(response, reverse('buyer_cart'), fetch_redirect_response=False)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(SocialAccount.objects.count(), 1)
        self.assertEqual(
            SocialAccount.objects.get(provider_user_id='facebook-user-persisted').user,
            self.buyer,
        )
        self.assertEqual(int(self.client.session['_auth_user_id']), self.buyer.pk)

    @patch('users.views.get_facebook_identity')
    def test_new_facebook_email_creates_buyer_and_persists_provider_identity(self, get_identity):
        get_identity.return_value = {
            'id': 'facebook-user-1002',
            'name': 'New Facebook Buyer',
            'email': 'new-facebook-buyer@example.test',
        }
        parameters = self.start_login()

        response = self.callback(parameters['state'][0], code='authorization-code')

        self.assertRedirects(response, reverse('buyer_cart'), fetch_redirect_response=False)
        account = get_user_model().objects.get(email='new-facebook-buyer@example.test')
        self.assertEqual(account.role, 'BUYER')
        self.assertEqual(account.status, 'ACTIVE')
        self.assertTrue(account.email_verified)
        self.assertFalse(account.has_usable_password())
        self.assertEqual(
            SocialAccount.objects.get(
                provider='FACEBOOK',
                provider_user_id='facebook-user-1002',
            ).user,
            account,
        )
        self.assertEqual(int(self.client.session['_auth_user_id']), account.pk)

    @patch('users.views.get_facebook_identity')
    def test_existing_non_buyer_email_is_not_logged_in_or_linked(self, get_identity):
        seller = get_user_model().objects.create_user(
            username='facebook-seller',
            email='facebook-seller@example.test',
            password='FacebookSeller!82734',
            full_name='Seller',
            role='SELLER',
            status='ACTIVE',
            email_verified=True,
        )
        get_identity.return_value = {
            'id': 'facebook-seller-1003',
            'name': 'Seller',
            'email': seller.email,
        }
        parameters = self.start_login()

        response = self.callback(parameters['state'][0], code='authorization-code')

        self.assertRedirects(
            response,
            reverse('auth_login') + '?next=' + reverse('buyer_cart'),
            fetch_redirect_response=False,
        )
        self.assertFalse(SocialAccount.objects.exists())
        self.assertNotIn('_auth_user_id', self.client.session)

    @patch('users.views.get_facebook_identity')
    def test_email_permission_denial_does_not_create_an_account(self, get_identity):
        get_identity.return_value = {
            'id': 'facebook-user-no-email',
            'name': 'No Email',
        }
        parameters = self.start_login()

        response = self.callback(parameters['state'][0], code='authorization-code')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertFalse(SocialAccount.objects.exists())
        self.assertNotIn('_auth_user_id', self.client.session)

    @patch('users.views.get_facebook_identity')
    def test_ambiguous_case_insensitive_email_does_not_link_an_arbitrary_buyer(self, get_identity):
        get_user_model().objects.create_user(
            username='facebook-buyer-case-duplicate',
            email='FACEBOOK-BUYER@example.test',
            password='FacebookBuyer!82734',
            full_name='Duplicate Buyer',
            role='BUYER',
            status='ACTIVE',
            email_verified=True,
        )
        get_identity.return_value = {
            'id': 'facebook-user-ambiguous-email',
            'name': 'Facebook Buyer',
            'email': self.buyer.email,
        }
        parameters = self.start_login()

        response = self.callback(parameters['state'][0], code='authorization-code')

        self.assertEqual(response.status_code, 302)
        self.assertFalse(SocialAccount.objects.exists())
        self.assertNotIn('_auth_user_id', self.client.session)

    @patch('users.views.get_facebook_identity')
    def test_cancel_or_permission_denial_returns_to_login_without_provider_exchange(self, get_identity):
        parameters = self.start_login()
        response = self.callback(parameters['state'][0], error='access_denied')

        self.assertRedirects(
            response,
            reverse('auth_login') + '?next=' + reverse('buyer_cart'),
            fetch_redirect_response=False,
        )
        get_identity.assert_not_called()
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertNotIn('_auth_user_id', self.client.session)

    @patch('users.views.get_facebook_identity')
    def test_invalid_or_replayed_state_is_rejected(self, get_identity):
        parameters = self.start_login()
        bad_response = self.callback('attacker-controlled-state', code='authorization-code')
        self.assertEqual(bad_response.status_code, 302)
        get_identity.assert_not_called()

        replay_response = self.callback(parameters['state'][0], code='authorization-code')
        self.assertEqual(replay_response.status_code, 302)
        get_identity.assert_not_called()
        self.assertNotIn('_auth_user_id', self.client.session)

    @patch('users.views.get_facebook_identity')
    def test_expired_oauth_state_is_rejected(self, get_identity):
        parameters = self.start_login()
        session = self.client.session
        pending = session['facebook_oauth_state']
        pending['created_at'] -= 601
        session['facebook_oauth_state'] = pending
        session.save()

        response = self.callback(parameters['state'][0], code='authorization-code')

        self.assertEqual(response.status_code, 302)
        get_identity.assert_not_called()
        self.assertNotIn('_auth_user_id', self.client.session)

    @override_settings(FACEBOOK_APP_ID='', FACEBOOK_APP_SECRET='')
    def test_missing_server_credentials_show_configuration_error(self):
        response = self.client.get(reverse('auth_facebook_login'))
        self.assertRedirects(
            response,
            reverse('auth_login') + '?next=' + reverse('buyer_cart'),
            fetch_redirect_response=False,
        )

    @override_settings(FACEBOOK_REDIRECT_URI='')
    def test_insecure_callback_is_rejected_before_redirecting_to_facebook(self):
        response = self.client.get(reverse('auth_facebook_login'))

        self.assertRedirects(
            response,
            reverse('auth_login') + '?next=' + reverse('buyer_cart'),
            fetch_redirect_response=False,
        )
        self.assertNotIn('facebook_oauth_state', self.client.session)

    @patch(
        'users.facebook_oauth.urlopen',
        side_effect=[
            BytesIO(b'{"access_token":"temporary-access-token"}'),
            BytesIO(b'{"id":"facebook-user-2001","name":"OAuth User","email":"oauth@example.test"}'),
        ],
    )
    def test_backend_exchanges_code_and_fetches_identity_with_bearer_token(self, urlopen_mock):
        identity = get_facebook_identity(
            code='authorization-code',
            redirect_uri='https://testserver/auth/facebook/callback/',
        )

        self.assertEqual(identity['id'], 'facebook-user-2001')
        self.assertEqual(urlopen_mock.call_count, 2)
        token_request = urlopen_mock.call_args_list[0].args[0]
        profile_request = urlopen_mock.call_args_list[1].args[0]
        self.assertIn('test-facebook-app-secret', token_request.full_url)
        self.assertEqual(profile_request.get_header('Authorization'), 'Bearer temporary-access-token')
        self.assertNotIn('temporary-access-token', profile_request.full_url)
        self.assertEqual(urlopen_mock.call_args_list[0].kwargs['timeout'], 10)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class BuyerPasswordRecoveryTests(TestCase):
    old_password = 'BuyerOld!82734'
    new_password = 'BuyerNew!82734'

    def setUp(self):
        self.buyer = get_user_model().objects.create_user(
            username='recovery-buyer',
            email='recovery@example.test',
            password=self.old_password,
            full_name='Người mua',
            role='BUYER',
            status='ACTIVE',
        )

    def test_login_links_to_enabled_buyer_password_recovery(self):
        response = self.client.get(reverse('auth_login'))
        self.assertContains(response, f'href="{reverse("buyer_forgot_password")}"')
        self.assertNotContains(response, 'data-backend-pending="password-recovery"')

    def test_forgot_password_validates_email_and_does_not_disclose_unknown_users(self):
        invalid = self.client.post(reverse('buyer_forgot_password'), {'email': 'not-an-email'})
        self.assertTrue(invalid.context['form'].errors['email'])
        self.assertFalse(PasswordResetToken.objects.exists())

        unknown = self.client.post(reverse('buyer_forgot_password'), {'email': 'missing@example.test'})
        self.assertContains(unknown, 'Nếu email thuộc một tài khoản người mua')
        self.assertFalse(PasswordResetToken.objects.exists())
        self.assertFalse(mail.outbox)

    def test_forgot_password_sends_link_to_the_uniquely_matching_buyer(self):
        response = self.client.post(reverse('buyer_forgot_password'), {'email': self.buyer.email.upper()})
        self.assertContains(response, 'Nếu email thuộc một tài khoản người mua')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.buyer.email])

        token = PasswordResetToken.objects.get(user=self.buyer)
        self.assertFalse(token.used)
        self.assertGreater(token.expires_at, timezone.now())
        self.assertIn(reverse('buyer_reset_password', args=[token.token]), mail.outbox[0].body)

        self.client.post(reverse('buyer_forgot_password'), {'email': self.buyer.email})
        token.refresh_from_db()
        self.assertTrue(token.used)
        self.assertEqual(PasswordResetToken.objects.filter(user=self.buyer, used=False).count(), 1)
        self.assertEqual(len(mail.outbox), 2)

    def test_case_insensitive_duplicate_address_is_not_assigned_to_an_arbitrary_account(self):
        get_user_model().objects.create_user(
            username='recovery-buyer-duplicate',
            email='RECOVERY@example.test',
            password=self.old_password,
            full_name='Người mua khác',
            role='BUYER',
        )
        response = self.client.post(reverse('buyer_forgot_password'), {'email': self.buyer.email})
        self.assertContains(response, 'Nếu email thuộc một tài khoản người mua')
        self.assertFalse(PasswordResetToken.objects.exists())
        self.assertFalse(mail.outbox)

    def test_non_buyer_account_cannot_receive_a_buyer_reset_link(self):
        get_user_model().objects.create_user(
            username='recovery-seller',
            email='seller-recovery@example.test',
            password=self.old_password,
            full_name='Người bán',
            role='SELLER',
        )
        response = self.client.post(reverse('buyer_forgot_password'), {
            'email': 'seller-recovery@example.test',
        })
        self.assertContains(response, 'Nếu email thuộc một tài khoản người mua')
        self.assertFalse(PasswordResetToken.objects.exists())
        self.assertFalse(mail.outbox)

    @patch('users.views.send_mail', side_effect=SMTPException('mail server unavailable'))
    def test_email_delivery_failure_is_reported_without_leaving_a_valid_token(self, send_mail_mock):
        response = self.client.post(reverse('buyer_forgot_password'), {'email': self.buyer.email})
        self.assertContains(response, 'Không gửi được email khôi phục.')
        self.assertFalse(PasswordResetToken.objects.filter(user=self.buyer, used=False).exists())
        send_mail_mock.assert_called_once()

    def test_password_reset_validates_confirmation_hashes_password_invalidates_tokens_and_session(self):
        older_token = PasswordResetToken.objects.create(
            user=self.buyer,
            token='older-reset-token',
            expires_at=timezone.now() + timedelta(hours=1),
        )
        token = PasswordResetToken.objects.create(
            user=self.buyer,
            token='active-reset-token',
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.client.force_login(self.buyer)

        mismatch = self.client.post(reverse('buyer_reset_password', args=[token.token]), {
            'password1': self.new_password,
            'password2': 'Different!82734',
        })
        self.assertContains(mismatch, 'Mật khẩu nhập lại không khớp.')
        self.buyer.refresh_from_db()
        self.assertTrue(self.buyer.check_password(self.old_password))
        token.refresh_from_db()
        self.assertFalse(token.used)

        response = self.client.post(reverse('buyer_reset_password', args=[token.token]), {
            'password1': self.new_password,
            'password2': self.new_password,
        })
        self.assertRedirects(response, reverse('auth_login'), fetch_redirect_response=False)
        self.buyer.refresh_from_db()
        self.assertFalse(self.buyer.check_password(self.old_password))
        self.assertTrue(self.buyer.check_password(self.new_password))
        self.assertNotEqual(self.buyer.password, self.new_password)
        self.assertEqual(
            PasswordResetToken.objects.filter(
                pk__in=[older_token.pk, token.pk], used=True,
            ).count(),
            2,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.buyer.email])
        self.assertIn('đã được thay đổi', mail.outbox[0].subject)

        self.client.get(reverse('buyer_cart'))
        self.assertNotIn('_auth_user_id', self.client.session)

        reused = self.client.get(reverse('buyer_reset_password', args=[token.token]))
        self.assertRedirects(reused, reverse('auth_login'), fetch_redirect_response=False)


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
