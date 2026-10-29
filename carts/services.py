from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from products.models import Product
from .models import Cart, CartItem


def cart_summary(user):
    items = list(CartItem.objects.filter(cart__user=user)
                 .select_related('product__shop', 'product__brand')
                 .order_by('product__shop_id', 'added_at', 'pk'))
    for item in items:
        item.line_total = item.product.price * item.quantity
        item.available = item.product.status == 'ACTIVE' and item.product.stock_quantity > 0
    return {
        'cart_items': items,
        'subtotal': sum((item.line_total for item in items), Decimal('0')),
        'item_count': sum(item.quantity for item in items),
    }


def validate_quantity(product, quantity):
    if product.status != 'ACTIVE' or product.stock_quantity <= 0:
        raise ValidationError('Sản phẩm đã hết hàng hoặc tạm ngừng bán.')
    if quantity < 1 or quantity > product.stock_quantity:
        raise ValidationError('Số lượng trong giỏ không được vượt quá tồn kho.')


@transaction.atomic
def add_product(user, product_id, quantity):
    try:
        product = Product.objects.select_for_update().get(pk=product_id)
    except Product.DoesNotExist:
        raise ValidationError('Sản phẩm không còn tồn tại.')

    # Kiểm tra trạng thái hoạt động của shop
    if product.shop.status == 'PENDING':
        raise ValidationError('Shop hiện đang chờ xét duyệt và không thể bán sản phẩm. Vui lòng quay lại sau!')
    if product.shop.status == 'SUSPENDED':
        raise ValidationError('Shop hiện không kinh doanh trên hệ thống. Sản phẩm tạm thời không thể mua.')

    # Kiểm tra trạng thái của sản phẩm
    if product.status == 'INACTIVE':
        raise ValidationError('Sản phẩm hiện không được phép bán!')
    if product.status == 'OUT_OF_STOCK':
        raise ValidationError('Sản phẩm hiện hết hàng!')

    validate_quantity(product, quantity)
    cart, _ = Cart.objects.get_or_create(user=user)
    item = CartItem.objects.select_for_update().filter(cart=cart, product=product).first()
    total_quantity = quantity + (item.quantity if item else 0)
    validate_quantity(product, total_quantity)
    if item:
        item.quantity = total_quantity
        item.save(update_fields=['quantity'])
    else:
        item = CartItem.objects.create(cart=cart, product=product, quantity=quantity)
    cart.save(update_fields=['updated_at'])
    return item
