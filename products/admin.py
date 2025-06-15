from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Product, Category, ProductDocument, Warehouse, UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Профиль пользователя'

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'get_warehouse')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'role', ('profile__warehouse', admin.RelatedFieldListFilter))
    search_fields = ('username', 'first_name', 'last_name', 'email', 'userprofile__warehouse__name')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'email', 'phone', 'address')}),
        ('Роли и разрешения', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )

    def get_warehouse(self, obj):
        return obj.userprofile.warehouse.name if hasattr(obj, 'userprofile') and obj.userprofile.warehouse else '-'
    get_warehouse.short_description = 'Склад'

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'get_employee_count', 'created_at')
    search_fields = ('name', 'address')
    readonly_fields = ('created_at',)

    def get_employee_count(self, obj):
        return obj.userprofile_set.count()
    get_employee_count.short_description = 'Количество сотрудников'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_product_count', 'description')
    search_fields = ('name', 'description')

    def get_product_count(self, obj):
        return obj.product_set.count()
    get_product_count.short_description = 'Количество товаров'

class ProductDocumentInline(admin.TabularInline):
    model = ProductDocument
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'warehouse', 'price', 'quantity', 'is_active', 'created_by')
    list_filter = ('category', 'warehouse', 'is_active', 'created_at')
    search_fields = ('name', 'sku', 'description')
    readonly_fields = ('created_at', 'created_by')
    inlines = [ProductDocumentInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'sku', 'description', 'category', 'warehouse')
        }),
        ('Цена и наличие', {
            'fields': ('price', 'quantity', 'is_active')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Если это создание нового объекта
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(ProductDocument)
class ProductDocumentAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('product__name', 'name')
    readonly_fields = ('uploaded_at',)

# Просто регистрируем User с кастомным UserAdmin
admin.site.register(User, UserAdmin)