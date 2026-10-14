from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Product

def load_products(request):
    products = Product.objects.select_related('category', 'shop', 'brand').order_by('-created_at')

   
    searchName = request.GET.get('search', '').strip()
    locStatus = request.GET.get('status', '').strip()
    locIDcategory = request.GET.get('category', '').strip()


    if searchName != '':
        products = products.filter(product_name__icontains=searchName)

   
    if locStatus != '':
        products = products.filter(status=locStatus)

    
    if locIDcategory != '':
        products = products.filter(category_id=locIDcategory)

   
    phantrang = Paginator(products, 10)
    numPage = request.GET.get('page')
    showProduct = phantrang.get_page(numPage)

    boxSP = {
        'showProduct': showProduct,
        'searchName': searchName,
        'locStatus': locStatus,
        'locIDcategory': locIDcategory,
    }
    return render(request, 'admin/products.html', boxSP)


def showORhide_Product(request, product_id):
    product = Product.objects.filter(product_id=product_id).first()
    if not product:
        messages.error(request, 'Product not found.')
        return redirect('load_products')

    if product.status == 'ACTIVE':
        product.status = 'INACTIVE'
        messages.success(request, 'Product has been hidden.')
    else:
        product.status = 'ACTIVE'
        messages.success(request, 'Product has been shown.')

    product.save()
    return redirect('load_products')