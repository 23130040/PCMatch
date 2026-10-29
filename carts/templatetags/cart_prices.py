from decimal import Decimal, ROUND_HALF_UP

from django import template

register = template.Library()


@register.filter
def vnd(value):
    amount = Decimal(value).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return format(amount, ',.0f').replace(',', '.')


@register.filter
def compact_vnd(value):
    amount = Decimal(value)
    absolute_amount = abs(amount)
    if absolute_amount >= Decimal('1000000000'):
        compact_amount, suffix = amount / Decimal('1000000000'), 'tỷ'
    elif absolute_amount >= Decimal('1000000'):
        compact_amount, suffix = amount / Decimal('1000000'), 'triệu'
    else:
        return vnd(amount)
    return f'{compact_amount.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)}'.replace('.', ',') + f' {suffix}'
