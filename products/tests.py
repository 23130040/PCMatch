from django.contrib.auth import get_user_model
from django.test import Client, TestCase
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
        self.assertNotContains(response, 'js/buyer.js')

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

    def test_search_form_and_comparison_work_without_javascript(self):
        first = self.create_product()
        second = self.create_product(product_name='Ryzen 7', slug='ryzen-7')
        response = self.get_catalog()
        self.assertContains(response, 'method="get"')
        self.assertContains(response, 'data-comparison-form')
        self.assertContains(response, 'Thêm so sánh')
        self.assertNotContains(response, '<template')
        response = self.client.get(reverse('buyer_compare'), {'products': [first.pk, second.pk]})
        self.assertEqual(response.context['compared_products'], [first, second])
        self.assertNotContains(response, 'js/buyer.js')

    def test_pagination_retains_filter_query(self):
        for index in range(7):
            self.create_product(product_name=f'Ryzen {index}', slug=f'ryzen-{index}')
        response = self.get_catalog(q='Ryzen', brand=self.brand.pk, p=2)
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertContains(response, 'Tìm thấy 7 sản phẩm')
        self.assertContains(response, f'/buyer/search/?q=Ryzen&amp;brand={self.brand.pk}&amp;p=1')


class AdminProductListTests(CatalogTestData):
    def setUp(self):
        staff = get_user_model().objects.create_user(
            username='product-staff', email='staff-products@example.com', is_staff=True, role='ADMIN',
        )
        self.client.force_login(staff)

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
        self.assertContains(response, reverse('buyer_comparison_update'))
        self.assertContains(response, 'Thêm so sánh')
        self.assertNotContains(response, 'type="checkbox" name="products"')

    def update_selection(self, action, product=None, **extra):
        return self.client.post(reverse('buyer_comparison_update'), {
            'action': action, 'product_id': product.pk if product else '',
            'return_to': reverse('buyer_search'), **extra,
        })

    def test_selection_survives_filters_detail_and_comparison_navigation(self):
        first = self.create_product()
        second = self.create_product(product_name='Ryzen 7', slug='ryzen-7')
        self.assertRedirects(self.update_selection('add', first), reverse('buyer_search'))
        response = self.client.get(reverse('buyer_search'), {'q': 'không tồn tại'})
        self.assertContains(response, 'Ryzen 5 · Bỏ')
        response = self.client.get(reverse('buyer_product_detail', args=[second.pk]))
        self.assertContains(response, 'Đang so sánh 1/4')
        self.update_selection('add', second)
        response = self.client.get(reverse('buyer_compare'))
        self.assertEqual(response.context['compared_products'], [first, second])
        self.update_selection('remove', first)
        self.assertEqual(self.client.get(reverse('buyer_compare')).context['compared_products'], [second])
        self.update_selection('clear')
        self.assertContains(self.client.get(reverse('buyer_compare')), 'Chưa chọn sản phẩm')

    def test_repeated_add_and_invalid_choices_keep_existing_selection(self):
        products = [self.create_product(slug=f'selected-{index}') for index in range(5)]
        other = self.create_product(slug='other-selected-category', category=self.empty_category)
        self.update_selection('add', products[0])
        self.update_selection('add', products[0])
        self.assertEqual(self.client.session['product_comparison'], [products[0].pk])
        for product in products[1:4]:
            self.update_selection('add', product)
        for product, expected_error in [(products[4], 'tối đa 4'), (other, 'cùng danh mục')]:
            response = self.client.post(reverse('buyer_comparison_update'), {
                'action': 'add', 'product_id': product.pk,
            }, HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 400)
            self.assertIn(expected_error, response.json()['message'])
            self.assertEqual(response.json()['selected'], [item.pk for item in products[:4]])

    def test_ajax_selection_uses_escaped_html_and_current_database_names(self):
        product = self.create_product(product_name='Ryzen <Pro> & Kit')
        response = self.client.post(reverse('buyer_comparison_update'), {
            'action': 'add', 'product_id': product.pk,
            'return_to': reverse('buyer_search') + '?q=Ryzen',
        }, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['selected'], [product.pk])
        self.assertIn('Ryzen &lt;Pro&gt; &amp; Kit · Bỏ', payload['html'])
        self.assertIn('return_to" value="/buyer/search/?q=Ryzen"', payload['html'])
        product.product_name = 'Tên đã cập nhật'
        product.save(update_fields=['product_name'])
        self.assertContains(self.client.get(reverse('buyer_search')), 'Tên đã cập nhật · Bỏ')
        product.delete()
        self.assertNotContains(self.client.get(reverse('buyer_search')), 'Tên đã cập nhật · Bỏ')

    def test_selection_endpoint_requires_csrf_post_and_rejects_external_redirects(self):
        product = self.create_product()
        url = reverse('buyer_comparison_update')
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(Client(enforce_csrf_checks=True).post(url, {'action': 'clear'}).status_code, 403)
        response = self.update_selection('add', product, return_to='https://example.com/')
        self.assertRedirects(response, reverse('buyer_search'))
        response = self.client.post(url, {'action': 'add', 'product_id': '999999'}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['selected'], [product.pk])

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
        self.assertContains(response, 'class="table-wrap product-comparison"')

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

    def test_comparison_route_uses_database_without_demo_mode(self):
        response = self.client.get(reverse('buyer_compare'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-catalog-source="database"')


class BuyerHomeTests(CatalogTestData):
    def test_root_and_buyer_home_render_database_products(self):
        newest = self.create_product(product_name='Mới nhất', slug='newest', sold_quantity=2)
        bestseller = self.create_product(product_name='Bán chạy nhất', slug='bestseller', sold_quantity=30)
        latest = self.create_product(product_name='Vừa thêm', slug='latest', sold_quantity=1)
        self.create_product(product_name='Sản phẩm ẩn', slug='hidden', status='INACTIVE', sold_quantity=100)
        for name in ['home', 'buyer_home']:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(list(response.context['bestselling_products']), [bestseller, newest, latest])
                self.assertEqual(list(response.context['newest_products']), [latest, bestseller, newest])
                self.assertContains(response, 'data-page="home" data-section="buyer"')
                self.assertContains(response, reverse('buyer_product_detail', args=[latest.pk]))
                self.assertNotContains(response, 'Sản phẩm ẩn')
                self.assertNotContains(response, 'Toàn bộ PCMatch trong một bản đồ')
                self.assertNotContains(response, '<template')
                self.assertNotContains(response, 'js/buyer.js')

    def test_empty_home_still_renders_navigation_and_empty_states(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Chọn linh kiện. Chọn shop phù hợp.')
        self.assertContains(response, 'Chưa có sản phẩm đang bán.')
        self.assertContains(response, reverse('buyer_search'))


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

    def test_legacy_demo_detail_redirects_to_real_catalog(self):
        response = self.client.get(reverse('buyer_model'), {'id': 'CPU-7600'})
        self.assertRedirects(response, reverse('buyer_search'))
