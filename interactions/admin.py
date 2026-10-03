from django.contrib import admin

from .models import (
    ProductView,
    UserProductInteraction,
)

admin.site.register(ProductView)
admin.site.register(UserProductInteraction)