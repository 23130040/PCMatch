from time import time
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from products.models import Product
from users.views import buyer_required, is_active_buyer
from .forms import CartQuantityForm
from .models import CartItem
from .services import add_product, cart_summary, validate_quantity
from interactions.models import UserProductInteraction

@buyer_required
def cart_detail(request):
    return render(request, 'buyer/cart.html', {
        'page_name': 'cart', 'page_section': 'buyer', **cart_summary(request.user),
    })



@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    form = CartQuantityForm(request.POST)

    if not form.is_valid():
        message = 'Vui lòng nhập số lượng nguyên lớn hơn 0.'
        error = True
    else:
        quantity = form.cleaned_data['quantity']

        try:
            validate_quantity(product, quantity)
        except ValidationError as exc:
            message = exc.messages[0]
            error = True
        else:
            if not is_active_buyer(request.user):
                request.session['pending_cart_add'] = {
                    'product_id': product_id,
                    'quantity': quantity,
                    'expires': time() + 900,
                }
                query = urlencode({
                    'next': reverse(
                        'buyer_product_detail',
                        args=[product_id]
                    )
                })
                return redirect(reverse('auth_login') + '?' + query)

            try:
                add_product(request.user, product_id, quantity)

                UserProductInteraction.objects.create(
                    user=request.user,
                    product=product,
                    interacted_type='CART',
                    quantity=quantity,
                )

                message = 'Đã thêm sản phẩm vào giỏ hàng thành công!'
                error = False

            except ValidationError as exc:
                message = exc.messages[0]
                error = True

    if request.headers.get('Accept') == 'application/json':
        return JsonResponse(
            {'message': message},
            status=400 if error else 200,
        )

    if error:
        messages.error(request, message)
    else:
        messages.success(request, message)

    return redirect(
        'buyer_product_detail',
        product_id=product_id
    )


@require_POST
@buyer_required
@transaction.atomic
def cart_update(request, item_id):
    owned = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    product = Product.objects.select_for_update().get(pk=owned.product_id)
    item = get_object_or_404(CartItem.objects.select_for_update(), pk=item_id, cart__user=request.user)
    form = CartQuantityForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Vui lòng nhập số lượng nguyên lớn hơn 0.')
    else:
        try:
            validate_quantity(product, form.cleaned_data['quantity'])
            item.quantity = form.cleaned_data['quantity']
            item.save(update_fields=['quantity'])
            item.cart.save(update_fields=['updated_at'])
            messages.success(request, 'Đã cập nhật số lượng.')
        except ValidationError as error:
            messages.error(request, error.messages[0])
    return redirect('buyer_cart')


@require_POST
@buyer_required
def cart_remove(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    cart = item.cart
    item.delete()
    cart.save(update_fields=['updated_at'])
    messages.success(request, 'Đã xóa sản phẩm khỏi giỏ hàng.')
    return redirect('buyer_cart')

@require_GET
@buyer_required
def cart_checkout(request):
    from orders.services import checkout_token
    from payments.vnpay import configured
    address = request.user.addresses.filter(is_archived=False).order_by('-is_default', 'pk').first()
    return render(request, 'buyer/checkout.html', {
        'page_name': 'checkout', 'page_section': 'buyer',
        'checkout_user': request.user, 'shipping_address': address,
        'checkout_token': checkout_token(request.user),
        'vnpay_ready': configured(),
        **cart_summary(request.user),
    })
