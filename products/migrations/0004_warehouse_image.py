# Generated by Django 5.2.3 on 2025-06-15 14:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_warehouse_alter_category_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='warehouse',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='warehouses/', verbose_name='Изображение'),
        ),
    ]
