from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from carts.models import Cart, CartItem
from payments.models import Payment
from products.models import Category, Product
from shops.models import Shop
from users.models import Address
from .models import Order, OrderItem


def checkout_data(cls):
    User = get_user_model()
    cls.buyer = User.objects.create_user(username='checkout-buyer', email='buyer@test.local', role='BUYER')
    cls.other_buyer = User.objects.create_user(username='other-buyer', email='other@test.local', role='BUYER')
    cls.owner = User.objects.create_user(username='checkout-seller', email='seller@test.local', role='SELLER')
    cls.other_owner = User.objects.create_user(username='other-seller', email='seller2@test.local', role='SELLER')
    cls.admin = User.objects.create_user(username='checkout-admin', email='admin@test.local', role='ADMIN', is_staff=True)
    cls.shop = Shop.objects.create(owner=cls.owner, shop_name='Shop A', status='ACTIVE')
    cls.other_shop = Shop.objects.create(owner=cls.other_owner, shop_name='Shop B', status='ACTIVE')
    category = Category.objects.create(category_name='CPU')
    cls.product = Product.objects.create(shop=cls.shop, category=category, product_name='CPU checkout', slug='checkout-cpu', price=100000, stock_quantity=5)
    cls.other_product = Product.objects.create(shop=cls.other_shop, category=category, product_name='CPU B', slug='checkout-b', price=300000, stock_quantity=3)
    cls.address = Address.objects.create(user=cls.buyer, receiver_name='Người mua', receiver_phone='0901234567', province='TP.HCM', district='Quận 1', ward='Phường 1', detail_address='123 Lê Lợi')
    cls.cart = Cart.objects.create(user=cls.buyer)
    CartItem.objects.create(cart=cls.cart, product=cls.product, quantity=2)


class CheckoutTests(TestCase):
    setUpTestData = classmethod(checkout_data)

    def setUp(self):
        self.client.force_login(self.buyer)

    def submit(self, method='COD', token=None, **extra):
        if token is None:
            token = self.client.get(reverse('buyer_checkout')).context['checkout_token']
        return self.client.post(reverse('buyer_place_order'), {'paymentMethod': method, 'checkout_token': token, **extra})

    def create_cod(self):
        self.submit()
        return Order.objects.get()

    def update_shop(self, order, status, owner=None, **extra):
        self.client.force_login(owner or self.owner)
        return self.client.post(reverse('shop_order_update_status', args=[order.pk]), {'new_status': status, **extra})

    def approve(self, order):
        self.client.force_login(self.admin)
        return self.client.post(reverse('update_order_status', args=[order.pk]), {'status': 'COMFIRMED'})

    def test_cod_creates_real_order_from_server_prices(self):
        response = self.submit(total_amount='1', user_id=self.other_buyer.pk, address_id=999999)
        order = Order.objects.get()
        self.assertRedirects(response, f'{reverse("buyer_order")}?id={order.order_code}')
        self.assertEqual(order.user, self.buyer)
        self.assertEqual(order.address, self.address)
        self.assertEqual(order.total_amount, Decimal('200000'))
        self.assertEqual((order.payment_status, order.order_status), ('UNPAID', 'PENDING'))
        self.assertEqual(order.order_items.get().unit_price, Decimal('100000'))
        self.assertEqual(order.payments.get().status, 'UNPAID')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertFalse(CartItem.objects.exists())

    def test_repeated_post_is_idempotent_even_after_cart_changes(self):
        token = self.client.get(reverse('buyer_checkout')).context['checkout_token']
        self.submit(token=token)
        CartItem.objects.create(cart=self.cart, product=self.other_product, quantity=1)
        self.submit(token=token)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(CartItem.objects.get().product, self.other_product)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)

    def test_validation_failures_leave_cart_stock_and_orders_unchanged(self):
        for method in ['', 'INVALID']:
            self.submit(method)
        self.product.stock_quantity = 1
        self.product.save()
        self.submit()
        self.assertFalse(Order.objects.exists())
        self.assertFalse(Payment.objects.exists())
        self.assertEqual(CartItem.objects.get().quantity, 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 1)

    def test_missing_address_and_empty_cart_are_rejected(self):
        self.address.delete()
        self.submit()
        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.exists())
        CartItem.objects.all().delete()
        from .services import checkout_token
        self.submit(token=checkout_token(self.buyer))
        self.assertFalse(Order.objects.exists())

    def test_failed_line_rolls_back_whole_checkout(self):
        CartItem.objects.create(cart=self.cart, product=self.other_product, quantity=10)
        self.submit()
        self.assertFalse(Order.objects.exists())
        self.assertEqual(CartItem.objects.count(), 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_persistence_failure_rolls_back_reserved_stock_and_cart(self):
        with patch('orders.services.Payment.objects.create', side_effect=IntegrityError('write failed')):
            self.submit()
        self.assertFalse(Order.objects.exists())
        self.assertFalse(Payment.objects.exists())
        self.assertEqual(CartItem.objects.get().quantity, 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_tampered_and_foreign_checkout_tokens_are_rejected(self):
        from .services import checkout_token
        self.submit(token='tampered')
        self.submit(token=checkout_token(self.other_buyer))
        self.assertFalse(Order.objects.exists())

    def test_post_requires_authentication_and_csrf(self):
        self.assertEqual(self.client.get(reverse('buyer_place_order')).status_code, 405)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.buyer)
        self.assertEqual(client.post(reverse('buyer_place_order'), {'paymentMethod': 'COD'}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.post(reverse('buyer_place_order')).status_code, 302)
        self.assertFalse(Order.objects.exists())

    @override_settings(VNPAY_TMN_CODE='', VNPAY_HASH_SECRET='', VNPAY_RETURN_URL='')
    def test_unconfigured_vnpay_does_not_create_or_reserve_anything(self):
        self.submit('VNPAY')
        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_only_admin_can_approve_and_only_using_post(self):
        order = self.create_cod()
        url = reverse('update_order_status', args=[order.pk])
        self.client.post(url, {'status': 'COMFIRMED'})
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url, {'status': 'COMFIRMED'}).status_code, 405)
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'PENDING')
        self.approve(order)
        self.approve(order)
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'COMFIRMED')
        self.assertEqual(order.status_history.count(), 2)
        response = self.client.get(reverse('load_ListOrder'))
        self.assertContains(response, order.order_code)

    def test_shop_cannot_approve_or_skip_processing(self):
        order = self.create_cod()
        self.update_shop(order, 'COMFIRMED')
        self.update_shop(order, 'PROCESSING')
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'PENDING')
        self.approve(order)
        self.update_shop(order, 'SHIPPING')
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'COMFIRMED')

    def test_cod_requires_delivery_and_collection_before_paid(self):
        order = self.create_cod()
        self.approve(order)
        self.update_shop(order, 'PROCESSING')
        self.update_shop(order, 'SHIPPING')
        self.update_shop(order, 'DELIVERED')
        order.refresh_from_db()
        self.assertEqual((order.order_status, order.payment_status), ('SHIPPING', 'UNPAID'))
        response = self.client.get(reverse('shop_order'), {'id': order.pk})
        self.assertContains(response, 'name="cod_collected"')
        self.update_shop(order, 'DELIVERED', cod_collected='yes')
        self.update_shop(order, 'DELIVERED', cod_collected='yes')
        order.refresh_from_db()
        self.assertEqual((order.order_status, order.payment_status), ('DELIVERED', 'PAID'))
        self.assertEqual(order.payments.get().status, 'PAID')
        self.assertIsNotNone(order.payments.get().paid_at)
        self.product.refresh_from_db()
        self.assertEqual(self.product.sold_quantity, 2)

    def test_multi_shop_completion_is_scoped_to_each_shop(self):
        CartItem.objects.create(cart=self.cart, product=self.other_product, quantity=1)
        order = self.create_cod()
        self.approve(order)
        for status in ['PROCESSING', 'SHIPPING', 'DELIVERED']:
            self.update_shop(order, status, cod_collected='yes')
        order.refresh_from_db()
        self.assertEqual((order.order_status, order.payment_status), ('COMFIRMED', 'UNPAID'))
        self.assertEqual(OrderItem.objects.get(order=order, shop=self.other_shop).item_status, 'COMFIRMED')
        self.assertContains(self.client.get(reverse('shop_order'), {'id': order.pk}), 'Hoàn thành')
        for status in ['PROCESSING', 'SHIPPING', 'DELIVERED']:
            self.update_shop(order, status, owner=self.other_owner, cod_collected='yes')
        order.refresh_from_db()
        self.assertEqual((order.order_status, order.payment_status), ('DELIVERED', 'PAID'))

    def test_foreign_shop_and_buyer_cannot_access_order(self):
        order = self.create_cod()
        response = self.update_shop(order, 'PROCESSING', owner=self.other_owner)
        self.assertEqual(response.status_code, 404)
        self.client.force_login(self.other_buyer)
        self.assertEqual(self.client.get(reverse('buyer_order'), {'id': order.order_code}).status_code, 404)
        self.assertNotContains(self.client.get(reverse('buyer_orders')), order.order_code)
