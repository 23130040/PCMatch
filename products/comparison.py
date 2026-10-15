from .models import Product


SESSION_KEY = 'product_comparison'


def parse_product_ids(values):
    ids = []
    for value in ','.join(str(value) for value in values[:4])[:100].split(','):
        if value.isascii() and value.isdigit() and len(value) <= 18:
            product_id = int(value)
            if product_id not in ids:
                ids.append(product_id)
        if len(ids) == 4:
            break
    return ids


def comparison_products(ids):
    found = {
        product.pk: product for product in Product.objects.filter(pk__in=ids)
        .select_related('category', 'brand', 'shop').prefetch_related('specifications')
    }
    return [found[product_id] for product_id in ids if product_id in found]


def session_products(request):
    return comparison_products(parse_product_ids(request.session.get(SESSION_KEY, [])))
