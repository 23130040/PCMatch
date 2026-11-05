from django.core.management.base import BaseCommand

from orders.services import process_order_timeouts


class Command(BaseCommand):
    help = 'Expire unconfirmed shop orders, escalate cancellation requests, and complete delivered orders.'

    def handle(self, *args, **options):
        counts = process_order_timeouts()
        self.stdout.write(
            self.style.SUCCESS(
                'Processed order deadlines: '
                f'{counts["shop_orders"]} shop orders, '
                f'{counts["cancellation_requests"]} cancellation requests, '
                f'{counts["delivered_shop_orders"]} delivered orders.'
            )
        )
