from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Category, Part, PartDocument, Order, OrderItem

class PartDocumentInline(admin.TabularInline):
    model = PartDocument
    extra = 1

class OrderItemInline(admin.TabularInline):
    model = OrderItem
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

@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'wholesale_price', 'quantity', 'min_order')
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
            'fields': ('quantity', 'min_order', 'sku')
        }),
    )
    list_editable = ('price', 'wholesale_price', 'quantity')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'notes')
    inlines = [OrderItemInline]

admin.site.register(PartDocument)
admin.site.register(OrderItem)