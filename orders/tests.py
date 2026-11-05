from decimal import Decimal
from datetime import timedelta
import hashlib
import hmac
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from carts.models import Cart, CartItem
from notifications.models import Notification
from payments.models import Payment
from products.models import Category, Product
from shops.models import Shop
from users.models import Address
from .models import CancellationRequest, Order, OrderItem, ShopOrder
from .services import (
    complete_delivered_shop_orders,
    escalate_expired_cancellation_requests,
    expire_unconfirmed_shop_orders,
    mark_carrier_delivered,
    request_order_cancellation,
)


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
        owner = owner or self.owner
        self.client.force_login(owner)
        if status == 'SHIPPING':
            extra.setdefault('carrier_name', 'Hãng kiểm thử')
            extra.setdefault('tracking_code', f'TRACK-{order.pk}-{owner.pk}')
            extra['action'] = 'handoff'
        return self.client.post(reverse('shop_order_update_status', args=[order.pk]), {'new_status': status, **extra})

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

    def test_new_order_is_listed_and_notified_in_the_owning_shop_portal(self):
        order = self.create_cod()
        self.client.force_login(self.owner)

        response = self.client.get(reverse('shop_orders'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.order_code)
        self.assertEqual(response.context['orders_page'].paginator.count, 1)
        self.assertTrue(Notification.objects.filter(
            user=self.owner,
            type='ORDER_NEW',
            message__contains=order.order_code,
        ).exists())

    def test_buyer_notifications_show_unread_count_and_can_be_marked_read(self):
        first = Notification.objects.create(user=self.buyer, title='Đơn đã được tạo', message='Đơn hàng đang chờ shop.')
        Notification.objects.create(user=self.buyer, title='Cập nhật mới', message='Shop đã cập nhật đơn.')

        response = self.client.get(reverse('buyer_notifications'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2 thông báo · 2 chưa đọc')
        self.assertContains(response, 'Đơn đã được tạo')
        self.assertContains(response, 'aria-label="Thông báo, 2 chưa đọc"')
        self.assertEqual(response.context['notification_count'], 2)

        self.client.post(reverse('buyer_notifications'), {'notification_id': first.pk})
        first.refresh_from_db()
        self.assertTrue(first.is_read)
        self.assertEqual(self.client.get(reverse('buyer_notifications')).context['unread_notification_count'], 1)

        self.client.post(reverse('buyer_notifications'))
        self.assertFalse(Notification.objects.filter(user=self.buyer, is_read=False).exists())

    def test_buyer_cannot_mark_another_users_notification_as_read(self):
        foreign_note = Notification.objects.create(
            user=self.other_buyer,
            title='Thông báo riêng',
            message='Không thuộc tài khoản đang đăng nhập.',
        )

        response = self.client.post(reverse('buyer_notifications'), {'notification_id': foreign_note.pk})

        self.assertEqual(response.status_code, 404)
        foreign_note.refresh_from_db()
        self.assertFalse(foreign_note.is_read)

    def test_buyer_notifications_page_includes_all_records_through_pagination(self):
        Notification.objects.bulk_create([
            Notification(user=self.buyer, title=f'Thông báo {index}', message='Cập nhật đơn hàng.')
            for index in range(21)
        ])

        response = self.client.get(reverse('buyer_notifications'), {'page': 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['notification_total'], 21)
        self.assertEqual(len(response.context['notifications_page']), 1)
        self.assertContains(response, 'Trang 2 / 2')

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

    def test_admin_order_page_is_read_only_and_order_is_already_available_to_shop(self):
        order = self.create_cod()
        self.client.force_login(self.admin)
        response = self.client.get(reverse('staff_order_detail', args=[order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Xác nhận đơn')
        self.assertEqual(
            self.client.post(f'/staff/order/{order.pk}/update/', {'status': 'COMFIRMED'}).status_code,
            404,
        )
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'PENDING')
        self.assertEqual(order.status_history.count(), 1)
        self.assertEqual(order.shop_orders.get(shop=self.shop).status, 'PENDING')
        response = self.client.get(reverse('load_ListOrder'))
        self.assertContains(response, order.order_code)
        self.assertContains(response, reverse('staff_order_detail', args=[order.pk]))

    def test_staff_order_detail_shows_all_order_data_and_history(self):
        order = self.create_cod()
        OrderItem.objects.create(
            order=order,
            product=self.other_product,
            shop=self.other_shop,
            quantity=3,
            unit_price=Decimal('300000'),
            subtotal=Decimal('900000'),
            item_status='PENDING',
        )
        order.subtotal = Decimal('1100000')
        order.shipping_fee = Decimal('15000')
        order.platform_fee = Decimal('22000')
        order.total_amount = Decimal('1137000')
        order.save(update_fields=['subtotal', 'shipping_fee', 'platform_fee', 'total_amount'])
        url = reverse('staff_order_detail', args=[order.pk])

        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.admin)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        for expected in [
            order.order_code,
            'Người mua',
            '0901234567',
            '123 Lê Lợi',
            'Chờ shop xác nhận',
            'Chưa thanh toán',
            'Cash on Delivery',
            'CPU checkout',
            'Shop A',
            'CPU B',
            'Shop B',
            'Tạm tính',
            'Phí giao hàng',
            'Phí nền tảng',
            'Tổng tiền',
            'Buyer đặt đơn; đang chờ shop xác nhận.',
            'Tiến độ theo shop',
        ]:
            with self.subTest(expected=expected):
                self.assertContains(response, expected)
        self.assertNotContains(response, 'Xác nhận đơn')

    def test_staff_order_detail_never_exposes_order_confirmation(self):
        order = self.create_cod()
        self.client.force_login(self.admin)

        response = self.client.get(reverse('staff_order_detail', args=[order.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chờ shop xác nhận')
        self.assertNotContains(response, 'Xác nhận đơn')

    def test_staff_order_detail_rejects_missing_order(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('staff_order_detail', args=[999999]))

        self.assertEqual(response.status_code, 404)

    def test_shop_cannot_skip_confirmation_or_modify_another_shops_order(self):
        order = self.create_cod()
        self.update_shop(order, 'SHIPPING')
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'PENDING')
        self.update_shop(order, 'PROCESSING', owner=self.other_owner)
        self.update_shop(order, 'PROCESSING')
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'PROCESSING')

    def test_shop_handoff_waits_for_carrier_and_buyer_confirmation(self):
        order = self.create_cod()
        self.update_shop(order, 'PROCESSING')
        self.update_shop(order, 'SHIPPING')
        shop_order = order.shop_orders.get(shop=self.shop)
        result = mark_carrier_delivered(
            provider='test-carrier',
            event_id=f'event-{order.pk}',
            tracking_code=shop_order.tracking_code,
        )
        self.assertEqual(result, 'delivered')
        order.refresh_from_db()
        self.assertEqual((order.order_status, order.payment_status), ('DELIVERED', 'UNPAID'))
        self.client.force_login(self.buyer)
        self.client.post(reverse('buyer_confirm_received', args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual((order.order_status, order.payment_status), ('COMPLETED', 'UNPAID'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.sold_quantity, 2)

    def test_buyer_order_detail_shows_shop_status_and_cancellation_options(self):
        order = self.create_cod()
        response = self.client.get(reverse('buyer_order'), {'id': order.order_code})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.shop.shop_name)
        self.assertContains(response, 'Chờ shop xác nhận')
        self.assertContains(response, 'Gửi yêu cầu hủy')
        self.assertContains(response, 'Đổi ý')

    def test_multi_shop_status_rolls_up_from_the_slowest_active_shop(self):
        CartItem.objects.create(cart=self.cart, product=self.other_product, quantity=1)
        order = self.create_cod()
        self.update_shop(order, 'PROCESSING')
        self.update_shop(order, 'SHIPPING')
        first = order.shop_orders.get(shop=self.shop)
        mark_carrier_delivered(provider='test-carrier', event_id='first', tracking_code=first.tracking_code)
        order.refresh_from_db()
        self.assertEqual((order.order_status, order.payment_status), ('PENDING', 'UNPAID'))
        self.assertEqual(OrderItem.objects.get(order=order, shop=self.other_shop).item_status, 'PENDING')
        self.assertContains(self.client.get(reverse('shop_order'), {'id': order.pk}), 'Chờ buyer xác nhận')
        self.update_shop(order, 'PROCESSING', owner=self.other_owner)
        self.update_shop(order, 'SHIPPING', owner=self.other_owner)
        second = order.shop_orders.get(shop=self.other_shop)
        mark_carrier_delivered(provider='test-carrier', event_id='second', tracking_code=second.tracking_code)
        order.refresh_from_db()
        self.assertEqual((order.order_status, order.payment_status), ('DELIVERED', 'UNPAID'))

    def test_shop_rejection_restores_stock_and_records_reason(self):
        order = self.create_cod()
        self.update_shop(
            order,
            'CANCELLED',
            action='reject',
            reason='OUT_OF_STOCK',
            note='Tồn kho vừa hết.',
        )
        shop_order = order.shop_orders.get(shop=self.shop)
        self.assertEqual(shop_order.status, 'CANCELLED')
        self.assertIn('Hết hàng', shop_order.history.filter(new_status='CANCELLED').get().note)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_buyer_cancels_pending_single_shop_order_and_restores_stock(self):
        order = self.create_cod()
        response = self.client.post(
            reverse('buyer_cancel_order', args=[order.pk]),
            {'reason': 'CHANGED_MIND'},
        )
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.order_status, 'CANCELLED')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_multishop_buyer_cancellation_is_independent_per_shop(self):
        CartItem.objects.create(cart=self.cart, product=self.other_product, quantity=1)
        order = self.create_cod()
        self.update_shop(order, 'PROCESSING')

        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse('buyer_cancel_order', args=[order.pk]),
            {'reason': 'CHANGED_MIND', 'note': 'Đặt nhầm.'},
        )
        self.assertEqual(response.status_code, 302)
        shop_a = order.shop_orders.get(shop=self.shop)
        shop_b = order.shop_orders.get(shop=self.other_shop)
        cancellation = CancellationRequest.objects.get(shop_order=shop_a)
        self.assertEqual(cancellation.status, 'PENDING')
        self.assertEqual(shop_b.status, 'CANCELLED')
        self.other_product.refresh_from_db()
        self.assertEqual(self.other_product.stock_quantity, 3)

        self.client.force_login(self.owner)
        self.client.post(reverse('shop_order_update_status', args=[order.pk]), {
            'action': 'approve_cancellation',
            'cancellation_request_id': cancellation.pk,
        })
        shop_a.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(shop_a.status, 'CANCELLED')
        self.assertEqual(order.order_status, 'CANCELLED')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_unconfirmed_timeout_restores_stock_and_records_system_actor(self):
        order = self.create_cod()
        now = timezone.now() + timedelta(days=1)
        self.assertEqual(expire_unconfirmed_shop_orders(now), 1)
        shop_order = order.shop_orders.get(shop=self.shop)
        self.assertEqual(shop_order.status, 'CANCELLED')
        history = shop_order.history.filter(new_status='CANCELLED').get()
        self.assertIsNone(history.changed_by)
        self.assertIn('Hệ thống', history.note)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    @override_settings(CARRIER_WEBHOOK_SECRET='test-webhook-secret')
    def test_signed_carrier_webhook_is_idempotent(self):
        order = self.create_cod()
        self.update_shop(order, 'PROCESSING')
        self.update_shop(order, 'SHIPPING')
        shop_order = order.shop_orders.get(shop=self.shop)
        body = json.dumps({
            'provider': 'test-carrier',
            'event_id': 'delivery-1',
            'tracking_code': shop_order.tracking_code,
            'status': 'DELIVERED',
        }).encode()
        timestamp = str(int(timezone.now().timestamp()))
        signature = hmac.new(
            b'test-webhook-secret',
            timestamp.encode() + b'.' + body,
            hashlib.sha256,
        ).hexdigest()
        headers = {
            'HTTP_X_PCMATCH_TIMESTAMP': timestamp,
            'HTTP_X_PCMATCH_SIGNATURE': signature,
        }
        url = reverse('carrier_delivery_webhook')
        first = self.client.post(url, body, content_type='application/json', **headers)
        duplicate = self.client.post(url, body, content_type='application/json', **headers)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()['result'], 'delivered')
        self.assertEqual(duplicate.json()['result'], 'duplicate')
        shop_order.refresh_from_db()
        self.assertEqual(shop_order.status, 'DELIVERED')

    def test_delivered_order_auto_completes_after_three_days(self):
        order = self.create_cod()
        self.update_shop(order, 'PROCESSING')
        self.update_shop(order, 'SHIPPING')
        shop_order = order.shop_orders.get(shop=self.shop)
        mark_carrier_delivered(
            provider='test-carrier',
            event_id='auto-complete',
            tracking_code=shop_order.tracking_code,
        )
        self.assertEqual(complete_delivered_shop_orders(timezone.now() + timedelta(days=4)), 1)
        shop_order.refresh_from_db()
        self.assertEqual(shop_order.status, 'COMPLETED')
        self.assertIsNone(shop_order.history.filter(new_status='COMPLETED').get().changed_by)

    def test_unanswered_cancellation_is_escalated_for_admin_resolution(self):
        CartItem.objects.create(cart=self.cart, product=self.other_product, quantity=1)
        order = self.create_cod()
        self.update_shop(order, 'PROCESSING')
        cancellation_result = request_order_cancellation(
            order.pk, self.buyer, 'CHANGED_MIND', 'Đổi ý.',
        )
        self.assertTrue(cancellation_result['request_created'])
        cancellation = CancellationRequest.objects.get(shop_order__shop=self.shop)
        self.assertEqual(
            escalate_expired_cancellation_requests(timezone.now() + timedelta(hours=13)),
            1,
        )
        cancellation.refresh_from_db()
        self.assertEqual(cancellation.status, 'ESCALATED')

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('staff_resolve_cancellation', args=[cancellation.pk]),
            {'decision': 'approve'},
        )
        self.assertEqual(response.status_code, 302)
        cancellation.refresh_from_db()
        self.assertEqual(cancellation.status, 'ADMIN_APPROVED')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_foreign_shop_and_buyer_cannot_access_order(self):
        order = self.create_cod()
        response = self.update_shop(order, 'PROCESSING', owner=self.other_owner)
        self.assertEqual(response.status_code, 404)
        self.client.force_login(self.other_buyer)
        self.assertEqual(self.client.get(reverse('buyer_order'), {'id': order.order_code}).status_code, 404)
        self.assertNotContains(self.client.get(reverse('buyer_orders')), order.order_code)
