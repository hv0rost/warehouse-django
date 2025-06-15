from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied

from .models import Product, Category, ProductDocument, Warehouse, generate_sku
from .forms import ProductForm, DocumentUploadForm, RegistrationForm, CategoryForm, WarehouseForm
from django.contrib.auth import login
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe


@login_required
def product_list(request):
    """Страница каталога с фильтрами и управлением товарами"""
    query = request.GET.get('q', '').strip()  # Убираем лишние пробелы
    category_id = request.GET.get('category')
    warehouse_id = request.GET.get('warehouse')



    # Базовый queryset
    products = Product.objects.select_related('category', 'warehouse')
    
    # Для отладки - выведем все товары до фильтрации
    all_products = list(Product.objects.all())


    # Фильтрация по складу
    if warehouse_id:
        products = products.filter(warehouse_id=warehouse_id)
    elif not request.user.is_staff and hasattr(request.user, 'profile') and request.user.profile.warehouse:
        products = products.filter(warehouse=request.user.profile.warehouse)

    if query:
        
        # Поиск по отдельным полям для отладки
        name_results = list(Product.objects.filter(name__icontains=query))
        desc_results = list(Product.objects.filter(description__icontains=query))
        sku_results = list(Product.objects.filter(sku__icontains=query))
        cat_results = list(Product.objects.filter(category__name__icontains=query))
        warehouse_results = list(Product.objects.filter(warehouse__name__icontains=query))


        # Разбиваем поисковый запрос на слова
        search_terms = query.split()
        
        # Создаем пустой Q объект
        search_query = Q()
        # Для каждого слова добавляем условия поиска
        for term in search_terms:
            term_query = (
                Q(name__icontains=term) |
                Q(description__icontains=term) |
                Q(sku__icontains=term) |
                Q(category__name__icontains=term) |
                Q(warehouse__name__icontains=term)
            )
            search_query |= term_query
            print(f"\nПоиск по термину '{term}':")
            print(f"SQL: {term_query}")
            term_results = list(Product.objects.filter(term_query))
            print(f"Найдено: {[p.name for p in term_results]}")
        
        products = products.filter(search_query)
        
        print(f"\nИтоговый SQL запрос: {products.query}")
        print(f"Найдено товаров: {products.count()}")
        print("Найденные товары:")
        for p in products:
            print(f"- {p.name} (категория: {p.category.name}, склад: {p.warehouse.name})")
    
    print("\n=== Конец обработки запроса ===")

    if category_id:
        products = products.filter(category_id=category_id)

    # Обработка действий с товарами (только для админов и менеджеров склада)
    if request.method == 'POST':
        action = request.POST.get('action')
        product_id = request.POST.get('product_id')
        
        if action and product_id:
            product = get_object_or_404(Product, pk=product_id)
            
            # Проверка прав на управление товаром
            can_manage = (
                request.user.is_staff or  # Админ может управлять всеми товарами
                (hasattr(request.user, 'profile') and  # Менеджер может управлять только товарами своего склада
                 request.user.profile.warehouse == product.warehouse)
            )
            
            if not can_manage:
                raise PermissionDenied
            
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
    warehouses = Warehouse.objects.all() if request.user.is_staff else None

    return render(request, 'products/list.html', {
        'products': products,
        'categories': categories,
        'warehouses': warehouses,
        'search_query': query,
        'selected_category': int(category_id) if category_id else None,
        'selected_warehouse': int(warehouse_id) if warehouse_id else None,
        'is_staff': request.user.is_staff,
    })

@login_required
def product_detail(request, pk):
    """Детальная страница товара"""
    product = get_object_or_404(Product.objects.prefetch_related('documents'), pk=pk)
    
    # Проверка прав на просмотр товара
    can_view = (
        request.user.is_staff or  # Админ может просматривать все товары
        product.is_active or  # Активные товары видны всем
        (hasattr(request.user, 'profile') and  # Менеджер может просматривать товары своего склада
         request.user.profile.warehouse == product.warehouse)
    )
    
    if not can_view:
        raise PermissionDenied

    documents = product.documents.all()

    if request.method == 'POST' and request.user.is_authenticated:
        form = DocumentUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            document = form.save(commit=False)
            document.product = product
            document.save()
            messages.success(request, 'Файл успешно загружен.')
            return redirect('product_detail', pk=pk)
    else:
        form = DocumentUploadForm(user=request.user)

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
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('profile')
    else:
        form = RegistrationForm()

    return render(request, 'registration/register.html', {
        'form': form,
    })


# Административные представления
@login_required
def add_product(request):
    """Добавление нового товара"""
    # Проверяем права доступа
    if not (request.user.is_staff or request.user.role == 'manager'):
        raise PermissionDenied("У вас нет прав на добавление товаров")

    # Получаем предустановленный склад из GET-параметра
    initial_warehouse = None
    warehouse_id = request.GET.get('warehouse')
    if warehouse_id:
        initial_warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
        # Проверяем, что менеджер может добавлять товары только на свой склад
        if request.user.role == 'manager' and request.user.profile.warehouse != initial_warehouse:
            raise PermissionDenied("Вы можете добавлять товары только на свой склад")

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, user=request.user, initial_warehouse=initial_warehouse)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            try:
                product.save()
                messages.success(request, f'Товар "{product.name}" успешно сохранен! SKU: {product.sku}')
                # Если товар был создан со страницы склада, возвращаемся на страницу склада
                if warehouse_id:
                    return redirect('warehouse_detail', pk=warehouse_id)
                return redirect('product_list')
            except IntegrityError:
                messages.error(request, 'Товар с таким артикулом уже существует')
    else:
        form = ProductForm(user=request.user, initial_warehouse=initial_warehouse)

    return render(request, 'products/form.html', {
        'form': form,
        'title': 'Добавление товара'
    })


@login_required
def edit_product(request, pk):
    """Редактирование товара"""
    product = get_object_or_404(Product, pk=pk)
    
    # Проверка прав на редактирование товара
    can_edit = (
        request.user.is_staff or  # Админ может редактировать все товары
        (hasattr(request.user, 'profile') and  # Менеджер может редактировать только товары своего склада
         request.user.profile.warehouse == product.warehouse)
    )
    
    if not can_edit:
        raise PermissionDenied

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Товар "{product.name}" успешно обновлен!')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product, user=request.user)

    return render(request, 'products/form.html', {
        'form': form,
        'title': f'Редактирование {product.name}',
        'edit_mode': True
    })

@require_POST
@login_required
def delete_product(request, pk):
    """Удаление товара"""
    product = get_object_or_404(Product, pk=pk)
    
    # Проверка прав на удаление товара
    can_delete = (
        request.user.is_staff or  # Админ может удалять все товары
        (hasattr(request.user, 'profile') and  # Менеджер может удалять только товары своего склада
         request.user.profile.warehouse == product.warehouse)
    )
    
    if not can_delete:
        raise PermissionDenied

    product_name = product.name
    product.delete()
    messages.success(request, f'Товар "{product_name}" успешно удален!')
    return redirect('product_list')


# categories
@login_required
def category_list(request):
    """Список категорий"""
    categories = Category.objects.all()
    return render(request, 'categories/list.html', {
        'categories': categories,
    })

@user_passes_test(lambda u: u.is_staff)
def category_add(request):
    """Добавление категории"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Категория "{category.name}" успешно создана!')
            return redirect('category_list')
    else:
        form = CategoryForm()

    return render(request, 'categories/form.html', {
        'form': form,
        'title': 'Добавление категории'
    })

@user_passes_test(lambda u: u.is_staff)
def category_edit(request, pk):
    """Редактирование категории"""
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Категория "{category.name}" успешно обновлена!')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'categories/form.html', {
        'form': form,
        'title': f'Редактирование категории {category.name}',
        'edit_mode': True
    })

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

@user_passes_test(lambda u: u.is_staff)
def warehouse_list(request):
    """Список складов"""
    warehouses = Warehouse.objects.all()
    return render(request, 'warehouses/list.html', {
        'warehouses': warehouses,
        'title': 'Склады'
    })

@user_passes_test(lambda u: u.is_staff)
def warehouse_detail(request, pk):
    """Детальная информация о складе"""
    warehouse = get_object_or_404(Warehouse, pk=pk)
    products = Product.objects.filter(warehouse=warehouse)
    employees = warehouse.employees.all()
    
    return render(request, 'warehouses/detail.html', {
        'warehouse': warehouse,
        'products': products,
        'employees': employees,
        'title': f'Склад: {warehouse.name}'
    })

@user_passes_test(lambda u: u.is_staff)
def warehouse_create(request):
    """Создание нового склада"""
    if request.method == 'POST':
        form = WarehouseForm(request.POST, request.FILES)
        if form.is_valid():
            warehouse = form.save()
            messages.success(request, f'Склад "{warehouse.name}" успешно создан!')
            return redirect('warehouse_list')
    else:
        form = WarehouseForm()
    
    return render(request, 'warehouses/form.html', {
        'form': form,
        'title': 'Создание склада',
        'edit_mode': False
    })

@user_passes_test(lambda u: u.is_staff)
def warehouse_edit(request, pk):
    """Редактирование склада"""
    warehouse = get_object_or_404(Warehouse, pk=pk)
    
    if request.method == 'POST':
        form = WarehouseForm(request.POST, request.FILES, instance=warehouse)
        if form.is_valid():
            warehouse = form.save()
            messages.success(request, f'Склад "{warehouse.name}" успешно обновлен!')
            return redirect('warehouse_list')
    else:
        form = WarehouseForm(instance=warehouse)
    
    return render(request, 'warehouses/form.html', {
        'form': form,
        'warehouse': warehouse,
        'title': f'Редактирование склада: {warehouse.name}',
        'edit_mode': True
    })

@user_passes_test(lambda u: u.is_staff)
@require_POST
def warehouse_delete(request, pk):
    """Удаление склада"""
    warehouse = get_object_or_404(Warehouse, pk=pk)
    name = warehouse.name
    
    # Проверяем, есть ли связанные товары или сотрудники
    if warehouse.product_set.exists():
        messages.error(request, 'Невозможно удалить склад, так как на нем есть товары')
        return redirect('warehouse_list')
    
    if warehouse.employees.exists():
        messages.error(request, 'Невозможно удалить склад, так как на нем есть сотрудники')
        return redirect('warehouse_list')
    
    warehouse.delete()
    messages.success(request, f'Склад "{name}" успешно удален!')
    return redirect('warehouse_list')

