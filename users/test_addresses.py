from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from carts.models import Cart, CartItem
from orders.models import Order
from orders.services import create_order
from products.models import Category, Product
from shops.models import Shop
from .models import Address


class BuyerAddressTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.buyer = User.objects.create_user(username='address-buyer', email='address@test.local', role='BUYER')
        cls.other = User.objects.create_user(username='address-other', email='other-address@test.local', role='BUYER')
        cls.seller = User.objects.create_user(username='address-seller', email='seller-address@test.local', role='SELLER')

    def setUp(self):
        self.client.force_login(self.buyer)
        self.values = {
            'receiver_name': 'Người nhận', 'receiver_phone': '0901234567',
            'province': 'TP. Hồ Chí Minh', 'district': '', 'ward': 'Phường Bến Nghé',
            'detail_address': '123 Lê Lợi',
        }

    def save(self, **overrides):
        return self.client.post(reverse('buyer_addresses'), {**self.values, **overrides})

    def address(self, user=None, **overrides):
        return Address.objects.create(user=user or self.buyer, **{**self.values, **overrides})

    def test_page_contains_working_form_and_empty_state(self):
        response = self.client.get(reverse('buyer_addresses'))
        self.assertContains(response, 'Chưa có địa chỉ')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'name="receiver_name"')
        self.assertNotContains(response, 'data-backend-form="pending"')
        self.assertNotContains(response, 'disabled=')

    def test_first_address_is_saved_for_current_user_and_becomes_default(self):
        response = self.save(user_id=self.other.pk, is_archived='on', receiver_name='  Người nhận  ')
        self.assertRedirects(response, reverse('buyer_addresses'))
        address = Address.objects.get()
        self.assertEqual(address.user, self.buyer)
        self.assertEqual(address.receiver_name, 'Người nhận')
        self.assertEqual(address.district, '')
        self.assertTrue(address.is_default)
        self.assertFalse(address.is_archived)
        response = self.client.get(reverse('buyer_addresses'))
        self.assertContains(response, '123 Lê Lợi')
        self.assertContains(response, 'Mặc định')

    def test_invalid_phone_preserves_entered_values_without_saving(self):
        for phone in ['123', '09012345678', '09012abcde', '+84901234567']:
            with self.subTest(phone=phone):
                response = self.save(receiver_phone=phone)
                self.assertEqual(response.status_code, 200)
                self.assertIn('receiver_phone', response.context['form'].errors)
                self.assertEqual(response.context['form']['receiver_name'].value(), self.values['receiver_name'])
                self.assertFalse(Address.objects.exists())

    def test_required_and_oversized_values_are_validated_on_server(self):
        for field, value in [('receiver_name', '  '), ('province', ''), ('ward', ''), ('detail_address', ''), ('province', 'x' * 101), ('detail_address', 'x' * 256)]:
            with self.subTest(field=field, value=value):
                response = self.save(**{field: value})
                self.assertIn(field, response.context['form'].errors)
                self.assertFalse(Address.objects.exists())

    def test_adding_and_changing_default_keeps_one_default(self):
        self.save()
        first = Address.objects.get()
        self.save(detail_address='456 Nguyễn Huệ')
        second = Address.objects.exclude(pk=first.pk).get()
        self.assertFalse(second.is_default)
        response = self.client.post(reverse('buyer_address_default', args=[second.pk]))
        self.assertRedirects(response, reverse('buyer_addresses'))
        first.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertEqual(Address.objects.get(is_default=True).pk, second.pk)
        self.save(detail_address='789 Pasteur', is_default='on')
        self.assertEqual(Address.objects.filter(is_default=True).count(), 1)
        self.assertEqual(Address.objects.get(is_default=True).detail_address, '789 Pasteur')

    def test_database_rejects_two_active_defaults_for_one_buyer(self):
        self.address(is_default=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.address(is_default=True)
        self.address(user=self.other, is_default=True)

    def test_edit_unused_address_updates_existing_record(self):
        address = self.address(is_default=True)
        response = self.client.get(reverse('buyer_addresses'), {'edit': address.pk})
        self.assertEqual(response.context['form']['receiver_name'].value(), 'Người nhận')
        self.save(address_id=address.pk, receiver_name='Tên mới')
        address.refresh_from_db()
        self.assertEqual(address.receiver_name, 'Tên mới')
        self.assertTrue(address.is_default)
        self.assertEqual(Address.objects.count(), 1)

    def test_edit_used_address_preserves_order_recipient(self):
        address = self.address(is_default=True)
        order = Order.objects.create(user=self.buyer, address=address, order_code='ADDRESS-HISTORY', subtotal=100000, total_amount=100000, payment_method='COD')
        self.save(address_id=address.pk, receiver_name='Người nhận mới', detail_address='456 Nguyễn Huệ')
        address.refresh_from_db()
        order.refresh_from_db()
        self.assertTrue(address.is_archived)
        self.assertFalse(address.is_default)
        self.assertEqual(order.address.receiver_name, 'Người nhận')
        self.assertEqual(order.address.detail_address, '123 Lê Lợi')
        saved = Address.objects.get(user=self.buyer, is_archived=False)
        self.assertNotEqual(saved.pk, address.pk)
        self.assertEqual(saved.receiver_name, 'Người nhận mới')
        self.assertTrue(saved.is_default)
        response = self.client.get(reverse('buyer_addresses'))
        self.assertContains(response, '456 Nguyễn Huệ')
        self.assertNotContains(response, '123 Lê Lợi')
        self.assertEqual(self.client.get(reverse('buyer_addresses'), {'edit': address.pk}).status_code, 404)
        self.assertEqual(self.client.post(reverse('buyer_address_default', args=[address.pk])).status_code, 404)

    def test_other_buyers_addresses_cannot_be_read_edited_or_made_default(self):
        address = self.address(user=self.other, receiver_name='Thông tin riêng tư')
        self.assertNotContains(self.client.get(reverse('buyer_addresses')), 'Thông tin riêng tư')
        self.assertEqual(self.client.get(reverse('buyer_addresses'), {'edit': address.pk}).status_code, 404)
        self.assertEqual(self.save(address_id=address.pk).status_code, 404)
        self.assertEqual(self.client.post(reverse('buyer_address_default', args=[address.pk])).status_code, 404)
        address.refresh_from_db()
        self.assertEqual(address.receiver_name, 'Thông tin riêng tư')

    def test_invalid_identifiers_return_not_found(self):
        for value in ['bad', '-1', '9' * 100]:
            self.assertEqual(self.client.get(reverse('buyer_addresses'), {'edit': value}).status_code, 404)
            self.assertEqual(self.save(address_id=value).status_code, 404)

    def test_mutations_require_csrf_authentication_and_post(self):
        address = self.address()
        url = reverse('buyer_address_default', args=[address.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.buyer)
        self.assertEqual(strict.post(reverse('buyer_addresses'), self.values).status_code, 403)
        self.assertEqual(strict.post(url).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.post(reverse('buyer_addresses'), self.values).status_code, 302)
        self.client.force_login(self.seller)
        self.assertEqual(self.client.post(reverse('buyer_addresses'), self.values).status_code, 302)
        self.assertEqual(Address.objects.count(), 1)

    def test_checkout_and_order_creation_use_saved_default_not_archive(self):
        archived = self.address(is_archived=True, receiver_name='Địa chỉ cũ')
        self.save()
        saved = Address.objects.get(user=self.buyer, is_archived=False)
        shop = Shop.objects.create(owner=self.seller, shop_name='Shop địa chỉ', status='ACTIVE')
        category = Category.objects.create(category_name='CPU')
        product = Product.objects.create(shop=shop, category=category, product_name='CPU địa chỉ', slug='address-cpu', price=100000, stock_quantity=2)
        cart = Cart.objects.create(user=self.buyer)
        CartItem.objects.create(cart=cart, product=product, quantity=1)
        response = self.client.get(reverse('buyer_checkout'))
        self.assertEqual(response.context['shipping_address'], saved)
        self.assertNotContains(response, archived.receiver_name)
        order = create_order(self.buyer, 'COD', uuid4())
        self.assertEqual(order.address, saved)
