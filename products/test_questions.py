from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from shops.models import Shop
from .models import Category, Product, ProductAnswer, ProductQuestion


class ProductQuestionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.buyer = User.objects.create_user(username='question-buyer', email='questions-buyer@test.local', full_name='Người hỏi', role='BUYER')
        cls.other_buyer = User.objects.create_user(username='question-participant', email='questions-participant@test.local', full_name='Khách tham gia', role='BUYER')
        cls.owner = User.objects.create_user(username='question-owner', email='questions-owner@test.local', role='SELLER')
        cls.other_owner = User.objects.create_user(username='question-other', email='questions-other@test.local', role='SELLER')
        cls.admin = User.objects.create_user(username='question-admin', email='questions-admin@test.local', role='ADMIN', is_staff=True)
        cls.shop = Shop.objects.create(owner=cls.owner, shop_name='Shop hỏi đáp', status='ACTIVE')
        cls.other_shop = Shop.objects.create(owner=cls.other_owner, shop_name='Shop khác', status='ACTIVE')
        category = Category.objects.create(category_name='CPU')
        cls.product = Product.objects.create(shop=cls.shop, category=category, product_name='CPU hỏi đáp', slug='qa-cpu', price=100000, stock_quantity=3)
        cls.other_product = Product.objects.create(shop=cls.other_shop, category=category, product_name='CPU riêng', slug='qa-other', price=200000, stock_quantity=2)

    def detail_url(self):
        return reverse('buyer_product_detail', args=[self.product.pk])

    def send(self, text='Sản phẩm bảo hành bao lâu?', **extra):
        return self.client.post(reverse('buyer_product_question_create', args=[self.product.pk]), {'question': text, **extra})

    def question(self, **extra):
        return ProductQuestion.objects.create(product=self.product, user=self.buyer, question='Sản phẩm bảo hành bao lâu?', **extra)

    def answer(self, question, text='Bảo hành 36 tháng.'):
        return self.client.post(reverse('shop_question_answer', args=[question.pk]), {'answer': text})

    def test_public_page_has_question_section_and_login_link(self):
        response = self.client.get(self.detail_url())
        self.assertContains(response, 'Hỏi đáp sản phẩm (0)')
        self.assertContains(response, 'Chưa có câu hỏi nào.')
        self.assertContains(response, 'Đăng nhập')
        self.assertNotContains(response, 'name="question"')
        target = parse_qs(urlparse(response.context['question_login_url']).query)['next'][0]
        self.assertEqual(target, self.detail_url() + '#product-questions')

    def test_buyer_can_submit_question_with_server_owned_product_and_author(self):
        self.client.force_login(self.buyer)
        response = self.send('  Còn hàng không?  ', user_id=self.owner.pk, product_id=self.other_product.pk, status='on')
        self.assertRedirects(response, self.detail_url() + '#product-questions')
        question = ProductQuestion.objects.get()
        self.assertEqual((question.user, question.product, question.question), (self.buyer, self.product, 'Còn hàng không?'))
        self.assertFalse(question.status)
        self.assertContains(self.client.get(self.detail_url()), 'Đang chờ shop trả lời.')

    def test_guest_redirect_returns_to_product_after_login(self):
        response = self.send()
        self.assertEqual(parse_qs(urlparse(response.url).query)['next'], [self.detail_url() + '#product-questions'])
        self.assertFalse(ProductQuestion.objects.exists())

    def test_seller_admin_and_inactive_buyer_cannot_submit(self):
        for user in [self.owner, self.admin]:
            self.client.force_login(user)
            self.send()
        self.buyer.status = 'LOCKED'
        self.buyer.save(update_fields=['status'])
        self.client.force_login(self.buyer)
        self.send()
        self.assertFalse(ProductQuestion.objects.exists())

    def test_question_validates_empty_and_oversized_content(self):
        self.client.force_login(self.buyer)
        for text in ['', '   ', 'x' * 1001]:
            response = self.send(text)
            self.assertEqual(response.status_code, 400)
            self.assertIn('question', response.context['question_form'].errors)
        self.assertFalse(ProductQuestion.objects.exists())

    def test_out_of_stock_accepts_questions_but_hidden_product_and_inactive_shop_do_not(self):
        self.client.force_login(self.buyer)
        self.product.status = 'OUT_OF_STOCK'
        self.product.save(update_fields=['status'])
        self.assertEqual(self.send().status_code, 302)
        self.product.status = 'INACTIVE'
        self.product.save(update_fields=['status'])
        self.assertEqual(self.send().status_code, 400)
        self.product.status = 'ACTIVE'
        self.product.save(update_fields=['status'])
        self.shop.status = 'SUSPENDED'
        self.shop.save(update_fields=['status'])
        self.assertEqual(self.send().status_code, 400)
        self.assertEqual(ProductQuestion.objects.count(), 1)

    def test_questions_are_scoped_and_paginated_newest_first(self):
        ProductQuestion.objects.create(product=self.other_product, user=self.buyer, question='Câu hỏi riêng sản phẩm khác')
        for index in range(11):
            ProductQuestion.objects.create(product=self.product, user=self.buyer, question=f'Câu hỏi số {index}')
        response = self.client.get(self.detail_url())
        self.assertEqual(len(response.context['questions_page']), 10)
        self.assertContains(response, 'Câu hỏi số 10')
        self.assertNotContains(response, 'Câu hỏi số 0<')
        self.assertNotContains(response, 'Câu hỏi riêng sản phẩm khác')
        response = self.client.get(self.detail_url(), {'questions_page': 2})
        self.assertEqual(len(response.context['questions_page']), 1)
        self.assertContains(response, 'Câu hỏi số 0')

    def test_shop_can_answer_and_reply_appears_on_public_product(self):
        question = self.question()
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse('shop_questions')), question.question)
        response = self.answer(question)
        self.assertRedirects(response, reverse('shop_questions') + '?answered=1')
        question.refresh_from_db()
        self.assertTrue(question.status)
        self.assertEqual(question.answers.get().user, self.owner)
        self.client.logout()
        response = self.client.get(self.detail_url())
        self.assertContains(response, 'Bảo hành 36 tháng.')
        self.assertContains(response, self.shop.shop_name)
        self.assertNotContains(response, 'Đang chờ shop trả lời.')

    def test_reply_requires_owning_shop_and_allows_continuation(self):
        question = self.question()
        self.client.force_login(self.other_owner)
        self.assertEqual(self.answer(question).status_code, 404)
        self.client.force_login(self.buyer)
        self.answer(question)
        self.assertFalse(ProductAnswer.objects.exists())
        self.client.force_login(self.owner)
        self.answer(question)
        self.answer(question, 'Shop bổ sung: bảo hành tại hãng.')
        self.assertEqual(ProductAnswer.objects.count(), 2)

    def test_reply_validates_content_and_writes_answer_and_status_atomically(self):
        question = self.question()
        self.client.force_login(self.owner)
        for text in ['  ', 'x' * 501]:
            self.answer(question, text)
        self.assertFalse(ProductAnswer.objects.exists())
        question.refresh_from_db()
        self.assertFalse(question.status)
        with patch.object(ProductQuestion, 'save', side_effect=IntegrityError('failed')):
            self.answer(question)
        self.assertFalse(ProductAnswer.objects.exists())
        question.refresh_from_db()
        self.assertFalse(question.status)

    def test_question_and_answer_text_are_escaped_and_private_identifiers_not_exposed(self):
        self.buyer.full_name = ''
        self.buyer.username = self.buyer.email
        self.buyer.save(update_fields=['full_name', 'username'])
        question = ProductQuestion.objects.create(product=self.product, user=self.buyer, question='<script>question()</script>')
        ProductAnswer.objects.create(question=question, user=self.owner, answer='<img src=x onerror=alert(1)>')
        ProductAnswer.objects.create(question=question, user=self.other_owner, answer='Trả lời không thuộc shop')
        response = self.client.get(self.detail_url())
        self.assertContains(response, '&lt;script&gt;question()&lt;/script&gt;')
        self.assertContains(response, '&lt;img src=x onerror=alert(1)&gt;')
        self.assertNotContains(response, '<script>question()</script>')
        self.assertNotContains(response, self.buyer.email)
        self.assertNotContains(response, 'Trả lời không thuộc shop')

    def test_endpoints_require_post_and_csrf(self):
        question = self.question()
        question_url = reverse('buyer_product_question_create', args=[self.product.pk])
        answer_url = reverse('shop_question_answer', args=[question.pk])
        self.assertEqual(self.client.get(question_url).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.buyer)
        self.assertEqual(strict.post(question_url, {'question': 'Còn hàng?'}).status_code, 403)
        strict.force_login(self.owner)
        self.assertEqual(strict.post(answer_url, {'answer': 'Còn hàng.'}).status_code, 403)
        self.assertEqual(strict.get(answer_url).status_code, 405)

    def test_missing_product_does_not_create_question(self):
        self.client.force_login(self.buyer)
        response = self.client.post(reverse('buyer_product_question_create', args=[9999999]), {'question': 'Còn hàng? '})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(ProductQuestion.objects.exists())

    def followup(self, question, text='Có dùng được với laptop không?', **extra):
        return self.client.post(
            reverse('buyer_product_question_followup', args=[self.product.pk, question.pk]),
            {'reply': text, **extra},
        )

    def test_question_author_can_follow_up_and_shop_can_answer_again(self):
        question = self.question()
        self.client.force_login(self.owner)
        self.answer(question)
        self.client.force_login(self.buyer)
        response = self.followup(question)
        self.assertEqual(response.status_code, 302)
        question.refresh_from_db()
        self.assertFalse(question.status)
        self.assertEqual(ProductQuestion.objects.count(), 1)
        reply = ProductAnswer.objects.filter(is_shop_reply=False).get()
        self.assertEqual(reply.user, self.buyer)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('shop_questions'))
        self.assertContains(response, 'Có dùng được với laptop không?')
        self.assertContains(response, 'name="answer"')
        self.answer(question, 'Có, dùng được với laptop có Bluetooth.')
        question.refresh_from_db()
        self.assertTrue(question.status)
        self.client.logout()
        body = self.client.get(self.detail_url()).content.decode()
        self.assertLess(body.index('Bảo hành 36 tháng.'), body.index('Có dùng được với laptop không?'))
        self.assertLess(body.index('Có dùng được với laptop không?'), body.index('Có, dùng được với laptop có Bluetooth.'))

    def test_other_buyers_can_join_without_impersonating_shop(self):
        question = self.question()
        self.client.force_login(self.other_buyer)
        self.followup(question, user_id=self.owner.pk, is_shop_reply='true', question_id=999999)
        reply = ProductAnswer.objects.get()
        self.assertEqual(reply.user, self.other_buyer)
        self.assertEqual(reply.question, question)
        self.assertFalse(reply.is_shop_reply)
        self.client.logout()
        response = self.client.get(self.detail_url())
        self.assertContains(response, 'Khách tham gia')
        self.assertContains(response, 'product-question-followup')

    def test_followup_reopens_shop_pending_inbox_and_orders_by_latest_activity(self):
        old_question = self.question()
        new_question = self.question()
        self.client.force_login(self.owner)
        self.answer(old_question)
        self.client.force_login(self.buyer)
        self.followup(old_question)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('shop_questions'))
        self.assertEqual([row.pk for row in response.context['questions_page']], [old_question.pk, new_question.pk])
        self.assertEqual(response.context['question_pending'], 2)
        self.assertNotContains(self.client.get(reverse('shop_questions'), {'answered': '1'}), 'Có dùng được với laptop không?')

    def test_followup_checks_login_role_post_csrf_and_product_scope(self):
        question = self.question()
        url = reverse('buyer_product_question_followup', args=[self.product.pk, question.pk])
        response = self.followup(question)
        self.assertEqual(parse_qs(urlparse(response.url).query)['next'], [self.detail_url() + f'?questions_page=1#product-question-{question.pk}'])
        for user in [self.owner, self.admin]:
            self.client.force_login(user)
            self.followup(question)
        self.assertEqual(self.client.get(url).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.buyer)
        self.assertEqual(strict.post(url, {'reply': 'Hỏi thêm'}).status_code, 403)
        self.client.force_login(self.buyer)
        foreign_url = reverse('buyer_product_question_followup', args=[self.other_product.pk, question.pk])
        self.assertEqual(self.client.post(foreign_url, {'reply': 'Hỏi thêm'}).status_code, 404)
        self.assertFalse(ProductAnswer.objects.exists())

    def test_followup_invalid_form_stays_on_correct_thread_page(self):
        question = self.question()
        for index in range(11):
            self.question()
        self.client.force_login(self.buyer)
        response = self.followup(question, 'x' * 1001)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context['questions_page'].number, 2)
        thread = next(row for row in response.context['questions_page'] if row.pk == question.pk)
        self.assertTrue(thread.reply_form.is_bound)
        self.assertIn('reply', thread.reply_form.errors)
        self.assertContains(response, f'id="product-question-{question.pk}"', status_code=400)
        response = self.followup(question, '  ')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ProductAnswer.objects.exists())

    def test_followup_is_atomic_and_unavailable_for_paused_shop(self):
        question = self.question(status=True)
        self.client.force_login(self.buyer)
        with patch.object(ProductQuestion, 'save', side_effect=IntegrityError('failed')):
            self.assertEqual(self.followup(question).status_code, 503)
        self.assertFalse(ProductAnswer.objects.exists())
        question.refresh_from_db()
        self.assertTrue(question.status)
        self.shop.status = 'SUSPENDED'
        self.shop.save(update_fields=['status'])
        self.assertEqual(self.followup(question).status_code, 400)
        self.assertFalse(ProductAnswer.objects.exists())

    def test_followup_form_ids_are_unique_and_content_is_escaped(self):
        first, second = self.question(), self.question()
        self.client.force_login(self.buyer)
        response = self.client.get(self.detail_url())
        for question in [first, second]:
            self.assertContains(response, f'id="id_reply_{question.pk}_reply"', count=1)
        self.followup(first, '<script>followup()</script>')
        response = self.client.get(self.detail_url())
        self.assertContains(response, '&lt;script&gt;followup()&lt;/script&gt;')
        self.assertNotContains(response, '<script>followup()</script>')
