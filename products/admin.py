from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Category, Product, ProductDocument

class ProductDocumentInline(admin.TabularInline):
    model = ProductDocument
    extra = 1

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('role', 'phone', 'address')}),
    )

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'wholesale_price', 'quantity')
    list_filter = ('category',)
    search_fields = ('name', 'sku', 'description')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'category', 'description', 'image')
        }),
        ('Ценообразование', {
            'fields': ('price', 'wholesale_price', 'wholesale_threshold')
        }),
        ('Инвентаризация', {
            'fields': ('quantity', 'sku')
        }),
    )
    list_editable = ('price', 'wholesale_price', 'quantity')

admin.site.register(ProductDocument)