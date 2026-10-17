"""Serve isolated fixtures for checking Shop HTML; never modify the working database."""
import os
import sqlite3
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
os.environ['DJANGO_SETTINGS_MODULE'] = 'PCMatch.settings'
from django.conf import settings

copy = root / 'artifacts/backend_shop_browser.sqlite3'
copy.parent.mkdir(exist_ok=True)
with sqlite3.connect(f'file:{root / "db.sqlite3"}?mode=ro', uri=True) as source:
    with sqlite3.connect(copy) as target:
        source.backup(target)
settings.DATABASES['default']['NAME'] = copy

import django
django.setup()
from django.contrib.auth import get_user_model
from django.core.management import call_command
from products.models import Category, Product, ProductQuestion, ProductAnswer
from shops.models import Shop
from orders.models import Order, OrderItem, Return
from users.models import Address

User = get_user_model()
owner = User.objects.create_user(username='backend-shop-check', email='backendshop@example.test', password='BackendShop!9472', full_name='Gian hàng kiểm thử', status='ACTIVE')
User.objects.create_user(username='backend-staff-check', email='backendstaff@example.test', password='BackendStaff!9472', full_name='Quản trị kiểm thử', role='ADMIN', is_staff=True, status='ACTIVE')
other = User.objects.create_user(username='backend-other-check', email='backendother@example.test', password='BackendOther!9472', full_name='Tài khoản khác', status='ACTIVE')
shop = Shop.objects.create(owner=owner, shop_name='Gian hàng kiểm thử', phone='0901234567', address='123 Lê Lợi', status='ACTIVE')
foreign_shop = Shop.objects.create(owner=other, shop_name='Gian hàng khác', phone='0901234568', address='456 Lê Lợi', status='ACTIVE')
category = Category.objects.create(category_name='Linh kiện kiểm thử')
product = Product.objects.create(shop=shop, category=category, product_name='CPU của gian hàng kiểm thử', slug='backend-browser-cpu', price=1500000, stock_quantity=8, sold_quantity=1)
Product.objects.create(shop=shop, category=category, product_name='RAM hết hàng kiểm thử', slug='backend-browser-ram', price=800000, stock_quantity=0)
foreign = Product.objects.create(shop=foreign_shop, category=category, product_name='Sản phẩm riêng tư của shop khác', slug='backend-browser-foreign', price=9900000, stock_quantity=1)
address = Address.objects.create(user=owner, receiver_name='Người nhận kiểm thử', receiver_phone='0901234567', province='TP.HCM', district='Quận 1', ward='Bến Nghé', detail_address='123 Lê Lợi')
for index, status in enumerate(['PENDING', 'DELIVERED']):
    order = Order.objects.create(user=owner, address=address, order_code=f'BACKEND-CHECK-{index}', subtotal=1500000, total_amount=1500000, payment_method='COD', payment_status='PAID', order_status=status)
    OrderItem.objects.create(order=order, shop=shop, product=product, quantity=1, unit_price=1500000, subtotal=1500000, item_status=status)
    if index == 0:
        Return.objects.create(order=order, user=owner, reason='Lý do đổi trả kiểm thử')
ProductQuestion.objects.create(product=product, user=owner, question='Câu hỏi chưa trả lời kiểm thử')
question = ProductQuestion.objects.create(product=product, user=owner, question='Câu hỏi đã trả lời kiểm thử', status=True)
ProductAnswer.objects.create(question=question, user=owner, answer='Nội dung trả lời từ cơ sở dữ liệu')
call_command('runserver', '127.0.0.1:8767', use_reloader=False)
