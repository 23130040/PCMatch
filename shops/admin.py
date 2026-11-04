from django.contrib import admin

from .models import Shop


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('shop_name', 'owner', 'status', 'phone', 'legal_submitted_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('shop_name', 'owner__email', 'owner__username', 'phone')
    actions = ('approve_shops', 'suspend_shops')

    @admin.action(description='Phê duyệt shop đã chọn')
    def approve_shops(self, request, queryset):
        # Saving each record individually lets Shop.save() detect the transition and notify the owner.
        blocked = []
        for shop in queryset:
            if not shop.is_ready_for_approval():
                blocked.append(shop.shop_name)
                continue
            shop.status = 'ACTIVE'
            shop.save()
        if blocked:
            self.message_user(
                request,
                'Không thể duyệt shop chưa xác thực email hoặc chưa nộp đủ giấy tờ: '
                + ', '.join(blocked),
                level='error',
            )

    @admin.action(description='Tạm ngưng shop đã chọn')
    def suspend_shops(self, request, queryset):
        queryset.update(status='SUSPENDED')
