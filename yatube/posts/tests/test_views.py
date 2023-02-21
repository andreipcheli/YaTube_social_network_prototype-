import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from ..models import Post, Group, Follow
from django.urls import reverse
from django import forms
from django.core.cache import cache

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class Views_Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.user = User.objects.create_user(username='user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self) -> None:
        self.guest_client = Client()
        self.authorized_author_client = Client()
        self.authorized_author_client.force_login(self.author)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_if_views_use_correct_template(self):
        cache.clear()
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}): (
                'posts/group_list.html'),
            reverse('posts:profile', kwargs={'username': 'author'}): (
                'posts/profile.html'),
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}): (
                'posts/post_detail.html'),
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}): (
                'posts/create_post.html'),
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_shows_correct_context(self):
        cache.clear()
        response = self.authorized_author_client.get(reverse('posts:index'))
        page_obj = response.context['page_obj']
        first_post = page_obj[0]
        self.assertEqual(first_post.author, self.author)
        self.assertEqual(first_post.group, self.group)
        self.assertEqual(first_post.text, self.post.text)

    def test_group_posts_shows_correct_context(self):
        response = self.authorized_author_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        page_obj = response.context['page_obj']
        first_post = page_obj[0]
        group = response.context['group']
        self.assertEqual(first_post.author, self.author)
        self.assertEqual(first_post.group, self.group)
        self.assertEqual(first_post.text, self.post.text)
        self.assertEqual(group, self.group)

    def test_post_detail_shows_correct_context(self):
        response = self.authorized_author_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        post_num = response.context['post_num']
        post = response.context['post']
        self.assertEqual(post_num, (
            Post.objects.filter(author=self.author).count()))
        self.assertEqual(post, self.post)

    def test_profile_shows_correct_context(self):
        response = self.authorized_author_client.get(
            reverse('posts:profile', kwargs={'username': 'author'}))
        page_obj = response.context['page_obj']
        first_post = page_obj[0]
        post_num = response.context['post_num']
        author = response.context['author']
        self.assertEqual(first_post.author, self.author)
        self.assertEqual(first_post.group, self.group)
        self.assertEqual(author, self.author)
        self.assertEqual(post_num, (
            Post.objects.filter(author=self.author).count()))

    def test_post_create_shows_correct_context(self):
        response = self.authorized_author_client.get(
            reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                # Проверяет, что поле формы является экземпляром
                # указанного класса
                self.assertIsInstance(form_field, expected)

    def test_post_edit_shows_correct_context(self):
        response = self.authorized_author_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                # Проверяет, что поле формы является экземпляром
                # указанного класса
                self.assertIsInstance(form_field, expected)
        is_edit = response.context['is_edit']
        post_id = response.context['post_id']
        self.assertEqual(is_edit, True)
        self.assertEqual(post_id, self.post.id)

    def test_paginator(self):
        cache.clear()
        # Creating 10 test posts
        for post_num in range(10):
            Post.objects.create(
                author=self.author,
                text=f'Тестовый_пост {post_num+1}',
                group=self.group
            )
        addresses = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': 'author'})]
        for address in addresses:
            with self.subTest(address=address):
                response = self.client.get(address)
                # Проверка: количество постов на первой странице равно 10.
                self.assertEqual(len(response.context['page_obj']), 10)
                response = self.client.get(address + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 1)

    def test_new_post_displayed_in_group_index_profile(self):
        cache.clear()
        post = Post.objects.create(
            author=self.author,
            text='Тестовый_пост',
            group=self.group
        )
        response = self.client.get(reverse('posts:index'))
        self.assertIn(post, response.context['page_obj'])
        response = self.authorized_author_client.get(
            reverse('posts:profile', kwargs={'username': 'author'}))
        self.assertIn(post, response.context['page_obj'])
        response = self.authorized_author_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertIn(post, response.context['page_obj'])
        group = Group.objects.create(
            title='Группа',
            slug='slug',
            description='Тестовое описание',
        )
        response = self.authorized_author_client.get(
            reverse('posts:group_list', kwargs={'slug': group.slug}))
        self.assertNotIn(post, response.context['page_obj'])

    def test_post_with_picture(self):
        cache.clear()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        post = Post.objects.create(
            author=self.author,
            text='Тестовый_пост',
            group=self.group,
            image=uploaded
        )
        addresses = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': 'author'})]
        for address in addresses:
            with self.subTest(address=address):
                response = self.authorized_author_client.get(address)
                page_obj = response.context['page_obj']
                first_post = page_obj[0]
                self.assertEqual(first_post.image, post.image)

    def test_post_with_picture_in_post_detail(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        post = Post.objects.create(
            author=self.author,
            text='Тестовый_пост',
            group=self.group,
            image=uploaded
        )
        address = reverse('posts:post_detail', kwargs={'post_id': post.id})
        response = self.authorized_author_client.get(address)
        expected = response.context['post'].image
        self.assertEqual(expected, post.image)

    def test_cache(self):
        response = self.guest_client.get(reverse('posts:index'))
        content_before = response.content
        self.post.delete
        response_after = self.guest_client.get(reverse('posts:index'))
        content_after = response_after.content
        self.assertEqual(content_before, content_after)
        cache.clear()
        response_after_cache_clear = self.guest_client.get(reverse(
            'posts:index'))
        self.assertNotEqual(response_after_cache_clear, response_after)

    def test_follow_page_shows_correct_context(self):
        Follow.objects.create(
            author = self.author,
            user=self.user
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        page_obj = response.context['page_obj']
        first_post = page_obj[0]
        self.assertEqual(first_post.author, self.author)
        self.assertEqual(first_post.group, self.group)
        self.assertEqual(first_post.text, self.post.text)

    def test_func_follow_works_correct(self):
        response_before = self.authorized_client.get(reverse('posts:follow_index'))
        self.authorized_client.get(reverse('posts:profile_follow', kwargs={'username': self.author.username}))
        response_after = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotEqual(response_before.content, response_after.content)
        
    def test_func_unfollow_works_correct(self):
        Follow.objects.create(
            author = self.author,
            user=self.user
        )
        response_before = self.authorized_client.get(reverse('posts:follow_index'))
        self.authorized_client.get(reverse('posts:profile_unfollow', kwargs={'username': self.author.username}))
        response_after = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotEqual(response_before.content, response_after.content)

