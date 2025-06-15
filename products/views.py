from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_POST

from .models import Product, Category, ProductDocument, generate_sku
from .forms import ProductForm, DocumentUploadForm, RegistrationForm, CategoryForm
from django.contrib.auth import login
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe


@login_required
def product_list(request):
    """Страница каталога с фильтрами и управлением товарами"""
    query = request.GET.get('q', '')
    category_id = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    show_all = request.GET.get('show_all', 'false') == 'true'

    # Базовый queryset
    products = Product.objects.select_related('category')
    
    # Если не админ или не запрошены все товары, показываем только доступные
    if not request.user.is_staff or not show_all:
        products = products.filter(quantity__gt=0)

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

    # Обработка действий с товарами (только для админов)
    if request.user.is_staff and request.method == 'POST':
        action = request.POST.get('action')
        product_id = request.POST.get('product_id')
        
        if action and product_id:
            product = get_object_or_404(Product, pk=product_id)
            
            if action == 'delete':
                product_name = product.name
                product.delete()
                messages.success(request, f'Товар "{product_name}" успешно удален!')
            elif action == 'toggle_visibility':
                product.is_active = not product.is_active
                product.save()
                status = 'активирован' if product.is_active else 'деактивирован'
                messages.success(request, f'Товар "{product.name}" {status}!')
            
            return redirect('product_list')

    categories = Category.objects.all()
    return render(request, 'products/list.html', {
        'products': products,
        'categories': categories,
        'search_query': query,
        'selected_category': int(category_id) if category_id else None,
        'show_all': show_all,
        'is_staff': request.user.is_staff,
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

    return render(request, 'products/detail.html', {
        'product': product,
        'documents': documents,
        'form': form,
    })



@login_required
def profile(request):
    """Личный кабинет пользователя"""
    return render(request, 'profile.html', {
        'user': request.user
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
                return redirect('product_list')
            except IntegrityError:
                messages.error(request, 'Товар с таким артикулом уже существует')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = ProductForm()

    return render(request, 'products/form.html', {
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
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'products/form.html', {
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
    return redirect('product_list')


# categories
@login_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'categories/list.html', {'categories': categories})

@user_passes_test(lambda u: u.is_staff)
def category_add(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'categories/form.html', {'form': form, 'title': 'Добавить категорию'})

@user_passes_test(lambda u: u.is_staff)
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'categories/form.html', {'form': form, 'title': 'Редактировать категорию'})

@user_passes_test(lambda u: u.is_staff)
def category_delete(request, pk):
    """Удаление категории"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        category_name = category.name
        try:
            category.delete()
            messages.success(request, f'Категория "{category_name}" успешно удалена!')
        except IntegrityError:
            messages.error(request, f'Невозможно удалить категорию "{category_name}", так как она используется в товарах.')
    
    return redirect('category_list')

