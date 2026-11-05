from django.db import migrations


def move_admin_catalog_to_seller(apps, schema_editor):
    Shop = apps.get_model('shops', 'Shop')
    Product = apps.get_model('products', 'Product')
    OrderItem = apps.get_model('orders', 'OrderItem')
    ShopOrder = apps.get_model('orders', 'ShopOrder')
    User = apps.get_model('users', 'User')

    source_shops = list(
        Shop.objects.filter(
            shop_name__iexact='admin',
            owner__username__iexact='admin',
        ).select_related('owner')
    )
    if not source_shops:
        return
    if len(source_shops) != 1:
        raise RuntimeError('Không thể tự động chuyển dữ liệu: có nhiều shop admin.')

    source = source_shops[0]
    if not (source.owner.is_staff or source.owner.role == 'ADMIN'):
        raise RuntimeError(
            'Không thể tự động chuyển dữ liệu: tài khoản sở hữu shop admin '
            'không được xác định là quản trị nền tảng.'
        )

    target_shops = list(
        Shop.objects.filter(
            shop_name__iexact='titanshop',
            status='ACTIVE',
            owner__role='SELLER',
            owner__is_staff=False,
            owner__is_superuser=False,
        )
    )
    if len(target_shops) != 1:
        raise RuntimeError(
            'Không thể chuyển sản phẩm khỏi shop admin: cần đúng một shop '
            'seller đang hoạt động tên titanshop.'
        )
    target = target_shops[0]

    source_orders = ShopOrder.objects.filter(shop_id=source.pk).values('order_id')
    if ShopOrder.objects.filter(shop_id=target.pk, order_id__in=source_orders).exists():
        raise RuntimeError(
            'Không thể tự động chuyển đơn: đã có đơn đồng thời thuộc shop admin '
            'và titanshop.'
        )

    Product.objects.filter(shop_id=source.pk).update(shop_id=target.pk)
    OrderItem.objects.filter(shop_id=source.pk).update(shop_id=target.pk)
    ShopOrder.objects.filter(shop_id=source.pk).update(shop_id=target.pk)
    if source.owner.role == 'SELLER':
        User.objects.filter(pk=source.owner_id).update(role='ADMIN')
    source.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0005_alter_order_order_status_and_more'),
        ('products', '0006_productreviewimage'),
        ('shops', '0005_shop_contact_email_verified_and_more'),
        ('users', '0006_emailverificationsend_and_more'),
    ]

    operations = [
        migrations.RunPython(move_admin_catalog_to_seller),
    ]
