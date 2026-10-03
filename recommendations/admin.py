from django.contrib import admin
from .models import (
    ProductRecommendation,
    FrequentItemset,
    FrequentItemsetProduct,
    AssociationRule,
)

admin.site.register(ProductRecommendation)
admin.site.register(FrequentItemset)
admin.site.register(FrequentItemsetProduct)
admin.site.register(AssociationRule)
