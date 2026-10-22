from django import forms

from shops.models import Shop

from .models import Brand, Category, ProductSpecification


class ProductQuestionForm(forms.Form):
    question = forms.CharField(
        label='Câu hỏi của bạn', max_length=1000,
        error_messages={
            'required': 'Vui lòng nhập câu hỏi về sản phẩm.',
            'max_length': 'Câu hỏi không được vượt quá 1.000 ký tự.',
        },
        widget=forms.Textarea(attrs={
            'rows': 4, 'maxlength': 1000,
            'placeholder': 'Bạn muốn hỏi shop về thông số, bảo hành hoặc tình trạng sản phẩm?',
            'aria-describedby': 'product-question-help',
        }),
    )


class ProductAnswerForm(forms.Form):
    answer = forms.CharField(
        max_length=500,
        error_messages={
            'required': 'Vui lòng nhập câu trả lời.',
            'max_length': 'Câu trả lời không được vượt quá 500 ký tự.',
        },
    )


class ProductFollowupForm(forms.Form):
    reply = forms.CharField(
        label='Nội dung hỏi thêm', max_length=1000,
        error_messages={
            'required': 'Vui lòng nhập nội dung muốn trao đổi.',
            'max_length': 'Nội dung không được vượt quá 1.000 ký tự.',
        },
        widget=forms.Textarea(attrs={
            'rows': 3, 'maxlength': 1000,
            'placeholder': 'Hỏi thêm hoặc tham gia trao đổi về câu hỏi này...',
        }),
    )


class AdminProductFilterForm(forms.Form):
    search = forms.CharField(
        label='Tìm kiếm', required=False, max_length=255,
        widget=forms.TextInput(attrs={
            'placeholder': 'Tìm theo tên sản phẩm, shop hoặc mã...',
            'aria-label': 'Tìm sản phẩm',
        }),
    )
    status = forms.ChoiceField(label='Trạng thái', required=False, choices=[
        ('', 'Tất cả'), ('ACTIVE', 'Đang bán'),
        ('OUT_OF_STOCK', 'Hết hàng'), ('INACTIVE', 'Tạm ẩn'),
    ])
    shop = forms.ModelChoiceField(
        label='Shop', queryset=Shop.objects.order_by('shop_name'),
        required=False, empty_label='Tất cả shop',
    )
    category = forms.ModelChoiceField(
        label='Danh mục', queryset=Category.objects.order_by('category_name'),
        required=False, empty_label='Tất cả danh mục',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ['shop', 'category']:
            self.fields[name].widget.attrs.update({
                'form': 'admin-product-filters',
                'data-admin-product-filter': '',
            })


class CatalogFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'type': 'search', 'placeholder': 'Tên, hãng hoặc mã sản phẩm',
        }),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.order_by('category_name'),
        required=False, empty_label='Tất cả',
    )
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.order_by('brand_name'),
        required=False, empty_label='Tất cả',
    )
    min = forms.DecimalField(
        required=False, min_value=0, max_digits=15, decimal_places=2,
        widget=forms.NumberInput(attrs={'min': '0', 'step': '1'}),
    )
    max = forms.DecimalField(
        required=False, min_value=0, max_digits=15, decimal_places=2,
        widget=forms.NumberInput(attrs={'min': '0', 'step': '1'}),
    )
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.order_by('shop_name'),
        required=False, empty_label='Tất cả shop',
    )
    region = forms.ChoiceField(
        required=False, disabled=True,
        choices=[('', 'Tất cả khu vực')],
    )
    availability = forms.ChoiceField(required=False, choices=[
        ('', 'Tất cả'), ('in', 'Còn hàng'), ('out', 'Hết hàng'),
        ('paused', 'Tạm ngừng bán'),
    ])
    sort = forms.ChoiceField(required=False, choices=[
        ('', 'Theo danh mục'), ('price', 'Giá tăng dần'),
        ('desc', 'Giá giảm dần'), ('sold', 'Bán chạy'), ('name', 'Tên A–Z'),
    ])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.technical_names = []
        category_id = self.data.get('category', '')
        if not str(category_id).isascii() or not str(category_id).isdigit():
            return
        if len(str(category_id)) > 18:
            return
        specifications = (
            ProductSpecification.objects
            .filter(product__category_id=category_id)
            .order_by('specification_name', 'specification_value')
            .values_list('specification_name', 'specification_value')
            .distinct()
        )
        options = {}
        for name, value in specifications:
            if name and value:
                options.setdefault(name, []).append((value, value))
        for name, choices in options.items():
            field_name = 'tech:' + name
            self.fields[field_name] = forms.ChoiceField(
                label=name, required=False, choices=[('', 'Tất cả'), *choices],
            )
            self.technical_names.append(field_name)

    def clean(self):
        cleaned = super().clean()
        minimum, maximum = cleaned.get('min'), cleaned.get('max')
        if minimum is not None and maximum is not None and maximum < minimum:
            self.add_error('max', 'Giá đến phải lớn hơn hoặc bằng giá từ.')
        return cleaned
