from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Part, PartDocument, Order, User, Category
from django.core.exceptions import ValidationError


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'phone', 'address')


class PartForm(forms.ModelForm):
    class Meta:
        model = Part
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sku'].required = True
        self.fields['sku'].label = "Артикул"

    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        if not sku:
            # Генерируем SKU только если поле пустое
            last_part = Part.objects.order_by('-id').first()
            sku = f"PART-{(last_part.id + 1) if last_part else 1}"
        return sku


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = PartDocument
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


class OrderForm(forms.Form):
    quantity = forms.IntegerField(
        label='Количество',
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1
        })
    )
    notes = forms.CharField(
        label='Комментарий',
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Ваши пожелания к заказу...'
        })
    )

    def __init__(self, *args, part=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.part = part
        if part:
            self.fields['quantity'].widget.attrs['max'] = part.quantity

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if not self.part:
            return quantity

        if quantity < self.part.min_order and quantity < self.part.quantity:
            raise ValidationError(
                f'Минимальное количество для заказа: {self.part.min_order} шт.'
            )

        if quantity > self.part.quantity:
            raise ValidationError(
                f'Недостаточно товара на складе. Доступно: {self.part.quantity} шт.'
            )

        return quantity

class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'this.form.submit()'
            })
        }