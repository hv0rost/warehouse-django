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
    last_part = Part.objects.order_by('-id').first()
    return f"PART-{(last_part.id + 1) if last_part else 1}"

class Part(models.Model):
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
    min_order = models.PositiveIntegerField(
        default=1,
        verbose_name='Минимальный заказ',
        validators=[MinValueValidator(1)]
    )
    sku = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Артикул',
        default=generate_sku  # Автогенерация по умолчанию
    )
    image = models.ImageField(
        upload_to='parts/',
        blank=True,
        null=True,
        verbose_name='Изображение'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Запчасть'
        verbose_name_plural = 'Запчасти'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def get_actual_price(self, quantity):
        if self.wholesale_price and quantity >= self.wholesale_threshold:
            return self.wholesale_price
        return self.price


class PartDocument(models.Model):
    part = models.ForeignKey(Part, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(
        upload_to='part_documents/',
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'xls', 'xlsx', 'odt'])]
    )
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы заказа'


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'В обработке'),
        ('processing', 'В процессе'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parts = models.ManyToManyField(Part, through='OrderItem')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at'] # Сортировка по дате (новые сначала)

    def __str__(self):
        return f"Заказ #{self.id} ({self.user.username})"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.orderitem_set.all())

    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    @property
    def get_status_class(self):
        status_classes = {
            'pending': 'warning',
            'processing': 'info',
            'completed': 'success',
            'cancelled': 'danger'
        }
        return status_classes.get(self.status, 'secondary')


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказов'

    @property
    def total_price(self):
        return self.price * self.quantity