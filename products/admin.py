from django.contrib import admin

from .models import (
    Brand,
    Category,
    Product,
    ProductImage,
    ProductSpecification,
    ProductQuestion,
    ProductAnswer,
)

admin.site.register(Brand)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(ProductSpecification)
admin.site.register(ProductQuestion)
admin.site.register(ProductAnswer)