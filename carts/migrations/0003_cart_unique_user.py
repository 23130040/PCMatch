from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('carts', '0002_initial')]

    operations = [
        migrations.AddConstraint(
            model_name='cart',
            constraint=models.UniqueConstraint(fields=['user'], name='unique_user_cart'),
        ),
    ]
