from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string


class User(AbstractUser):
    ROLES = (
        ('admin', 'Администратор'),
        ('manager', 'Менеджер'),
        ('client', 'Клиент'),
    )
    role = models.CharField(max_length=10, choices=ROLES, default='client')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)


class Warehouse(models.Model):
    """Модель склада"""
    name = models.CharField('Название', max_length=100)
    address = models.CharField('Адрес', max_length=200)
    description = models.TextField('Описание', blank=True)
    image = models.ImageField('Изображение', upload_to='warehouses/', blank=True, null=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Склад'
        verbose_name_plural = 'Склады'
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        # Проверка на уникальность названия склада
        if Warehouse.objects.filter(name=self.name).exclude(pk=self.pk).exists():
            raise ValidationError({'name': 'Склад с таким названием уже существует'})


class UserProfile(models.Model):
    """Профиль пользователя"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name='Склад', related_name='employees')
    
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.warehouse.name if self.warehouse else 'Нет склада'}"


class Category(models.Model):
    """Модель категории товаров"""
    name = models.CharField('Название', max_length=100)
    description = models.TextField('Описание', blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        if Category.objects.filter(name=self.name).exclude(pk=self.pk).exists():
            raise ValidationError({'name': 'Категория с таким названием уже существует'})


def generate_sku():
    """Генерация уникального артикула"""
    while True:
        sku = f"SKU-{get_random_string(8).upper()}"
        if not Product.objects.filter(sku=sku).exists():
            return sku


class Product(models.Model):
    """Модель товара"""
    name = models.CharField('Название', max_length=200)
    sku = models.CharField('Артикул', max_length=50, unique=True, blank=True)
    description = models.TextField('Описание', blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='Категория')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, verbose_name='Склад', null=True, blank=True)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField('Количество', default=0)
    image = models.ImageField('Изображение', upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Создал', null=True, blank=True)
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']
        permissions = [
            ("can_manage_warehouse_products", "Может управлять товарами склада"),
        ]

    def __str__(self):
        return f"{self.name} ({self.warehouse.name})"

    def clean(self):
        # Проверка на уникальность артикула в рамках склада
        if Product.objects.filter(sku=self.sku, warehouse=self.warehouse).exclude(pk=self.pk).exists():
            raise ValidationError({'sku': 'Товар с таким артикулом уже существует на этом складе'})

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = generate_sku()
        super().save(*args, **kwargs)


class ProductDocument(models.Model):
    """Модель документа товара"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField('Файл', upload_to='product_documents/')
    name = models.CharField('Название', max_length=200, null=True, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    uploaded_at = models.DateTimeField('Дата загрузки', auto_now_add=True)

    class Meta:
        verbose_name = 'Документ товара'
        verbose_name_plural = 'Документы товаров'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.name} - {self.product.name}"