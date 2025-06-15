from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator, MinValueValidator


class User(AbstractUser):
    ROLES = (
        ('admin', 'Администратор'),
        ('manager', 'Менеджер'),
        ('client', 'Клиент'),
    )
    role = models.CharField(max_length=10, choices=ROLES, default='client')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


def generate_sku():
    last_part = Product.objects.order_by('-id').first()
    return f"PART-{(last_part.id + 1) if last_part else 1}"

class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название')
    category = models.ForeignKey('Category', on_delete=models.CASCADE, verbose_name='Категория')
    description = models.TextField(verbose_name='Описание')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Розничная цена'
    )
    wholesale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Оптовая цена',
        blank=True,
        null=True
    )
    wholesale_threshold = models.IntegerField(
        default=10,
        verbose_name='Порог для опта',
        validators=[MinValueValidator(1)]
    )
    quantity = models.PositiveIntegerField(verbose_name='Количество на складе')
    sku = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Артикул',
        default=generate_sku
    )
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        verbose_name='Изображение'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def get_actual_price(self, quantity):
        if self.wholesale_price and quantity >= self.wholesale_threshold:
            return self.wholesale_price
        return self.price


class ProductDocument(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(
        upload_to='product_documents/',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'xls', 'xlsx', 'odt'])]
    )
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы товара'