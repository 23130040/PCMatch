from decimal import Decimal, ROUND_HALF_UP

from django import template

register = template.Library()


@register.filter
def vnd(value):
    amount = Decimal(value).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return format(amount, ',.0f').replace(',', '.')
