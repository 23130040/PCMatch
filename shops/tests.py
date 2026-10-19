from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

from orders.models import Order, OrderItem, Return
from products.models import Brand, Category, Product, ProductQuestion
from users.models import Address
from .models import Shop


class ShopBackendLayoutsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username='shop-owner', email='owner@example.test', password='ShopOwner!789', full_name='Chủ gian hàng', status='ACTIVE')
        cls.other = User.objects.create_user(username='other-owner', email='other@example.test', password='OtherOwner!789', full_name='Chủ khác', status='ACTIVE')
        cls.buyer = User.objects.create_user(username='shop-buyer', email='shopbuyer@example.test', password='ShopBuyer!789', full_name='Khách hàng', status='ACTIVE')
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

    def test_account_without_shop_sees_empty_layouts(self):
        self.client.force_login(self.buyer)
        for name in ['shop_dashboard', 'shop_offers', 'shop_orders', 'shop_questions', 'shop_revenue', 'shop_inventory']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'chưa được liên kết')
            self.assertNotContains(response, self.product.product_name)
            self.assertNotContains(response, self.foreign_product.product_name)

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

    def test_unimplemented_actions_cannot_simulate_a_success(self):
        response = self.client.post(reverse('shop_offers'), {'product_name': 'Fake', 'price': '1'})
        self.assertEqual(response.status_code, 405)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal('100000'))
