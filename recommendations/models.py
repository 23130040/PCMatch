from django.db import models

class ProductRecommendation(models.Model):
    RECOMMENDATION_TYPE_CHOICES = [
        ('SIMILAR_PRODUCT', 'Similar Product'),
    ]

    recommendation_id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='recommendations')
    recommended_product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='recommendation_by')
    similarity_score = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True)
    recommendation_type = models.CharField(max_length=30, choices=RECOMMENDATION_TYPE_CHOICES, default='SIMILAR_PRODUCT')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'recommended_product'],
                name='unique_product_recommendation',
            )
        ]
    def __str__(self):
        return f"{self.product} -> {self.recommended_product}"

class FrequentItemset(models.Model):
    itemset_id = models.BigAutoField(primary_key=True)
    itemset_code = models.CharField(max_length=255)
    support = models.DecimalField(max_digits=10, decimal_places=6)
    item_count = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.itemset_code

class FrequentItemsetProduct(models.Model):
    itemset = models.ForeignKey(FrequentItemset, on_delete=models.CASCADE, related_name='itemset_products')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='frequent_itemsets')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields = ['itemset', 'product'],
                name = 'unique_product_frequent_itemset',
            )
        ]

    def __str__(self):
        return f"{self.itemset} | {self.product}"

class AssociationRule(models.Model):
    rule_id = models.BigAutoField(primary_key=True)
    antecedent_itemset = models.ForeignKey(FrequentItemset, on_delete=models.CASCADE, related_name='antecedent_itemsets')
    consequent_itemset = models.ForeignKey(FrequentItemset, on_delete=models.CASCADE, related_name='consequent_itemsets')
    support = models.DecimalField(max_digits=10, decimal_places=6)
    confidence = models.DecimalField(max_digits=10, decimal_places=6)
    lift = models.DecimalField(max_digits=10, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.antecedent_itemset} -> {self.consequent_itemset}"