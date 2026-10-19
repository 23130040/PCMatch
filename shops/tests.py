from decimal import Decimal
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from notifications.models import Notification
from orders.models import Order, OrderItem, Return
from products.models import Brand, Category, Product, ProductQuestion
from users.models import Address, EmailVerificationToken
from .models import Shop


class ShopBackendLayoutsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username='shop-owner', email='owner@example.test', password='ShopOwner!789', full_name='Chủ gian hàng', role='SELLER', status='ACTIVE')
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
        self.client.force_login(self.admin)
        self.client.post(reverse('staff_shop_approve', args=[self.shop.pk]))
        self.client.post(reverse('staff_shop_approve', args=[self.shop.pk]))
        self.assertEqual(
            Notification.objects.filter(user=self.seller, type='SHOP_APPROVED').count(), 1)

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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
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
        # Step 1: seller account.
        response = self.register()
        self.assertRedirects(response, reverse('shop_verify_email'), fetch_redirect_response=False)
        seller = get_user_model().objects.get(username='newseller')
        self.assertEqual(seller.role, 'SELLER')
        self.assertFalse(seller.email_verified)

        # Step 2a: email verification page and activation link.
        token = EmailVerificationToken.objects.get(user=seller)
        response = self.client.get(reverse('shop_verify_email'))
        self.assertContains(response, 'Vui lòng kiểm tra email')
        response = self.client.get(reverse('shop_verify_email_confirm', args=[token.token]))
        self.assertRedirects(response, reverse('shop_verify_phone'), fetch_redirect_response=False)
        seller.refresh_from_db()
        self.assertTrue(seller.email_verified)

        # Step 2b: phone OTP.
        response = self.client.get(reverse('shop_verify_phone'))
        self.assertEqual(response.status_code, 200)
        code = self.client.session['shop_phone_otp']['code']
        response = self.client.post(reverse('shop_verify_phone'), {'phone': '0901234567', 'code': code})
        self.assertRedirects(response, reverse('shop_onboarding_profile'), fetch_redirect_response=False)
        seller.refresh_from_db()
        self.assertTrue(seller.phone_verified)

        # Step 3: shop profile.
        response = self.client.post(reverse('shop_onboarding_profile'), {
            'shop_name': 'Shop mới', 'address': 'Hà Nội', 'phone': '0901234567', 'description': 'Mô tả ngắn',
        })
        self.assertRedirects(response, reverse('shop_onboarding_legal'), fetch_redirect_response=False)
        shop = Shop.objects.get(owner=seller)
        self.assertEqual(shop.status, 'PENDING')

        # Step 4: legal documents -> pending approval.
        response = self.client.post(reverse('shop_onboarding_legal'), {
            'id_card': SimpleUploadedFile('cccd.jpg', b'cccd-bytes'),
            'business_license': SimpleUploadedFile('gpkd.jpg', b'gpkd-bytes'),
        })
        self.assertRedirects(response, reverse('shop_onboarding_pending'), fetch_redirect_response=False)
        shop.refresh_from_db()
        self.assertIsNotNone(shop.legal_submitted_at)

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
