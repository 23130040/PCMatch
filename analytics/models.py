from django.db import models

class SalesStatistic(models.Model):
    statistic_id = models.BigAutoField(primary_key=True)
    statistic_date = models.DateField()
    product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_statistics')
    shop = models.ForeignKey('shops.Shop', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_statistics')
    total_quantity = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_orders = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.statistic_date} | Revenue: {self.total_revenue}"