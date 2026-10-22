import hashlib
import hmac
from urllib.parse import parse_qs, urlencode, urlparse

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from carts.models import CartItem
from orders.models import Order
from orders.tests import checkout_data
from .models import Payment


@override_settings(VNPAY_TMN_CODE='TESTCODE', VNPAY_HASH_SECRET='test-secret-only', VNPAY_RETURN_URL='https://merchant.test/payments/vnpay/return/')
class VNPayTests(TestCase):
    setUpTestData = classmethod(checkout_data)

    def setUp(self):
        self.client.force_login(self.buyer)
        token = self.client.get(reverse('buyer_checkout')).context['checkout_token']
        self.response = self.client.post(reverse('buyer_place_order'), {'paymentMethod': 'VNPAY', 'checkout_token': token})
        self.order = Order.objects.get()
        self.payment = Payment.objects.get()

    def signed_params(self, **overrides):
        params = {
            'vnp_TmnCode': settings.VNPAY_TMN_CODE, 'vnp_TxnRef': self.payment.transaction_code,
            'vnp_Amount': '20000000', 'vnp_ResponseCode': '00', 'vnp_TransactionStatus': '00',
            'vnp_TransactionNo': '1234567', 'vnp_PayDate': '20261022123000',
            'vnp_OrderInfo': f'Thanh toan {self.order.order_code}',
        }
        params.update(overrides)
        params['vnp_SecureHash'] = hmac.new(settings.VNPAY_HASH_SECRET.encode(), urlencode(sorted(params.items())).encode(), hashlib.sha512).hexdigest()
        return params

    def ipn(self, params=None):
        return self.client.get(reverse('vnpay_ipn'), params or self.signed_params())

    def test_checkout_redirect_is_signed_and_order_waits_for_payment(self):
        query = parse_qs(urlparse(self.response.url).query)
        checksum = query.pop('vnp_SecureHash')[0]
        expected = hmac.new(settings.VNPAY_HASH_SECRET.encode(), urlencode(sorted((key, value[0]) for key, value in query.items())).encode(), hashlib.sha512).hexdigest()
        self.assertEqual(checksum, expected)
        self.assertEqual(query['vnp_Amount'], ['20000000'])
        self.assertEqual(query['vnp_ReturnUrl'], [settings.VNPAY_RETURN_URL])
        self.assertEqual((self.order.order_status, self.order.payment_status), ('AWAITING_PAYMENT', 'PENDING'))
        self.assertFalse(CartItem.objects.exists())

    def test_verified_ipn_marks_paid_and_waits_for_admin(self):
        self.client.logout()
        self.assertEqual(self.ipn().json()['RspCode'], '00')
        self.order.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual((self.order.order_status, self.order.payment_status), ('PENDING', 'PAID'))
        self.assertEqual(self.payment.gateway_transaction_no, '1234567')
        self.assertIsNotNone(self.payment.paid_at)
        self.assertEqual(self.order.order_items.get().item_status, 'PENDING')

    def test_repeated_callback_does_not_duplicate_history(self):
        self.ipn()
        self.assertEqual(self.ipn().json()['RspCode'], '02')
        self.assertEqual(self.order.status_history.count(), 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)

    def test_browser_return_never_marks_order_paid(self):
        response = self.client.get(reverse('vnpay_return'), self.signed_params())
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'PENDING')
        self.assertEqual(self.order.order_status, 'AWAITING_PAYMENT')

    def test_signature_amount_merchant_reference_and_duplicate_parameters(self):
        params = self.signed_params()
        params['vnp_Amount'] = '1'
        self.assertEqual(self.ipn(params).json()['RspCode'], '97')
        self.assertEqual(self.ipn(self.signed_params(vnp_Amount='1')).json()['RspCode'], '04')
        self.assertEqual(self.ipn(self.signed_params(vnp_TmnCode='WRONG')).json()['RspCode'], '97')
        self.assertEqual(self.ipn(self.signed_params(vnp_TxnRef='missing')).json()['RspCode'], '01')
        self.assertEqual(self.ipn(self.signed_params(vnp_Amount='NaN')).json()['RspCode'], '04')
        params = self.signed_params()
        params['vnp_Amount'] = ['20000000', '1']
        self.assertEqual(self.ipn(params).json()['RspCode'], '97')
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'PENDING')

    def test_terminal_failure_releases_stock_exactly_once(self):
        params = self.signed_params(vnp_ResponseCode='24', vnp_TransactionStatus='02')
        self.assertEqual(self.ipn(params).json()['RspCode'], '00')
        self.assertEqual(self.ipn(params).json()['RspCode'], '02')
        self.order.refresh_from_db()
        self.assertEqual((self.order.order_status, self.order.payment_status), ('CANCELLED', 'FAILED'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_uncertain_result_keeps_reservation_for_reconciliation(self):
        for status in ['01', '04', '05', '07']:
            self.assertEqual(self.ipn(self.signed_params(vnp_ResponseCode='07', vnp_TransactionStatus=status)).json()['RspCode'], '99')
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'PENDING')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertEqual(self.ipn().json()['RspCode'], '00')

    def test_admin_cannot_approve_unpaid_vnpay(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('update_order_status', args=[self.order.pk]), {'status': 'COMFIRMED'})
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, 'AWAITING_PAYMENT')

    def test_paid_vnpay_fulfillment_keeps_paid_without_cod_checkbox(self):
        self.ipn()
        self.client.force_login(self.admin)
        self.client.post(reverse('update_order_status', args=[self.order.pk]), {'status': 'COMFIRMED'})
        self.client.force_login(self.owner)
        for status in ['PROCESSING', 'SHIPPING', 'DELIVERED']:
            self.client.post(reverse('shop_order_update_status', args=[self.order.pk]), {'new_status': status})
        self.order.refresh_from_db()
        self.assertEqual((self.order.order_status, self.order.payment_status), ('DELIVERED', 'PAID'))
        self.assertEqual(self.ipn().json()['RspCode'], '02')

    def test_return_checks_signature_and_buyer_ownership(self):
        self.assertEqual(self.client.get(reverse('vnpay_return'), {'vnp_SecureHash': 'bad'}).status_code, 400)
        self.client.force_login(self.other_buyer)
        self.assertEqual(self.client.get(reverse('vnpay_return'), self.signed_params()).status_code, 404)
