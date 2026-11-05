
import math
import re

from collections import defaultdict
from decimal import Decimal
from carts.models import CartItem
from orders.models import OrderItem
from products.models import Product
from orders.models import Order
from itertools import combinations
from math import ceil
from django.db import transaction
from interactions.models import (
    ProductView,
    UserProductInteraction,
    FilterHistory,
)
from .models import (
    FrequentItemset,
    FrequentItemsetProduct,
    AssociationRule,
)

PRICE_UNIT = Decimal("1000000")

def normalize(text):
    return " ".join(re.findall(r"[^\W_]+", str(text).lower()))

def product_features(product):

    features = defaultdict(float)

    features[f"category:{product.category_id}"] += 3.0

    if product.brand_id:
        features[f"brand:{product.brand_id}"] += 2.0

    price_band = int(product.price // PRICE_UNIT)
    features[f"price:{price_band}"] += 0.8

    for word in normalize(product.product_name).split():
        if len(word) > 1:
            features[f"word:{word}"] += 0.3

    for spec in product.specifications.all():
        name = normalize(spec.specification_name)
        value = normalize(spec.specification_value)

        if name and value:
            features[f"spec:{name}:{value}"] += 1.5

    return dict(features)


def add_features(profile, features, weight):
    for feature, value in features.items():
        profile[feature] += value * weight


def add_price_preferences(profile, min_price, max_price):

    try:
        low = Decimal(str(min_price)) if min_price else None
        high = Decimal(str(max_price)) if max_price else None
    except Exception:
        return

    if low is None and high is None:
        return

    if low is not None and high is not None:
        start = int(low // PRICE_UNIT)
        end = int(high // PRICE_UNIT)
    elif low is not None:
        start = int(low // PRICE_UNIT)
        end = start + 2
    else:
        end = int(high // PRICE_UNIT)
        start = max(0, end - 2)

    end = min(end, start + 20)

    for band in range(max(0, start), max(0, end) + 1):
        profile[f"price:{band}"] += 1.0


def add_filter_preferences(profile, filters):
    category_id = filters.get("category")
    if category_id:
        profile[f"category:{category_id}"] += 2.0

    brand_id = filters.get("brand")
    if brand_id:
        profile[f"brand:{brand_id}"] += 2.0

    add_price_preferences(
        profile,
        filters.get("min"),
        filters.get("max"),
    )

    for word in normalize(filters.get("q", "")).split():
        if len(word) > 1:
            profile[f"word:{word}"] += 0.5

    for name, value in filters.get("technical", {}).items():
        name = normalize(name)
        value = normalize(value)

        if name and value:
            profile[f"spec:{name}:{value}"] += 2.0


def cosine_similarity(vector_a, vector_b):
    if not vector_a or not vector_b:
        return 0.0

    common_features = vector_a.keys() & vector_b.keys()

    dot_product = sum(
        vector_a[key] * vector_b[key]
        for key in common_features
    )

    norm_a = math.sqrt(sum(value ** 2 for value in vector_a.values()))
    norm_b = math.sqrt(sum(value ** 2 for value in vector_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def get_recommended_products(user, limit=8):

    if not user.is_authenticated:
        return []

    candidates = list(
        Product.objects.filter(
            status="ACTIVE",
            stock_quantity__gt=0,
            shop__status="ACTIVE",
        )
        .select_related("category", "brand", "shop")
        .prefetch_related("specifications")
    )

    if not candidates:
        return []

    profile = defaultdict(float)
    feature_cache = {}

    def get_features(product):
        if product.pk not in feature_cache:
            feature_cache[product.pk] = product_features(product)
        return feature_cache[product.pk]

    def learn_from_product(product, weight):
        add_features(profile, get_features(product), weight)

    views = (
        ProductView.objects
        .filter(user=user)
        .select_related("product__category", "product__brand")
        .prefetch_related("product__specifications")
        .order_by("-viewed_at")[:100]
    )

    for view in views:
        learn_from_product(view.product, 1.0)

    purchases = (
        OrderItem.objects
        .filter(
            order__user=user,
            order__order_status="DELIVERED",
        )
        .select_related("product__category", "product__brand")
        .prefetch_related("product__specifications")
        .order_by("-order__created_at")[:50]
    )

    purchased_ids = set()

    for item in purchases:
        purchased_ids.add(item.product_id)
        learn_from_product(item.product, 4.0)

    cart_events = (
        UserProductInteraction.objects
        .filter(user=user, interacted_type="CART")
        .select_related("product__category", "product__brand")
        .prefetch_related("product__specifications")
        .order_by("-created_at")[:50]
    )

    for event in cart_events:
        learn_from_product(event.product, 2.5)

    current_cart = (
        CartItem.objects
        .filter(cart__user=user)
        .select_related("product__category", "product__brand")
        .prefetch_related("product__specifications")
    )

    cart_product_ids = set()

    for item in current_cart:
        cart_product_ids.add(item.product_id)
        learn_from_product(item.product, 3.0)

    filter_histories = FilterHistory.objects.filter(
        user=user
    ).order_by("-created_at")[:10]

    for history in filter_histories:
        add_filter_preferences(profile, history.filters)

    if not profile:
        return candidates and list(
            Product.objects.filter(
                status="ACTIVE",
                stock_quantity__gt=0,
                shop__status="ACTIVE",
            )
            .select_related("category", "brand", "shop")
            .order_by("-sold_quantity", "-created_at")[:limit]
        ) or []

    excluded_ids = purchased_ids | cart_product_ids

    scored_products = []

    for product in candidates:
        if product.pk in excluded_ids:
            continue

        score = cosine_similarity(
            profile,
            get_features(product),
        )

        if score > 0:
            scored_products.append((score, product))

    scored_products.sort(
        key=lambda item: (
            item[0],
            item[1].sold_quantity,
            item[1].created_at,
        ),
        reverse=True,
    )

    recommendations = [
        product for score, product in scored_products[:limit]
    ]

    if len(recommendations) < limit:
        selected_ids = {
            product.pk for product in recommendations
        } | excluded_ids

        fallback_products = (
            Product.objects.filter(
                status="ACTIVE",
                stock_quantity__gt=0,
                shop__status="ACTIVE",
            )
            .exclude(pk__in=selected_ids)
            .select_related("category", "brand", "shop")
            .order_by("-sold_quantity", "-created_at")[:limit]
        )

        recommendations.extend(
            list(fallback_products)[:limit - len(recommendations)]
        )

    return recommendations


from collections import defaultdict
from itertools import combinations
from math import ceil

from django.db import transaction

from orders.models import Order
from products.models import Product
from .models import (
    FrequentItemset,
    FrequentItemsetProduct,
    AssociationRule,
)


def apriori(min_support=0.02, min_confidence=0.10):

    orders = (
        Order.objects
        .filter(order_status="DELIVERED")
        .prefetch_related("order_items")
    )

    transactions = []

    for order in orders:
        product_ids = {
            item.product_id
            for item in order.order_items.all()
        }

        if product_ids:
            transactions.append(product_ids)

    total_transactions = len(transactions)

    if total_transactions == 0:
        return {
            "transactions": 0,
            "frequent_itemsets": 0,
            "rules": 0,
            "message": "Chưa có đơn hàng hoàn thành để học.",
        }

    min_count = max(
        2,
        ceil(min_support * total_transactions),
    )

    item_counts = defaultdict(int)

    for basket in transactions:
        for product_id in basket:
            item_counts[frozenset([product_id])] += 1

    frequent_levels = {
        itemset: count
        for itemset, count in item_counts.items()
        if count >= min_count
    }

    all_frequent = dict(frequent_levels)

    pair_counts = defaultdict(int)

    for basket in transactions:

        eligible = sorted(
            product_id
            for product_id in basket
            if frozenset([product_id]) in frequent_levels
        )

        for product_a, product_b in combinations(eligible, 2):
            pair_counts[frozenset([product_a, product_b])] += 1

    frequent_pairs = {
        itemset: count
        for itemset, count in pair_counts.items()
        if count >= min_count
    }

    all_frequent.update(frequent_pairs)

    supports = {
        itemset: count / total_transactions
        for itemset, count in all_frequent.items()
    }

    with transaction.atomic():
        AssociationRule.objects.all().delete()
        FrequentItemsetProduct.objects.all().delete()
        FrequentItemset.objects.all().delete()

        saved_itemsets = {}

        for itemset, support in supports.items():
            product_ids = sorted(itemset)

            db_itemset = FrequentItemset.objects.create(
                itemset_code=",".join(map(str, product_ids)),
                support=round(support, 6),
                item_count=len(product_ids),
            )

            FrequentItemsetProduct.objects.bulk_create([
                FrequentItemsetProduct(
                    itemset=db_itemset,
                    product_id=product_id,
                )
                for product_id in product_ids
            ])

            saved_itemsets[itemset] = db_itemset

        rules_created = 0

        for pair, pair_support in supports.items():
            if len(pair) != 2:
                continue

            product_a, product_b = sorted(pair)

            support_a = supports.get(frozenset([product_a]), 0)
            support_b = supports.get(frozenset([product_b]), 0)

            if support_a == 0 or support_b == 0:
                continue

            confidence_a_b = pair_support / support_a
            lift_a_b = confidence_a_b / support_b

            confidence_b_a = pair_support / support_b
            lift_b_a = confidence_b_a / support_a

            rules_to_save = [
                (
                    product_a,
                    product_b,
                    confidence_a_b,
                    lift_a_b,
                ),
                (
                    product_b,
                    product_a,
                    confidence_b_a,
                    lift_b_a,
                ),
            ]

            for antecedent, consequent, confidence, lift in rules_to_save:
                if confidence < min_confidence or lift <= 1:
                    continue

                AssociationRule.objects.create(
                    antecedent_itemset=saved_itemsets[
                        frozenset([antecedent])
                    ],
                    consequent_itemset=saved_itemsets[
                        frozenset([consequent])
                    ],
                    support=round(pair_support, 6),
                    confidence=round(confidence, 6),
                    lift=round(lift, 6),
                )

                rules_created += 1

    return {
        "transactions": total_transactions,
        "frequent_itemsets": len(all_frequent),
        "rules": rules_created,
        "message": "Đã huấn luyện Apriori thành công.",
    }


def get_frequently_bought_together(product_id, limit=4):

    rules = (
        AssociationRule.objects
        .filter(
            antecedent_itemset__itemset_products__product_id=product_id,
            antecedent_itemset__item_count=1,
            consequent_itemset__item_count=1,
        )
        .select_related(
            "antecedent_itemset",
            "consequent_itemset",
        )
        .order_by("-lift", "-confidence")
    )

    recommended = []
    seen_ids = {product_id}

    for rule in rules:
        itemset_product = (
            rule.consequent_itemset.itemset_products
            .select_related("product", "product__shop", "product__category")
            .prefetch_related("product__specifications")
            .filter(
                product__status="ACTIVE",
                product__stock_quantity__gt=0,
                product__shop__status="ACTIVE",
            )
            .first()
        )

        if itemset_product is None:
            continue

        product = itemset_product.product

        if product.pk in seen_ids:
            continue

        seen_ids.add(product.pk)
        recommended.append(product)

        if len(recommended) >= limit:
            break

    return recommended
