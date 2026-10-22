from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q

from .models import ProductAnswer, ProductQuestion


def conversation_messages():
    return ProductAnswer.objects.filter(
        Q(is_shop_reply=False) | Q(is_shop_reply=True, user_id=F('question__product__shop__owner_id')),
    ).select_related('user').order_by('created_at', 'pk')


@transaction.atomic
def append_question_message(question_id, user, text, *, is_shop_reply):
    # Serialize messages so the inbox status follows the last committed reply.
    ProductQuestion.objects.filter(pk=question_id).update(status=F('status'))
    question = ProductQuestion.objects.select_for_update().select_related('product__shop').get(pk=question_id)
    shop = question.product.shop
    if not user.is_active or user.status != 'ACTIVE' or shop.status != 'ACTIVE':
        raise ValidationError('Hiện không thể gửi phản hồi trong cuộc trao đổi này.')
    if is_shop_reply:
        if user.pk != shop.owner_id or user.role != 'SELLER':
            raise ValidationError('Chỉ shop bán sản phẩm được gửi câu trả lời của người bán.')
    elif user.role not in {'BUYER', 'CUSTOMER'} or question.product.status == 'INACTIVE':
        raise ValidationError('Sản phẩm hiện không nhận câu hỏi mới từ tài khoản này.')
    message = ProductAnswer.objects.create(question=question, user=user, answer=text, is_shop_reply=is_shop_reply)
    question.status = is_shop_reply
    question.save(update_fields=['status'])
    return message
