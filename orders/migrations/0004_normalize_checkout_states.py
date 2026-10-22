from django.db import migrations


def normalize(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    OrderItem = apps.get_model('orders', 'OrderItem')
    Payment = apps.get_model('payments', 'Payment')
    Order.objects.filter(payment_method='COD', payment_status='PENDING').update(payment_status='UNPAID')
    Payment.objects.filter(payment_method='COD', status='PENDING').update(status='UNPAID')
    Order.objects.filter(payment_method='VNPAY', payment_status='PENDING', order_status='PENDING').update(order_status='AWAITING_PAYMENT')
    # Legacy shop updates only changed the order, not its items.
    for order in Order.objects.all().iterator():
        OrderItem.objects.filter(order=order, item_status__in=['', 'PENDING']).update(item_status=order.order_status)


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0003_order_checkout_token_alter_order_order_status_and_more'),
        ('payments', '0002_payment_gateway_transaction_no_alter_payment_status'),
    ]
    operations = [migrations.RunPython(normalize, migrations.RunPython.noop)]
