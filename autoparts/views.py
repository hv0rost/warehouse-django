from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_POST

from .models import Part, Category, Order, PartDocument, OrderItem, generate_sku
from .forms import PartForm, DocumentUploadForm, OrderForm, RegistrationForm, OrderStatusForm
from django.contrib.auth import login
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe


def index(request):
    categories = Category.objects.all()[:6]
    new_parts = Part.objects.filter(quantity__gt=0).order_by('-created_at')[:8]

    return render(request, 'autoparts/index.html', {
        'categories': categories,
        'parts': new_parts,
        'title': 'Главная страница'
    })


def catalog(request):
    """Страница каталога с фильтрами"""
    query = request.GET.get('q', '')
    category_id = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    parts = Part.objects.filter(quantity__gt=0)

    if query:
        parts = parts.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(sku__icontains=query)
        )

    if category_id:
        parts = parts.filter(category_id=category_id)

    if min_price:
        parts = parts.filter(price__gte=float(min_price))

    if max_price:
        parts = parts.filter(price__lte=float(max_price))

    categories = Category.objects.all()
    return render(request, 'autoparts/catalog.html', {
        'parts': parts,
        'categories': categories,
        'search_query': query,
        'selected_category': int(category_id) if category_id else None,
    })


def part_detail(request, pk):
    """Детальная страница запчасти"""
    part = get_object_or_404(Part.objects.prefetch_related('documents'), pk=pk)
    documents = part.documents.all()

    if request.method == 'POST' and request.user.is_authenticated:
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.part = part
            document.uploaded_by = request.user
            document.save()
            messages.success(request, 'Файл успешно загружен.')
            return redirect('part_detail', pk=pk)
    else:
        form = DocumentUploadForm()

    return render(request, 'autoparts/part_detail.html', {
        'part': part,
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
        'orderitem_set__part'
    ).order_by('-created_at')

    return render(request, 'autoparts/profile.html', {
        'orders': orders,
        'user': request.user
    })


@login_required
def create_order(request, part_id):
    part = get_object_or_404(Part, pk=part_id)

    if request.method == 'POST':
        form = OrderForm(request.POST, part=part)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            price = part.get_actual_price(quantity)

            order = Order.objects.create(
                user=request.user,
                notes=form.cleaned_data['notes'],
                status='pending'
            )
            OrderItem.objects.create(
                order=order,
                part=part,
                quantity=quantity,
                price=price
            )

            part.quantity -= quantity
            part.save()

            success_message = format_html(
                '<h4 class="alert-heading">Заказ оформлен!</h4>'
                '<p>Товар: <strong>{}</strong> × {} шт.</p>'
                '<p>Цена за единицу: {} ₽</p>'
                '<p>Общая сумма: <strong>{} ₽</strong></p>'
                '<hr>'
                '<p>Номер заказа: <strong>#{}</strong></p>',
                part.name,
                quantity,
                price,
                price * quantity,
                order.id
            )
            messages.success(request, success_message)
            return redirect('order_detail', order_id=order.id)
    else:
        form = OrderForm(part=part)

    return render(request, 'autoparts/create_order.html', {
        'part': part,
        'form': form,
        'title': 'Оформление заказа'
    })

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('orderitem_set__part'),
                            id=order_id,
                            user=request.user)
    return render(request, 'autoparts/order_detail.html', {
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
def part_management(request):
    """Управление запчастями (админка)"""
    parts = Part.objects.select_related('category').all()
    return render(request, 'autoparts/manage/part_management.html', {
        'parts': parts,
    })


@user_passes_test(lambda u: u.is_staff)
def add_part(request):
    if request.method == 'POST':
        form = PartForm(request.POST, request.FILES)
        if form.is_valid():
            part = form.save(commit=False)

            # Дополнительная проверка SKU
            if not part.sku:
                part.sku = generate_sku()

            try:
                part.save()
                messages.success(request, f'Запчасть "{part.name}" успешно сохранена! SKU: {part.sku}')
                return redirect('part_management')
            except IntegrityError:
                messages.error(request, 'Запчасть с таким артикулом уже существует')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = PartForm()

    return render(request, 'autoparts/manage/add_part.html', {
        'form': form,
        'title': 'Добавление запчасти'
    })


@user_passes_test(lambda u: u.is_staff)
def edit_part(request, pk):
    part = get_object_or_404(Part, pk=pk)
    if request.method == 'POST':
        form = PartForm(request.POST, request.FILES, instance=part)
        if form.is_valid():
            form.save()
            messages.success(request, f'Запчасть "{part.name}" успешно обновлена!')
            return redirect('part_management')
    else:
        form = PartForm(instance=part)

    return render(request, 'autoparts/manage/add_part.html', {
        'form': form,
        'title': f'Редактирование {part.name}',
        'edit_mode': True
    })

@require_POST
@user_passes_test(lambda u: u.is_staff)
def delete_part(request, pk):
    part = get_object_or_404(Part, pk=pk)
    part_name = part.name
    part.delete()
    messages.success(request, f'Запчасть "{part_name}" успешно удалена!')
    return redirect('part_management')