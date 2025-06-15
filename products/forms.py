from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Product, ProductDocument, User, Category, Warehouse


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'phone', 'address')


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'description', 'category', 'warehouse', 'price', 'quantity', 'image', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.initial_warehouse = kwargs.pop('initial_warehouse', None)
        super().__init__(*args, **kwargs)
        
        # Если пользователь менеджер
        if self.user and self.user.role == 'manager':
            if hasattr(self.user, 'profile') and self.user.profile.warehouse:
                self.fields['warehouse'].widget = forms.HiddenInput()
                self.fields['warehouse'].initial = self.user.profile.warehouse
            else:
                self.fields['warehouse'].widget = forms.HiddenInput()
        else:
            # Для всех остальных warehouse обязателен и видим
            self.fields['warehouse'].required = True
        if self.user and self.user.is_staff and self.initial_warehouse:
            self.fields['warehouse'].initial = self.initial_warehouse

    def clean(self):
        cleaned_data = super().clean()
        warehouse = cleaned_data.get('warehouse')
        if self.user and self.user.role == 'manager':
            if hasattr(self.user, 'profile') and self.user.profile.warehouse:
                cleaned_data['warehouse'] = self.user.profile.warehouse
            else:
                raise forms.ValidationError('У вас нет привязанного склада. Обратитесь к администратору.')
        elif not warehouse:
            raise forms.ValidationError('Поле "Склад" обязательно для заполнения.')
        return cleaned_data


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = ProductDocument
        fields = ['name', 'file']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Название документа'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        document = super().save(commit=False)
        if self.user:
            document.uploaded_by = self.user
        if commit:
            document.save()
        return document


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'address', 'description', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        if name and Warehouse.objects.filter(name=name).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError('Склад с таким названием уже существует')
        return cleaned_data