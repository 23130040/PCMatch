from django.conf import settings
from django.db import models

from shops.models import Shop

class Brand(models.Model):
    brand_id = models.BigAutoField(primary_key=True)
    brand_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='brand_logo/', blank=True)

    def __str__(self):
        return self.brand_name

class Category(models.Model):
    category_id = models.BigAutoField(primary_key=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    category_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.category_name

class Product(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('OUT_OF_STOCK', 'Out of stock'),
    ]

    product_id = models.BigAutoField(primary_key=True)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    product_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=15, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    sold_quantity = models.IntegerField(default=0)
    thumbnail = models.ImageField(upload_to='product_thumbnail/', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.product_name

class ProductImage(models.Model):
    image_id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image_url = models.ImageField(upload_to='product_images/')
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return str(self.image_url)


class ProductSpecification(models.Model):
    specification_id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    specification_name = models.CharField(max_length=100)
    specification_value = models.CharField(max_length=255)

    def __str__(self):
        return self.specification_name

class ProductQuestion(models.Model):
    question_id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='questions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_questions')
    question = models.TextField()
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question

class ProductAnswer(models.Model):
    answer_id = models.BigAutoField(primary_key=True)
    question = models.ForeignKey(ProductQuestion, on_delete=models.CASCADE, related_name='answers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_answers')
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.answer
