from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    # path('', views.index, name='index'),
    path('', views.catalog, name='catalog'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('profile/', views.profile, name='profile'),
    path('create_order/<int:product_id>/', views.create_order, name='create_order'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),

    path('manage/products/', views.product_management, name='product_management'),
    path('manage/products/add/', views.add_product, name='add_product'),
    path('manage/products/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('manage/products/delete/<int:pk>/', views.delete_product, name='delete_product'),

    # Auth URLs
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', views.register, name='register'),
]