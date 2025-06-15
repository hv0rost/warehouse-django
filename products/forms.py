from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Product, ProductDocument, User, Category


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
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sku'].required = True
        self.fields['sku'].label = "Артикул"

    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        if not sku:
            # Генерируем SKU только если поле пустое
            last_part = Product.objects.order_by('-id').first()
            sku = f"PART-{(last_part.id + 1) if last_part else 1}"
        return sku


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = ProductDocument
        fields = ['file', 'description']
        labels = {
            'file': 'Файл документа',
            'description': 'Описание документа'
        }
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Введите описание документа'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].widget.attrs.update({
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.xls,.xlsx,.odt'
        })


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']