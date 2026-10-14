from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from shops.models import Shop

from .models import Brand, Category, Product, ProductSpecification


class CatalogTestData(TestCase):
    @classmethod
    def setUpTestData(cls):
        owner = get_user_model().objects.create_user(
            username='catalog-owner', email='catalog@example.com',
        )
        cls.shop = Shop.objects.create(owner=owner, shop_name='Shop A', status='ACTIVE')
        cls.other_shop = Shop.objects.create(owner=owner, shop_name='Shop B', status='ACTIVE')
        cls.category = Category.objects.create(category_name='Bộ xử lý')
        cls.empty_category = Category.objects.create(category_name='Bộ nhớ')
        cls.brand = Brand.objects.create(brand_name='AMD')
        cls.other_brand = Brand.objects.create(brand_name='Intel')

    def create_product(self, **values):
        defaults = {
            'product_name': 'Ryzen 5', 'slug': 'ryzen-5', 'price': 2000000,
            'stock_quantity': 5, 'category': self.category, 'brand': self.brand,
            'shop': self.shop,
        }
        defaults.update(values)
        return Product.objects.create(**defaults)


class BuyerCatalogTests(CatalogTestData):
    def get_catalog(self, **params):
        response = self.client.get(reverse('buyer_search'), params)
        self.assertEqual(response.status_code, 200)
        return response

    def assert_filters_visible(self, response):
        self.assertContains(response, 'id="catalog-filters"')
        self.assertContains(response, 'class="search-layout"')
        for name in ['q', 'category', 'brand', 'min', 'max', 'shop', 'region', 'availability', 'sort']:
            self.assertContains(response, f'name="{name}"')
        self.assertContains(response, 'id="filter-drawer"')

    def test_empty_database_keeps_filter_layout(self):
        response = self.get_catalog()
        self.assert_filters_visible(response)
        self.assertContains(response, 'Tìm thấy 0 sản phẩm')
        self.assertContains(response, 'Không có sản phẩm phù hợp.')
        self.assertContains(response, 'Bộ xử lý')
        self.assertContains(response, 'AMD')
        self.assertContains(response, 'Shop A')
        self.assertNotContains(response, 'class="pagination"')

    def test_zero_matches_keep_selected_filters(self):
        self.create_product()
        response = self.get_catalog(q='không tồn tại', brand=self.brand.pk)
        self.assert_filters_visible(response)
        self.assertContains(response, 'Tìm thấy 0 sản phẩm')
        self.assertContains(response, 'value="không tồn tại"')
        self.assertContains(response, f'value="{self.brand.pk}" selected>AMD')

    def test_filters_use_database_products(self):
        target = self.create_product()
        other = self.create_product(
            product_name='Core i5', slug='core-i5', price=3000000,
            brand=self.other_brand, shop=self.other_shop, stock_quantity=0,
        )
        paused = self.create_product(
            product_name='Ryzen 7', slug='ryzen-7', price=4000000, status='INACTIVE',
        )
        for params, expected in [
            ({'q': 'core'}, [other]),
            ({'q': 'Intel'}, [other]),
            ({'brand': self.other_brand.pk}, [other]),
            ({'shop': self.other_shop.pk}, [other]),
            ({'category': self.empty_category.pk}, []),
            ({'min': '2000000', 'max': '2000000'}, [target]),
            ({'availability': 'in'}, [target]),
            ({'availability': 'out'}, [other]),
            ({'availability': 'paused'}, [paused]),
            ({'sort': 'price'}, [target, other, paused]),
            ({'sort': 'desc'}, [paused, other, target]),
        ]:
            with self.subTest(params=params):
                response = self.get_catalog(**params)
                self.assertEqual(list(response.context['page_obj']), expected)

    def test_technical_filters_match_all_selected_specifications(self):
        target = self.create_product()
        other = self.create_product(product_name='Ryzen khác', slug='other-ryzen')
        for product, name, value in [
            (target, 'Socket', 'AM5'), (target, 'RAM', 'DDR5'),
            (other, 'Socket', 'AM4'), (other, 'RAM', 'DDR4'),
        ]:
            ProductSpecification.objects.create(
                product=product, specification_name=name, specification_value=value,
            )
        response = self.get_catalog(**{
            'category': self.category.pk, 'tech:Socket': 'AM5', 'tech:RAM': 'DDR5',
        })
        self.assertEqual(list(response.context['page_obj']), [target])
        self.assertContains(response, 'name="tech:Socket"')
        self.assertContains(response, 'name="tech:RAM"')

    def test_invalid_price_keeps_filters_and_explains_error(self):
        self.create_product()
        response = self.get_catalog(min='3000000', max='2000000')
        self.assert_filters_visible(response)
        self.assertContains(response, 'Giá đến phải lớn hơn hoặc bằng giá từ.')
        self.assertContains(response, 'Tìm thấy 0 sản phẩm')
        for value in ['abc', '-1', 'NaN']:
            with self.subTest(value=value):
                self.assert_filters_visible(self.get_catalog(min=value))

    def test_pagination_retains_filter_query(self):
        for index in range(7):
            self.create_product(product_name=f'Ryzen {index}', slug=f'ryzen-{index}')
        response = self.get_catalog(q='Ryzen', brand=self.brand.pk, p=2)
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertContains(response, 'Tìm thấy 7 sản phẩm')
        self.assertContains(response, f'/buyer/search/?q=Ryzen&amp;brand={self.brand.pk}&amp;p=1')


class AdminProductListTests(CatalogTestData):
    def get_products(self, **params):
        response = self.client.get(reverse('staff_products'), params)
        self.assertEqual(response.status_code, 200)
        return response

    def test_empty_list_keeps_admin_layout_and_zero_counts(self):
        response = self.get_products()
        self.assertContains(response, 'Quản lý sản phẩm')
        self.assertContains(response, 'Chưa có sản phẩm nào.')
        self.assertContains(response, 'data-page="products" data-section="staff"')
        self.assertContains(response, 'id="admin-product-filters"')
        self.assertNotContains(response, '```')
        self.assertEqual(response.context['stats'], {
            'total': 0, 'selling': 0, 'out_of_stock': 0, 'hidden': 0,
        })

    def test_database_product_fields_are_rendered_in_table(self):
        product = self.create_product(
            product_name='Ryzen "Pro" & kit', price='2000000.50', sold_quantity=3,
            thumbnail='product_thumbnail/test.png',
        )
        response = self.get_products()
        self.assertEqual(list(response.context['showProduct']), [product])
        self.assertContains(response, 'Ryzen &quot;Pro&quot; &amp; kit')
        self.assertContains(response, 'Shop A')
        self.assertContains(response, 'Bộ xử lý')
        self.assertContains(response, '/media/product_thumbnail/test.png')
        self.assertContains(response, f'data-product-id="{product.pk}"')
        self.assertContains(response, 'data-price="2000000.50" data-sold="3"')
        self.assertContains(response, 'Chi tiết')
        self.assertNotContains(response, 'showORhide_Product')

    def test_filters_and_status_counts_use_real_data(self):
        active = self.create_product()
        out = self.create_product(
            product_name='Core i5', slug='core-i5', stock_quantity=0,
            brand=self.other_brand, shop=self.other_shop,
        )
        hidden = self.create_product(product_name='Ryzen 7', slug='ryzen-7', status='INACTIVE')
        marked_out = self.create_product(
            product_name='Ryzen 9', slug='ryzen-9', status='OUT_OF_STOCK',
        )
        for params, expected in [
            ({'search': 'Ryzen 5'}, [active]),
            ({'search': 'Shop B'}, [out]),
            ({'search': f'#{hidden.pk}'}, [hidden]),
            ({'shop': self.other_shop.pk}, [out]),
            ({'category': self.empty_category.pk}, []),
            ({'status': 'ACTIVE'}, [active]),
            ({'status': 'OUT_OF_STOCK'}, [marked_out, out]),
            ({'status': 'INACTIVE'}, [hidden]),
        ]:
            with self.subTest(params=params):
                response = self.get_products(**params)
                self.assertEqual(list(response.context['showProduct']), expected)
                self.assertEqual(response.context['stats'], {
                    'total': 4, 'selling': 1, 'out_of_stock': 2, 'hidden': 1,
                })
        response = self.get_products(status='ACTIVE')
        self.assertEqual([tab['count'] for tab in response.context['status_tabs']], [4, 1, 2, 1])

    def test_no_matches_and_invalid_filters_do_not_break_page(self):
        self.create_product()
        for params in [
            {'search': 'không tồn tại'}, {'category': 'invalid'}, {'status': 'invalid'},
        ]:
            with self.subTest(params=params):
                response = self.get_products(**params)
                self.assertContains(response, 'Không có sản phẩm phù hợp.')
                self.assertContains(response, 'id="admin-product-filters"')
                self.assertEqual(response.context['showProduct'].paginator.count, 0)

    def test_pagination_preserves_search_shop_category_and_status(self):
        for index in range(11):
            self.create_product(product_name=f'Mạch & kit {index}', slug=f'kit-{index}')
        params = {
            'search': 'Mạch & kit', 'shop': self.shop.pk,
            'category': self.category.pk, 'status': 'ACTIVE',
        }
        response = self.get_products(**params)
        self.assertEqual(len(response.context['showProduct']), 10)
        self.assertContains(response, f'/staff/products/?{escape(response.context["query_string"])}&amp;page=2')
        response = self.get_products(**params, page=2)
        self.assertEqual(len(response.context['showProduct']), 1)


class ProductComparisonTests(CatalogTestData):
    def get_comparison(self, ids):
        response = self.client.get(reverse('buyer_compare'), {
            'source': 'database', 'products': ids,
        })
        self.assertEqual(response.status_code, 200)
        return response

    def test_cards_render_detail_and_compare_actions(self):
        product = self.create_product()
        response = self.client.get(reverse('buyer_search'))
        self.assertContains(response, reverse('buyer_product_detail', args=[product.pk]))
        self.assertContains(response, 'data-action="product-compare-add"')

    def test_compares_current_database_values_and_specifications(self):
        first = self.create_product()
        second = self.create_product(
            product_name='Ryzen 7', slug='ryzen-7', price='3000000.50',
            shop=self.other_shop, stock_quantity=0,
        )
        ProductSpecification.objects.create(
            product=first, specification_name='Socket', specification_value='AM5',
        )
        response = self.get_comparison(f'{second.pk},{first.pk}')
        self.assertEqual(response.context['compared_products'], [second, first])
        self.assertContains(response, 'data-product-price="3000000.50"')
        self.assertContains(response, 'Shop B')
        self.assertContains(response, 'Socket')
        self.assertContains(response, 'AM5')
        self.assertContains(response, 'Hết hàng')
        self.assertContains(response, 'id="product-compare-items"')

    def test_missing_invalid_and_duplicate_ids(self):
        product = self.create_product()
        response = self.get_comparison(f'bad,{product.pk},{product.pk},999999999')
        self.assertEqual(response.context['compared_products'], [product])
        for ids in ['', 'bad,-1,999999999', '9' * 100]:
            with self.subTest(ids=ids):
                response = self.get_comparison(ids)
                self.assertContains(response, 'Chưa chọn sản phẩm')

    def test_limits_comparison_to_four_products(self):
        products = [self.create_product(slug=f'compare-{index}') for index in range(5)]
        response = self.get_comparison(','.join(str(product.pk) for product in products))
        self.assertEqual(response.context['compared_products'], products[:4])

    def test_rejects_different_categories(self):
        first = self.create_product()
        second = self.create_product(slug='other-category', category=self.empty_category)
        response = self.get_comparison(f'{first.pk},{second.pk}')
        self.assertContains(response, 'Chỉ so sánh sản phẩm cùng danh mục.')
        self.assertEqual(response.context['compared_products'], [])

    def test_original_demo_compare_route_still_renders(self):
        response = self.client.get(reverse('buyer_compare'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-catalog-source="demo"')


class BuyerProductDetailTests(CatalogTestData):
    def test_list_links_to_each_product_id(self):
        first = self.create_product()
        second = self.create_product(product_name='Ryzen 7', slug='ryzen-7')
        response = self.client.get(reverse('buyer_search'))
        self.assertEqual(response.status_code, 200)
        for product in [first, second]:
            self.assertContains(response, reverse('buyer_product_detail', args=[product.pk]))

    def test_detail_renders_requested_product_with_context(self):
        self.create_product()
        product = self.create_product(
            product_name='Chuột kiểm thử', slug='test-mouse', price=379000,
            thumbnail='product_thumbnail/test-mouse.jpg', description='Mô tả chuột kiểm thử.',
        )
        ProductSpecification.objects.create(
            product=product, specification_name='Kết nối', specification_value='USB',
        )
        response = self.client.get(reverse('buyer_product_detail', args=[product.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_product'], product)
        self.assertContains(response, 'data-page="model" data-section="buyer" data-catalog-source="database"')
        self.assertContains(response, 'Chuột kiểm thử')
        self.assertContains(response, 'Mô tả chuột kiểm thử.')
        self.assertContains(response, 'data-product-price="379000.00"')
        self.assertContains(response, '/media/product_thumbnail/test-mouse.jpg')
        self.assertContains(response, 'USB')
        self.assertNotContains(response, 'Ryzen 5')

    def test_unknown_product_returns_404(self):
        response = self.client.get(reverse('buyer_product_detail', args=[999999999]))
        self.assertEqual(response.status_code, 404)

    def test_original_demo_detail_remains_available(self):
        response = self.client.get(reverse('buyer_model'), {'id': 'CPU-7600'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-catalog-source="demo"')
