from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_POST

from .models import Product, Category, Order, ProductDocument, OrderItem, generate_sku
from .forms import ProductForm, DocumentUploadForm, OrderForm, RegistrationForm, OrderStatusForm
from django.contrib.auth import login
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe


@login_required
def catalog(request):
    """Страница каталога с фильтрами"""
    query = request.GET.get('q', '')
    category_id = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    products = Product.objects.filter(quantity__gt=0)

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(sku__icontains=query)
        )

    if category_id:
        products = products.filter(category_id=category_id)

    if min_price:
        products = products.filter(price__gte=float(min_price))

    if max_price:
        products = products.filter(price__lte=float(max_price))

    categories = Category.objects.all()
    return render(request, 'catalog.html', {
        'products': products,
        'categories': categories,
        'search_query': query,
        'selected_category': int(category_id) if category_id else None,
    })

@login_required
def product_detail(request, pk):
    """Детальная страница товара"""
    product = get_object_or_404(Product.objects.prefetch_related('documents'), pk=pk)
    documents = product.documents.all()

    if request.method == 'POST' and request.user.is_authenticated:
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.product = product
            document.uploaded_by = request.user
            document.save()
            messages.success(request, 'Файл успешно загружен.')
            return redirect('product_detail', pk=pk)
    else:
        form = DocumentUploadForm()

    return render(request, 'product_detail.html', {
        'product': product,
        'documents': documents,
        'form': form,
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'Статус заказа #{order.id} изменен на "{order.get_status_display()}"')

    return redirect(request.META.get('HTTP_REFERER', 'order_management'))


@login_required
def profile(request):
    """Личный кабинет пользователя"""
    orders = Order.objects.filter(user=request.user).select_related(
        'user'
    ).prefetch_related(
        'orderitem_set__product'
    ).order_by('-created_at')

    return render(request, 'profile.html', {
        'orders': orders,
        'user': request.user
    })


@login_required
def create_order(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    if request.method == 'POST':
        form = OrderForm(request.POST, product=product)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            price = product.get_actual_price(quantity)

            order = Order.objects.create(
                user=request.user,
                notes=form.cleaned_data['notes'],
                status='pending'
            )
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=price
            )

            product.quantity -= quantity
            product.save()

            success_message = format_html(
                '<h4 class="alert-heading">Заказ оформлен!</h4>'
                '<p>Товар: <strong>{}</strong> × {} шт.</p>'
                '<p>Цена за единицу: {} ₽</p>'
                '<p>Общая сумма: <strong>{} ₽</strong></p>'
                '<hr>'
                '<p>Номер заказа: <strong>#{}</strong></p>',
                product.name,
                quantity,
                price,
                price * quantity,
                order.id
            )
            messages.success(request, success_message)
            return redirect('order_detail', order_id=order.id)
    else:
        form = OrderForm(product=product)

    return render(request, 'create_order.html', {
        'product': product,
        'form': form,
        'title': 'Оформление заказа'
    })

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('orderitem_set__product'),
                            id=order_id,
                            user=request.user)
    return render(request, 'order_detail.html', {
        'order': order,
        'title': f'Заказ #{order.id}'
    })


def register(request):
    """Регистрация нового пользователя"""
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'client'
            user.save()

            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('profile')
    else:
        form = RegistrationForm()

    return render(request, 'registration/register.html', {
        'form': form,
    })


# Административные представления
@user_passes_test(lambda u: u.is_staff)
def product_management(request):
    """Управление товарами (админка)"""
    products = Product.objects.select_related('category').all()
    return render(request, 'manage/product_management.html', {
        'products': products,
    })


@user_passes_test(lambda u: u.is_staff)
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)

            # Дополнительная проверка SKU
            if not product.sku:
                product.sku = generate_sku()

            try:
                product.save()
                messages.success(request, f'Товар "{product.name}" успешно сохранен! SKU: {product.sku}')
                return redirect('product_management')
            except IntegrityError:
                messages.error(request, 'Товар с таким артикулом уже существует')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = ProductForm()

    return render(request, 'manage/add_product.html', {
        'form': form,
        'title': 'Добавление товара'
    })


@user_passes_test(lambda u: u.is_staff)
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Товар "{product.name}" успешно обновлен!')
            return redirect('product_management')
    else:
        form = ProductForm(instance=product)

    return render(request, 'manage/add_product.html', {
        'form': form,
        'title': f'Редактирование {product.name}',
        'edit_mode': True
    })

@require_POST
@user_passes_test(lambda u: u.is_staff)
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product_name = product.name
    product.delete()
    messages.success(request, f'Товар "{product_name}" успешно удален!')
    return redirect('product_management')