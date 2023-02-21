from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from ..models import Post, Group
from django.core.cache import cache

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.user = User.objects.create_user(username='no_name')
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

    def setUp(self) -> None:
        self.guest_client = Client()
        self.authorized_author_client = Client()
        self.authorized_author_client.force_login(self.author)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_if_urls_work_with_correct_type_of_user(self):
        cache.clear()
        users_for_urls = {
            '/': self.guest_client,
            f'/group/{self.group.slug}/': self.guest_client,
            f'/profile/{self.author.username}/': self.guest_client,
            f'/posts/{self.post.id}/': self.guest_client,
            '/create/': self.authorized_client,
            f'/posts/{self.post.id}/edit/': self.authorized_author_client,
            '/follow/': self.authorized_client
        }
        for address, user in users_for_urls.items():
            with self.subTest(address=address):
                response = user.get(address)
                self.assertEqual(response.status_code, 200)

    def test_if_urls_work_with_correct_template(self):
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.author.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/unexisting_page/': 'core/404.html',
            '/follow/': 'posts/follow.html'
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_author_client.get(address)
                self.assertTemplateUsed(response, template)

    # Проверяем редиректы для неавторизованного пользователя
    def test_post_create_url_redirect_for_anonymous(self):
        response = self.guest_client.get('/create/')
        self.assertEqual(response.status_code, 302)

    def test_post_edit_url_redirect_for_anonymous(self):
        response = self.guest_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, 302)

    def test_follow_redirect_for_anonymous(self):
        response = self.guest_client.get('/follow/')
        self.assertEqual(response.status_code, 302)

    # Проверяем переход на несуществующую страницу
    def test_unexisting_url_does_not_exist_at_desired_location(self):
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, 404)
