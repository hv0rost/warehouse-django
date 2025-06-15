from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    # path('', views.index, name='index'),
    path('', views.catalog, name='catalog'),
    path('part/<int:pk>/', views.part_detail, name='part_detail'),
    path('profile/', views.profile, name='profile'),
    path('create_order/<int:part_id>/', views.create_order, name='create_order'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),

    path('manage/parts/', views.part_management, name='part_management'),
    path('manage/parts/add/', views.add_part, name='add_part'),
    path('manage/parts/edit/<int:pk>/', views.edit_part, name='edit_part'),
    path('manage/parts/delete/<int:pk>/', views.delete_part, name='delete_part'),

    # Auth URLs
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', views.register, name='register'),
]