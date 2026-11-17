from django.contrib import admin

from .models import Payment, Wallet, WalletTransaction

admin.site.register(Payment)
admin.site.register(Wallet)
admin.site.register(WalletTransaction)