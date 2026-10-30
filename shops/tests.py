from decimal import Decimal
from datetime import timedelta
import re
from smtplib import SMTPException
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification
from orders.models import Order, OrderItem, Return
from products.models import Brand, Category, Product, ProductQuestion
from users.models import Address, EmailVerificationSend, EmailVerificationToken, PasswordResetToken
from .models import Shop


class ShopBackendLayoutsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username='shop-owner', email='owner@example.test', password='ShopOwner!789', full_name='Chủ gian hàng', role='SELLER', status='ACTIVE', email_verified=True)
        cls.other = User.objects.create_user(username='other-owner', email='other@example.test', password='OtherOwner!789', full_name='Chủ khác', role='SELLER', status='ACTIVE')
        cls.buyer = User.objects.create_user(username='shop-buyer', email='shopbuyer@example.test', password='ShopBuyer!789', full_name='Khách hàng', role='BUYER', status='ACTIVE')
        cls.seller_without_shop = User.objects.create_user(username='seller-no-shop', email='noshop@example.test', password='NoShop!7891', full_name='Người bán mới', role='SELLER', status='ACTIVE')
        cls.shop = Shop.objects.create(owner=cls.owner, shop_name='Gian hàng thật', phone='0901234567', address='Địa chỉ kho', status='ACTIVE')
        cls.other_shop = Shop.objects.create(owner=cls.other, shop_name='Gian hàng khác', phone='0901234568', address='Kho khác', status='ACTIVE')
        cls.category = Category.objects.create(category_name='CPU')
        cls.brand = Brand.objects.create(brand_name='Thương hiệu kiểm thử')
        cls.product = Product.objects.create(shop=cls.shop, category=cls.category, brand=cls.brand, product_name='CPU của gian hàng', slug='own-cpu', price=100000, stock_quantity=5, sold_quantity=1)
        cls.foreign_product = Product.objects.create(shop=cls.other_shop, category=cls.category, product_name='Sản phẩm riêng của gian hàng khác', slug='other-cpu', price=800000, stock_quantity=2)
        cls.address = Address.objects.create(user=cls.buyer, receiver_name='Khách hàng', receiver_phone='0901234569', province='TP.HCM', district='Quận 1', ward='Bến Nghé', detail_address='123 Lê Lợi')
        cls.order = Order.objects.create(user=cls.buyer, address=cls.address, order_code='ORDER-MIXED', subtotal=900000, total_amount=900000, payment_method='COD', payment_status='PAID', order_status='DELIVERED')
        OrderItem.objects.create(order=cls.order, product=cls.product, shop=cls.shop, quantity=1, unit_price=100000, subtotal=100000, item_status='DELIVERED')
        OrderItem.objects.create(order=cls.order, product=cls.foreign_product, shop=cls.other_shop, quantity=1, unit_price=800000, subtotal=800000, item_status='DELIVERED')
        cls.foreign_order = Order.objects.create(user=cls.buyer, address=cls.address, order_code='ORDER-OTHER-ONLY', subtotal=800000, total_amount=800000, payment_method='COD', order_status='PENDING')
        OrderItem.objects.create(order=cls.foreign_order, product=cls.foreign_product, shop=cls.other_shop, quantity=1, unit_price=800000, subtotal=800000, item_status='PENDING')
        cls.question = ProductQuestion.objects.create(product=cls.product, user=cls.buyer, question='Câu hỏi của gian hàng')
        cls.foreign_question = ProductQuestion.objects.create(product=cls.foreign_product, user=cls.buyer, question='Câu hỏi riêng của shop khác')
        cls.foreign_case = Return.objects.create(order=cls.foreign_order, user=cls.buyer, reason='Hồ sơ của shop khác')

    def setUp(self):
        self.client.force_login(self.owner)

    def test_products_and_questions_are_rendered_from_owned_shop(self):
        response = self.client.get(reverse('shop_offers'))
        self.assertContains(response, self.product.product_name)
        self.assertNotContains(response, self.foreign_product.product_name)
        self.assertNotContains(response, 'shop-templates-')
        response = self.client.get(reverse('shop_questions'))
        self.assertContains(response, self.question.question)
        self.assertNotContains(response, self.foreign_question.question)

    def test_order_details_and_revenue_exclude_other_shops_items(self):
        response = self.client.get(reverse('shop_order'), {'id': self.order.pk})
        self.assertContains(response, self.product.product_name)
        self.assertNotContains(response, self.foreign_product.product_name)
        self.assertEqual(response.context['order'].shop_total, Decimal('100000'))
        response = self.client.get(reverse('shop_revenue'))
        self.assertEqual(response.context['revenue']['total'], Decimal('100000'))
        self.assertEqual(response.context['revenue']['count'], 1)
        self.assertNotContains(response, self.foreign_order.order_code)

    def test_query_string_cannot_open_another_shops_records(self):
        cases = [('shop_offers', {'edit': self.foreign_product.pk}), ('shop_order', {'id': self.foreign_order.pk}), ('shop_aftersales', {'id': self.foreign_case.pk})]
        for name, query in cases:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name), query).status_code, 404)
        for name, key in [('shop_order', 'id'), ('shop_aftersales', 'id'), ('shop_offers', 'edit')]:
            for identifier in ['invalid', '-1', '9' * 100]:
                self.assertEqual(self.client.get(reverse(name), {key: identifier}).status_code, 404)

    def test_native_filters_and_edit_form_use_database_values(self):
        response = self.client.get(reverse('shop_offers'), {'q': 'CPU của', 'cat': self.category.pk, 'status': 'active'})
        self.assertContains(response, self.product.product_name)
        response = self.client.get(reverse('shop_offers'), {'q': self.foreign_product.product_name})
        self.assertEqual(response.context['products_page'].paginator.count, 0)
        response = self.client.get(reverse('shop_offers'), {'edit': self.product.pk})
        self.assertContains(response, 'name="product_name" value="CPU của gian hàng"')
        self.assertContains(response, '<fieldset disabled')
        for category in ['invalid', '9' * 100, '²']:
            response = self.client.get(reverse('shop_offers'), {'cat': category})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['products_page'].paginator.count, 0)

    def test_product_pagination_keeps_filters_and_shop_scope(self):
        Product.objects.bulk_create([
            Product(shop=self.shop, category=self.category, product_name=f'CPU phân trang {index}', slug=f'own-paged-{index}', price=100000, stock_quantity=1)
            for index in range(11)
        ])
        response = self.client.get(reverse('shop_offers'), {'q': 'CPU', 'cat': self.category.pk, 'page': '2'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['products_page'].paginator.count, 12)
        self.assertEqual(len(response.context['products_page']), 2)
        self.assertContains(response, 'Trang trước')
        self.assertNotContains(response, self.foreign_product.product_name)

    def test_account_without_shop_is_sent_to_onboarding(self):
        self.client.force_login(self.seller_without_shop)
        for name in ['shop_dashboard', 'shop_offers', 'shop_orders', 'shop_questions', 'shop_revenue', 'shop_inventory']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse('shop_onboarding_profile'))

    def test_shop_sign_in_page_uses_existing_django_authentication(self):
        self.client.logout()
        response = self.client.get(reverse('shop_login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shop/login.html')
        self.assertContains(response, f'action="{reverse("shop_login")}"')
        self.assertContains(response, f'name="next" value="{reverse("shop_dashboard")}"')
        self.assertContains(response, 'Đăng ký làm người bán')
        self.assertContains(response, 'Quên mật khẩu?')
        response = self.client.post(reverse('shop_login'), {'username': self.owner.email, 'password': 'ShopOwner!789'})
        self.assertRedirects(response, reverse('shop_dashboard'))
        self.assertEqual(self.client.get(reverse('shop_dashboard')).status_code, 200)
        self.client.logout()
        response = self.client.post(reverse('shop_login'), {'username': self.owner.username, 'password': 'sai'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'không đúng')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_seller_logout_returns_to_the_shop_login(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('shop_logout'))
        self.assertRedirects(response, reverse('shop_login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_unimplemented_actions_cannot_simulate_a_success(self):
        response = self.client.post(reverse('shop_offers'), {'product_name': 'Fake', 'price': '1'})
        self.assertEqual(response.status_code, 405)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal('100000'))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SellerPasswordRecoveryTests(TestCase):
    old_password = 'SellerOld!82734'
    new_password = 'SellerNew!82734'

    def setUp(self):
        self.seller = get_user_model().objects.create_user(
            username='recovery-seller',
            email='recovery-seller@example.test',
            password=self.old_password,
            full_name='Người bán',
            role='SELLER',
            status='ACTIVE',
        )

    def test_shop_login_forgot_link_opens_seller_recovery_form(self):
        response = self.client.get(reverse('shop_login'))
        self.assertContains(response, f'href="{reverse("shop_forgot")}"')
        response = self.client.get(reverse('shop_forgot'))
        self.assertTemplateUsed(response, 'shop/forgot_password.html')
        self.assertContains(response, 'name="email"')

    def test_forgot_password_validates_email_and_does_not_disclose_unknown_accounts(self):
        invalid = self.client.post(reverse('shop_forgot'), {'email': 'not-an-email'})
        self.assertTrue(invalid.context['form'].errors['email'])
        self.assertFalse(PasswordResetToken.objects.exists())

        unknown = self.client.post(reverse('shop_forgot'), {'email': 'missing@example.test'})
        self.assertContains(unknown, 'Nếu email thuộc một tài khoản seller')
        self.assertFalse(PasswordResetToken.objects.exists())
        self.assertFalse(mail.outbox)

    def test_forgot_password_sends_link_to_the_uniquely_matching_seller(self):
        response = self.client.post(reverse('shop_forgot'), {'email': self.seller.email.upper()})
        self.assertContains(response, 'Nếu email thuộc một tài khoản seller')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.seller.email])

        token = PasswordResetToken.objects.get(user=self.seller)
        self.assertFalse(token.used)
        self.assertGreater(token.expires_at, timezone.now())
        self.assertIn(reverse('shop_reset_password', args=[token.token]), mail.outbox[0].body)

        self.client.post(reverse('shop_forgot'), {'email': self.seller.email})
        token.refresh_from_db()
        self.assertTrue(token.used)
        self.assertEqual(PasswordResetToken.objects.filter(user=self.seller, used=False).count(), 1)

    def test_duplicate_case_insensitive_email_or_non_seller_cannot_be_recovered(self):
        User = get_user_model()
        User.objects.create_user(
            username='recovery-seller-duplicate',
            email='RECOVERY-SELLER@example.test',
            password=self.old_password,
            full_name='Người bán khác',
            role='SELLER',
        )
        User.objects.create_user(
            username='recovery-buyer',
            email='buyer-recovery@example.test',
            password=self.old_password,
            full_name='Người mua',
            role='BUYER',
        )
        for email in [self.seller.email, 'buyer-recovery@example.test']:
            with self.subTest(email=email):
                response = self.client.post(reverse('shop_forgot'), {'email': email})
                self.assertContains(response, 'Nếu email thuộc một tài khoản seller')
        self.assertFalse(PasswordResetToken.objects.exists())
        self.assertFalse(mail.outbox)

    @patch('shops.email_services.send_mail', side_effect=SMTPException('mail server unavailable'))
    def test_email_failure_is_visible_and_rolls_back_recovery_token(self, send_mail_mock):
        response = self.client.post(reverse('shop_forgot'), {'email': self.seller.email})
        self.assertContains(response, 'Chưa gửi được email.')
        self.assertFalse(PasswordResetToken.objects.filter(user=self.seller, used=False).exists())
        send_mail_mock.assert_called_once()

    def test_reset_validates_confirmation_hashes_password_invalidates_tokens_and_expires_session(self):
        old_token = PasswordResetToken.objects.create(
            user=self.seller,
            token='older-seller-reset-token',
            expires_at=timezone.now() + timedelta(hours=1),
        )
        token = PasswordResetToken.objects.create(
            user=self.seller,
            token='active-seller-reset-token',
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.client.force_login(self.seller)

        mismatch = self.client.post(reverse('shop_reset_password', args=[token.token]), {
            'password1': self.new_password,
            'password2': 'Different!82734',
        })
        self.assertContains(mismatch, 'Mật khẩu nhập lại không khớp.')
        self.seller.refresh_from_db()
        self.assertTrue(self.seller.check_password(self.old_password))
        token.refresh_from_db()
        self.assertFalse(token.used)

        response = self.client.post(reverse('shop_reset_password', args=[token.token]), {
            'password1': self.new_password,
            'password2': self.new_password,
        })
        self.assertRedirects(response, reverse('shop_login'), fetch_redirect_response=False)
        self.seller.refresh_from_db()
        self.assertFalse(self.seller.check_password(self.old_password))
        self.assertTrue(self.seller.check_password(self.new_password))
        self.assertNotEqual(self.seller.password, self.new_password)
        self.assertEqual(
            PasswordResetToken.objects.filter(
                pk__in=[old_token.pk, token.pk], used=True,
            ).count(),
            2,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.seller.email])
        self.assertIn('đã được thay đổi', mail.outbox[0].subject)

        self.client.get(reverse('shop_dashboard'))
        self.assertNotIn('_auth_user_id', self.client.session)

        reused = self.client.get(reverse('shop_reset_password', args=[token.token]))
        self.assertRedirects(reused, reverse('shop_login'), fetch_redirect_response=False)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class StaffShopApprovalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(
            username='shop-admin', email='shopadmin@example.test',
            password='ShopAdmin!321', full_name='Quản trị', role='ADMIN',
            status='ACTIVE', is_staff=True,
        )
        cls.buyer = User.objects.create_user(
            username='shop-outsider', email='outsider@example.test',
            password='Outsider!321', full_name='Người ngoài', role='BUYER', status='ACTIVE',
        )
        cls.seller = User.objects.create_user(
            username='new-seller', email='newseller@example.test',
            password='NewSeller!321', full_name='Chủ shop mới', role='SELLER',
            status='ACTIVE', email_verified=True, phone_verified=True,
        )
        cls.shop = Shop.objects.create(
            owner=cls.seller, shop_name='Shop chờ duyệt',
            phone='0900000011', address='Địa chỉ chờ duyệt', status='PENDING',
        )

    def test_staff_list_shows_real_shops_and_filters(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('staff_shop'))
        self.assertTemplateUsed(response, 'admin/shop.html')
        self.assertContains(response, 'Shop chờ duyệt')
        self.assertContains(response, 'newseller@example.test')
        self.assertEqual(response.context['shop_counts']['PENDING'], 1)
        self.assertEqual(response.context['shop_counts']['ACTIVE'], 0)

        response = self.client.get(reverse('staff_shop'), {'status': 'ACTIVE'})
        self.assertNotContains(response, 'Shop chờ duyệt')

        response = self.client.get(reverse('staff_shop'), {'search': 'chờ duyệt'})
        self.assertContains(response, 'Shop chờ duyệt')

    def test_buyer_cannot_open_staff_shop_management(self):
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('staff_shop'))
        self.assertRedirects(response, reverse('staff_login') + '?next=' + reverse('staff_shop'))

    def test_approval_lets_the_seller_reach_the_shop_dashboard(self):
        self.submit_legal_documents()
        self.client.force_login(self.admin)
        response = self.client.post(reverse('staff_shop_approve', args=[self.shop.pk]))
        self.assertRedirects(response, reverse('staff_shop'))

        self.shop.refresh_from_db()
        self.assertEqual(self.shop.status, 'ACTIVE')
        self.assertTrue(Notification.objects.filter(
            user=self.seller, type='SHOP_APPROVED').exists())

        # The pending screen is replaced by the real shop dashboard.
        self.client.force_login(self.seller)
        self.assertRedirects(self.client.get(reverse('shop_onboarding_pending')),
                             reverse('shop_dashboard'))
        self.assertEqual(self.client.get(reverse('shop_dashboard')).status_code, 200)

    def test_approving_twice_does_not_send_two_notifications(self):
        self.submit_legal_documents()
        self.client.force_login(self.admin)
        self.client.post(reverse('staff_shop_approve', args=[self.shop.pk]))
        self.client.post(reverse('staff_shop_approve', args=[self.shop.pk]))
        self.assertEqual(
            Notification.objects.filter(user=self.seller, type='SHOP_APPROVED').count(), 1)

    def submit_legal_documents(self):
        self.shop.id_card = SimpleUploadedFile('id.pdf', b'%PDF-1.4\nidentity')
        self.shop.business_license = SimpleUploadedFile('license.pdf', b'%PDF-1.4\nlicense')
        self.shop.legal_submitted_at = timezone.now()
        self.shop.save()

    def test_shop_approval_requires_verified_email_and_complete_documents(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('staff_shop_approve', args=[self.shop.pk]))
        self.assertRedirects(response, reverse('staff_shop'))
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.status, 'PENDING')

        self.submit_legal_documents()
        self.seller.phone_verified = False
        self.seller.save(update_fields=['phone_verified'])
        response = self.client.get(reverse('staff_shop'))
        self.assertContains(response, f'action="{reverse("staff_shop_approve", args=[self.shop.pk])}"')
        self.assertNotContains(response, 'disabled title="Cần xác thực email và nộp đủ hồ sơ pháp lý"')
        self.client.post(reverse('staff_shop_approve', args=[self.shop.pk]))
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.status, 'ACTIVE')

    def test_staff_document_download_is_protected_and_attachment_only(self):
        self.submit_legal_documents()
        url = reverse('staff_shop_document', args=[self.shop.pk, 'id-card'])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('staff_login') + '?next=' + url)

        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Disposition'].startswith('attachment;'))
        public_url = f'/media/{self.shop.id_card.name}'
        self.assertEqual(self.client.get(public_url).status_code, 404)

    def test_approval_requires_post(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse('staff_shop_approve', args=[self.shop.pk])).status_code,
            405,
        )

    def test_django_admin_action_cannot_bypass_shop_verification(self):
        self.admin.is_superuser = True
        self.admin.save(update_fields=['is_superuser'])
        self.client.force_login(self.admin)
        response = self.client.post(reverse('admin:shops_shop_changelist'), {
            'action': 'approve_shops',
            '_selected_action': [self.shop.pk],
            'index': '0',
        })
        self.assertEqual(response.status_code, 302)
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.status, 'PENDING')

    def test_suspend_closes_the_dashboard_until_approved_again(self):
        self.shop.status = 'ACTIVE'
        self.shop.save()
        self.client.force_login(self.admin)
        response = self.client.post(reverse('staff_shop_suspend', args=[self.shop.pk]))
        self.assertRedirects(response, reverse('staff_shop'))

        self.shop.refresh_from_db()
        self.assertEqual(self.shop.status, 'SUSPENDED')
        self.assertTrue(Notification.objects.filter(
            user=self.seller, type='SHOP_SUSPENDED').exists())

        self.client.force_login(self.seller)
        self.assertRedirects(self.client.get(reverse('shop_dashboard')),
                             reverse('shop_onboarding_pending'))

    def test_shop_actions_require_staff_and_post(self):
        self.client.logout()
        url = reverse('staff_shop_approve', args=[self.shop.pk])
        self.assertRedirects(self.client.post(url), reverse('staff_login') + '?next=' + url)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 405)


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    SHOP_PUBLIC_BASE_URL='http://127.0.0.1:8000',
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    BUYER_OTP_EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class SellerOnboardingFlowTests(TestCase):
    password = 'StrongSeller!123'

    def register(self, **overrides):
        payload = {
            'username': 'newseller',
            'email': 'newseller@example.test',
            'password1': self.password,
            'password2': self.password,
        }
        payload.update(overrides)
        return self.client.post(reverse('shop_register'), payload)

    def test_full_seller_onboarding_then_approval(self):
        # Account details stay in the session until the final legal submission.
        response = self.register()
        self.assertRedirects(response, reverse('shop_verify_email'), fetch_redirect_response=False)
        self.assertFalse(get_user_model().objects.filter(username='newseller').exists())
        response = self.client.get(reverse('shop_verify_phone'))
        self.assertRedirects(response, reverse('shop_verify_email'), fetch_redirect_response=False)

        # Step 2: send a real email verification link and continue after confirmation.
        response = self.client.get(reverse('shop_verify_email'))
        self.assertContains(response, 'Gửi liên kết xác thực')
        response = self.client.post(reverse('shop_verify_email'), {'email': 'newseller@example.test'})
        self.assertRedirects(response, reverse('shop_verify_email'), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        email_link = re.search(r'http://127\.0\.0\.1:8000[^\s]+', mail.outbox[0].body).group(0)
        self.assertIn('newseller@example.test', mail.outbox[0].to)
        response = self.client.get(email_link.replace('http://127.0.0.1:8000', ''))
        self.assertRedirects(response, reverse('shop_onboarding_profile'), fetch_redirect_response=False)
        self.assertFalse(get_user_model().objects.filter(username='newseller').exists())

        # Step 3: shop profile.
        response = self.client.post(reverse('shop_onboarding_profile'), {
            'shop_name': 'Shop mới', 'address': 'Hà Nội', 'phone': '0901234567', 'description': 'Mô tả ngắn',
        })
        self.assertRedirects(response, reverse('shop_onboarding_legal'), fetch_redirect_response=False)
        self.assertFalse(get_user_model().objects.filter(username='newseller').exists())
        self.assertFalse(Shop.objects.filter(shop_name='Shop mới').exists())

        # Invalid legal data must not create either database record.
        response = self.client.post(reverse('shop_onboarding_legal'), {})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username='newseller').exists())
        self.assertFalse(Shop.objects.filter(shop_name='Shop mới').exists())

        # Valid final submission creates an email-verified account and the shop.
        response = self.client.post(reverse('shop_onboarding_legal'), {
            'id_card': SimpleUploadedFile('cccd.pdf', b'%PDF-1.4\ncccd-bytes'),
            'business_license': SimpleUploadedFile('gpkd.pdf', b'%PDF-1.4\ngpkd-bytes'),
        })
        self.assertRedirects(response, reverse('shop_onboarding_pending'), fetch_redirect_response=False)
        seller = get_user_model().objects.get(username='newseller')
        shop = Shop.objects.get(owner=seller)
        self.assertEqual(seller.role, 'SELLER')
        self.assertEqual(seller.status, 'ACTIVE')
        self.assertFalse(seller.phone_verified)
        self.assertTrue(seller.email_verified)
        shop.refresh_from_db()
        self.assertIsNotNone(shop.legal_submitted_at)
        self.assertEqual(len(mail.outbox), 1)

        # Dashboard is blocked while the shop is not approved.
        self.assertRedirects(self.client.get(reverse('shop_dashboard')),
                             reverse('shop_onboarding_pending'), fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse('shop_onboarding_pending')), 'đang chờ xét duyệt')

        # Admin approval creates the notification and unlocks the dashboard.
        shop.status = 'ACTIVE'
        shop.save()
        self.assertTrue(Notification.objects.filter(user=seller, type='SHOP_APPROVED').exists())
        self.assertEqual(self.client.get(reverse('shop_dashboard')).status_code, 200)
        self.assertContains(self.client.get(reverse('shop_notifications')), 'shop của bạn đã sẵn sàng')

    def test_registration_validates_unique_username_and_email(self):
        get_user_model().objects.create_user(
            username='dup', email='dup@example.test', password=self.password, full_name='Dup',
        )
        response = self.register(username='dup')
        self.assertContains(response, 'Tên đăng nhập đã được sử dụng.')
        response = self.register(email='dup@example.test')
        self.assertContains(response, 'Email đã được đăng ký.')

    def test_unverified_seller_cannot_sign_in_and_can_resend_email(self):
        seller = get_user_model().objects.create_user(
            username='awaiting-email', email='awaiting@example.test',
            password=self.password, full_name='Awaiting email', role='SELLER',
            status='ACTIVE',
        )
        response = self.client.post(reverse('shop_login'), {
            'username': seller.username,
            'password': self.password,
        })
        self.assertContains(response, 'Email chưa được xác thực.')
        self.assertNotIn('_auth_user_id', self.client.session)

        EmailVerificationSend.objects.filter(email=seller.email).update(
            created_at=timezone.now() - timedelta(minutes=2),
        )
        response = self.client.post(reverse('shop_verify_email'), {'email': seller.email})
        self.assertRedirects(response, reverse('shop_verify_email'))
        self.assertEqual(len(mail.outbox), 1)
        tokens = list(EmailVerificationToken.objects.filter(user=seller).order_by('pk'))
        self.assertEqual(len(tokens), 1)
        self.assertIsNone(tokens[0].invalidated_at)

    def test_incomplete_registration_does_not_create_seller_in_database(self):
        self.register(username='incomplete', email='incomplete@example.test')
        self.assertFalse(get_user_model().objects.filter(username='incomplete').exists())
        response = self.client.post(reverse('shop_verify_email'), {'email': 'incomplete@example.test'})
        self.assertRedirects(response, reverse('shop_verify_email'))
        self.assertFalse(get_user_model().objects.filter(email='incomplete@example.test').exists())

    def test_email_resend_is_available(self):
        seller = get_user_model().objects.create_user(
            username='rate-limited', email='rate@example.test',
            password=self.password, full_name='Rate limited', role='SELLER',
            status='INACTIVE',
        )
        response = self.client.post(reverse('shop_verify_email'), {'email': seller.email})
        response = self.client.get(reverse('shop_verify_email'))
        self.assertContains(response, 'Gửi liên kết xác thực')
        self.assertEqual(len(mail.outbox), 1)

        EmailVerificationSend.objects.filter(email=seller.email).update(
            created_at=timezone.now() - timedelta(minutes=2),
        )
        for attempt in range(4):
            self.client.post(reverse('shop_verify_email'), {'email': seller.email})
            EmailVerificationSend.objects.filter(email=seller.email).update(
                created_at=timezone.now() - timedelta(minutes=2),
            )
        self.client.post(reverse('shop_verify_email'), {'email': seller.email})
        response = self.client.get(reverse('shop_verify_email'))
        self.assertContains(response, 'Gửi liên kết xác thực')
        self.assertEqual(len(mail.outbox), 6)

    def test_expired_and_invalid_activation_links_return_to_resend_form(self):
        seller = get_user_model().objects.create_user(
            username='expired-link', email='expired@example.test',
            password=self.password, full_name='Expired link', role='SELLER',
            status='INACTIVE',
        )
        self.client.post(reverse('shop_verify_email'), {'email': seller.email})
        token = EmailVerificationToken.objects.get(user=seller)
        token.expires_at = timezone.now() - timedelta(seconds=1)
        token.save(update_fields=['expires_at'])
        response = self.client.get(reverse('shop_verify_email_confirm', args=[token.token]))
        self.assertRedirects(response, reverse('shop_verify_email'), fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse('shop_verify_email')), 'đã hết hạn')
        response = self.client.get(reverse('shop_verify_email_confirm', args=['invalid-token']))
        self.assertRedirects(response, reverse('shop_verify_email'), fetch_redirect_response=False)

    def test_legal_documents_reject_mismatched_file_content(self):
        from .forms import ShopLegalForm

        form = ShopLegalForm(
            data={},
            files={
                'id_card': SimpleUploadedFile('identity.jpg', b'not-an-image'),
                'business_license': SimpleUploadedFile('license.pdf', b'%PDF-1.4\nvalid'),
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn('Nội dung tệp không khớp', str(form.errors['id_card']))

    def test_shop_name_must_be_unique(self):
        other = get_user_model().objects.create_user(
            username='owner1', email='owner1@example.test', password=self.password, full_name='Owner 1',
        )
        Shop.objects.create(owner=other, shop_name='Tên đã dùng', phone='0900000000', address='X')
        seller = get_user_model().objects.create_user(
            username='owner2', email='owner2@example.test', password=self.password, full_name='Owner 2',
            role='SELLER', email_verified=True, phone_verified=True,
        )
        self.client.force_login(seller)
        response = self.client.post(reverse('shop_onboarding_profile'), {
            'shop_name': 'Tên đã dùng', 'address': 'Y', 'phone': '0900000001', 'description': '',
        })
        self.assertContains(response, 'Tên shop đã được sử dụng.')
