from decimal import Decimal
from time import time
import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from products.models import Category, Product
from shops.models import Shop
from users.models import Address
from orders.models import Order
from .models import Cart, CartItem


@override_settings(
    BUYER_OTP_EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST='smtp.example.test',
    EMAIL_HOST_USER='otp@pcmatch.test',
    EMAIL_HOST_PASSWORD='test-password',
    DEFAULT_FROM_EMAIL='otp@pcmatch.test',
)
class DatabaseCartTests(TestCase):
    password = 'CartPass!82734'

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username='buyer', email='buyer@example.com', password=cls.password,
            full_name='Người mua', role='BUYER',
        )
        cls.other = get_user_model().objects.create_user(username='other', email='other@example.com')
        shop = Shop.objects.create(owner=cls.other, shop_name='Shop A', status='ACTIVE')
        category = Category.objects.create(category_name='Chuột')
        cls.product = Product.objects.create(
            shop=shop, category=category, product_name='Chuột <Pro> & USB', slug='mouse',
            price='379000.50', stock_quantity=5,
        )

    def add(self, quantity=1, **extra):
        return self.client.post(reverse('buyer_cart_add', args=[self.product.pk]), {'quantity': quantity, **extra})

    def make_item(self, quantity=1, user=None):
        cart, _ = Cart.objects.get_or_create(user=user or self.user)
        return CartItem.objects.create(cart=cart, product=self.product, quantity=quantity)

    def test_anonymous_add_requires_login_and_does_not_write_cart(self):
        response = self.add()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('auth_login') + '?next='))
        self.assertFalse(Cart.objects.exists())
        self.assertEqual(self.client.session['pending_cart_add']['product_id'], self.product.pk)
        self.assertEqual(self.client.get(reverse('buyer_cart')).status_code, 302)

    def test_login_finishes_pending_add_in_database(self):
        self.add(quantity=2)
        response = self.client.post(reverse('auth_login'), {'email': 'BUYER@example.com', 'password': self.password})
        self.assertRedirects(response, reverse('buyer_cart'))
        item = CartItem.objects.get(cart__user=self.user)
        self.assertEqual((item.product, item.quantity), (self.product, 2))
        self.assertNotIn('pending_cart_add', self.client.session)
        self.client.post(reverse('auth_login'), {'email': self.user.email, 'password': self.password})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)

    def test_failed_login_preserves_pending_add_without_database_writes(self):
        self.add()
        response = self.client.post(reverse('auth_login'), {'email': self.user.email, 'password': 'wrong'})
        self.assertContains(response, 'Email hoặc mật khẩu không đúng')
        self.assertFalse(CartItem.objects.exists())
        self.assertIn('pending_cart_add', self.client.session)

    def test_register_creates_real_account_and_finishes_add(self):
        self.add()
        response = self.client.post(reverse('auth_login'), {
            'mode': 'register', 'full_name': 'Người mua mới', 'email': 'new@example.com',
            'password1': self.password, 'password2': self.password,
        })
        self.assertRedirects(response, reverse('auth_verify_email'))
        new_user = get_user_model().objects.get(email='new@example.com')
        code = re.search(r'\b([0-9]{6})\b', mail.outbox[0].body).group(1)
        response = self.client.post(reverse('auth_verify_email'), {'code': code})
        self.assertRedirects(
            response,
            reverse('auth_login') + '?next=' + reverse('buyer_cart'),
            fetch_redirect_response=False,
        )
        response = self.client.post(reverse('auth_login'), {
            'email': 'new@example.com', 'password': self.password,
        })
        self.assertRedirects(response, reverse('buyer_cart'))
        self.assertTrue(new_user.check_password(self.password))
        new_user.refresh_from_db()
        self.assertTrue(new_user.email_verified)
        self.assertEqual(new_user.status, 'ACTIVE')
        self.assertEqual(CartItem.objects.get(cart__user=new_user).product, self.product)

    def test_repeated_add_merges_one_row_and_one_cart(self):
        self.client.force_login(self.user)
        self.add()
        self.add(quantity=2, price='1', user_id=self.other.pk)
        self.assertEqual(Cart.objects.filter(user=self.user).count(), 1)
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(CartItem.objects.get().quantity, 3)
        response = self.client.get(reverse('buyer_cart'))
        self.assertEqual(response.context['subtotal'], Decimal('1137001.50'))

    def test_invalid_quantities_and_unavailable_products_do_not_write(self):
        self.client.force_login(self.user)
        for quantity in [0, -1, '1.5', 'abc', 6, '9' * 50]:
            with self.subTest(quantity=quantity):
                self.add(quantity)
                self.assertFalse(CartItem.objects.exists())
        for status, stock in [('OUT_OF_STOCK', 5), ('INACTIVE', 5), ('ACTIVE', 0)]:
            with self.subTest(status=status, stock=stock):
                Product.objects.filter(pk=self.product.pk).update(status=status, stock_quantity=stock)
                self.add()
                self.assertFalse(CartItem.objects.exists())

    def test_add_cannot_exceed_combined_quantity(self):
        self.client.force_login(self.user)
        item = self.make_item(5)
        self.add()
        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)

    def test_cart_is_server_rendered_and_uses_current_database_prices(self):
        self.client.force_login(self.user)
        self.make_item(2)
        Product.objects.filter(pk=self.product.pk).update(price='400000.25')
        response = self.client.get(reverse('buyer_cart'))
        self.assertContains(response, 'Chuột &lt;Pro&gt; &amp; USB')
        self.assertContains(response, 'value="2"')
        self.assertContains(response, '800.001')
        self.assertNotContains(response, 'js/buyer.js')
        self.assertNotContains(response, 'Đang tải PCMatch')
        self.assertEqual(response.context['subtotal'], Decimal('800000.50'))
        self.assertEqual(response.context['database_cart_count'], 2)

    def test_cart_only_shows_current_user_items(self):
        self.make_item(user=self.other)
        self.client.force_login(self.user)
        response = self.client.get(reverse('buyer_cart'))
        self.assertContains(response, 'Giỏ hàng đang trống')
        self.assertNotContains(response, 'Chuột &lt;Pro&gt;')
        self.assertEqual(response.context['database_cart_count'], 0)

    def test_update_and_remove_persist_in_database(self):
        self.client.force_login(self.user)
        item = self.make_item()
        self.client.post(reverse('buyer_cart_update', args=[item.pk]), {'quantity': 4})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 4)
        for quantity in [0, 6, 'invalid']:
            self.client.post(reverse('buyer_cart_update', args=[item.pk]), {'quantity': quantity})
            item.refresh_from_db()
            self.assertEqual(item.quantity, 4)
        self.client.post(reverse('buyer_cart_remove', args=[item.pk]))
        self.assertFalse(CartItem.objects.exists())

    def test_other_user_cannot_update_or_remove_items(self):
        self.client.force_login(self.user)
        item = self.make_item(user=self.other)
        for route in ['buyer_cart_update', 'buyer_cart_remove']:
            response = self.client.post(reverse(route, args=[item.pk]), {'quantity': 2})
            self.assertEqual(response.status_code, 404)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)

    def test_mutations_require_post_and_csrf(self):
        self.client.force_login(self.user)
        item = self.make_item()
        for route, pk in [('buyer_cart_add', self.product.pk), ('buyer_cart_update', item.pk), ('buyer_cart_remove', item.pk)]:
            self.assertEqual(self.client.get(reverse(route, args=[pk])).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post(reverse('buyer_cart_add', args=[self.product.pk]), {'quantity': 1}).status_code, 403)

    def test_expired_pending_add_is_not_replayed(self):
        session = self.client.session
        session['pending_cart_add'] = {'product_id': self.product.pk, 'quantity': 1, 'expires': time() - 1}
        session.save()
        self.client.post(reverse('auth_login'), {'email': self.user.email, 'password': self.password})
        self.assertFalse(CartItem.objects.exists())

    def test_locked_account_and_external_next_are_rejected(self):
        get_user_model().objects.filter(pk=self.user.pk).update(status='LOCKED')
        response = self.client.post(reverse('auth_login'), {'email': self.user.email, 'password': self.password})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        get_user_model().objects.filter(pk=self.user.pk).update(status='ACTIVE')
        response = self.client.post(reverse('auth_login'), {'email': self.user.email, 'password': self.password, 'next': 'https://example.com/'})
        self.assertRedirects(response, reverse('buyer_cart'))

    def test_logout_ends_the_session_and_keeps_cart(self):
        self.client.force_login(self.user)
        self.make_item()
        response = self.client.get(reverse('auth_logout'))
        self.assertRedirects(response, reverse('auth_login'))
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get(reverse('buyer_cart')).status_code, 302)
        self.assertTrue(CartItem.objects.exists())

    def make_address(self, user=None, **values):
        fields = {
            'receiver_name': 'Người nhận kiểm thử', 'receiver_phone': '0901234567',
            'province': 'TP. Hồ Chí Minh', 'district': 'Quận 1',
            'ward': 'Phường Bến Nghé', 'detail_address': '12 Đường kiểm thử',
        }
        fields.update(values)
        return Address.objects.create(user=user or self.user, **fields)

    def test_cart_checkout_link_opens_real_checkout_instead_of_redirect_loop(self):
        self.client.force_login(self.user)
        self.make_item(2)
        response = self.client.get(reverse('buyer_cart'))
        self.assertContains(response, f'href="{reverse("buyer_checkout")}">Tiến hành thanh toán')
        response = self.client.get(reverse('buyer_checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-page="checkout" data-section="buyer"')
        self.assertContains(response, 'Chuột &lt;Pro&gt; &amp; USB')
        self.assertContains(response, 'Số lượng: 2')

    def test_checkout_uses_current_user_default_address_and_cart_database_values(self):
        self.client.force_login(self.user)
        get_user_model().objects.filter(pk=self.user.pk).update(phone='0902345678')
        self.make_address(receiver_name='Địa chỉ phụ')
        default = self.make_address(is_default=True, receiver_name='Người nhận mặc định')
        private_address = self.make_address(user=self.other, receiver_name='Thông tin riêng tư')
        item = self.make_item(2)
        self.make_item(5, user=self.other)
        Product.objects.filter(pk=self.product.pk).update(price='400000.25')
        response = self.client.get(reverse('buyer_checkout'), {
            'user_id': self.other.pk, 'address_id': private_address.pk, 'subtotal': 1,
        })
        self.assertEqual(response.context['checkout_user'], self.user)
        self.assertEqual(response.context['shipping_address'], default)
        self.assertEqual([row.pk for row in response.context['cart_items']], [item.pk])
        self.assertEqual(response.context['subtotal'], Decimal('800000.50'))
        self.assertEqual(response.context['item_count'], 2)
        for text in ['Người mua', self.user.email, '0902345678', 'Người nhận mặc định', '12 Đường kiểm thử', 'Phường Bến Nghé', 'Quận 1', 'TP. Hồ Chí Minh', '800.001']:
            self.assertContains(response, text)
        self.assertNotContains(response, 'Thông tin riêng tư')
        self.assertNotContains(response, self.other.email)
        self.assertNotContains(response, 'AMD Ryzen 5 7600')
        self.assertNotContains(response, 'Đặt đơn mô phỏng')
        self.assertFalse(Order.objects.exists())
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)

    def test_checkout_handles_missing_profile_fields_and_uses_first_address_if_no_default(self):
        self.client.force_login(self.user)
        self.make_item()
        response = self.client.get(reverse('buyer_checkout'))
        self.assertContains(response, 'Chưa cập nhật số điện thoại.')
        self.assertContains(response, 'Chưa có địa chỉ nhận hàng trong tài khoản.')
        address = self.make_address()
        self.make_address(receiver_name='Địa chỉ thêm sau')
        response = self.client.get(reverse('buyer_checkout'))
        self.assertEqual(response.context['shipping_address'], address)

    def test_checkout_empty_cart_requires_login_and_never_shows_other_users_items(self):
        response = self.client.get(reverse('buyer_checkout'))
        self.assertRedirects(response, reverse('auth_login') + '?next=' + reverse('buyer_checkout'), fetch_redirect_response=False)
        self.make_item(user=self.other)
        self.client.force_login(self.user)
        response = self.client.get(reverse('buyer_checkout'))
        self.assertContains(response, 'Giỏ hàng đang trống')
        self.assertNotContains(response, 'data-checkout-item=')
        self.assertNotContains(response, 'Chuột &lt;Pro&gt; &amp; USB')
        self.assertEqual(self.client.post(reverse('buyer_checkout')).status_code, 405)

    def test_checkout_reports_stock_changes_without_modifying_cart(self):
        self.client.force_login(self.user)
        item = self.make_item(3)
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=1)
        self.assertContains(self.client.get(reverse('buyer_checkout')), 'Số lượng vượt tồn kho (còn 1)')
        Product.objects.filter(pk=self.product.pk).update(status='INACTIVE')
        self.assertContains(self.client.get(reverse('buyer_checkout')), 'Sản phẩm đã hết hàng hoặc tạm ngừng bán.')
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)
