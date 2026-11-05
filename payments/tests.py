from django.test import TestCase
from django.urls import reverse

from carts.models import CartItem
from orders.models import Order
from orders.tests import checkout_data
from .models import Payment


class VNPayNotImplementedTests(TestCase):
    setUpTestData = classmethod(checkout_data)

    def setUp(self):
        self.client.force_login(self.buyer)
        self.checkout_token = self.client.get(reverse('buyer_checkout')).context['checkout_token']

    def test_vnpay_checkout_is_rejected_without_creating_an_order_or_payment(self):
        response = self.client.post(reverse('buyer_place_order'), {
            'paymentMethod': 'VNPAY',
            'checkout_token': self.checkout_token,
        })

        self.assertRedirects(response, reverse('buyer_checkout'))
        self.assertContains(self.client.get(reverse('buyer_checkout')), 'COD')
        self.assertFalse(Order.objects.exists())
        self.assertFalse(Payment.objects.exists())
        self.assertTrue(CartItem.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_unknown_vnpay_ipn_does_not_change_orders_or_inventory(self):
        response = self.client.get(reverse('vnpay_ipn'), {'vnp_TxnRef': 'unknown'})

        self.assertEqual(response.json()['RspCode'], '97')
        self.assertFalse(Order.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_browser_return_rejects_an_invalid_signature(self):
        response = self.client.get(reverse('vnpay_return'), {'vnp_SecureHash': 'invalid'})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())
