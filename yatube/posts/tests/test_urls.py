from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls.base import reverse

from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='IvanIvanov')
        cls.another_user = User.objects.create_user(username='PetrPetrov')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group_slug',
            description='Тестовое описание',
        )
        cls.post_without_group = Post.objects.create(
            author=cls.user,
            text='Тестовый текст поста без группы',
        )
        cls.post_with_group = Post.objects.create(
            author=cls.user,
            text='Тестовый текст поста с групппой',
            group=cls.group,
        )
        cls.post_another_user = Post.objects.create(
            author=cls.another_user,
            text='Тестовый другого пользователя',
        )

    def test_urls_unauthorized_user(self):
        """
        Проверяем отображение следующих страниц для
        неавторизованного пользователя:
        / - стартовой
        /group/<slug:slug>/ - постов группы
        /profile/<str:username>/ - профиля пользователя
        /posts/<int:post_id>/ - подробной информации о посте.
        """
        url_names = [
            '/',
            f'/group/{PostURLTests.group.slug}/',
            f'/profile/{PostURLTests.user.username}/',
            f'/posts/{PostURLTests.post_without_group.id}/',
        ]
        for url in url_names:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_unexisting_page(self):
        """Проверка неизвестной страницы."""
        response = self.client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_redirect_anonymous(self):
        """
        Проверяем перенаправление неавторизованного пользователя
        со следующих страниц:
        /create/ - создание поста
        /posts/<int:post_id>/edit/ - подробной информации о посте.
        """
        url_names = {
            '/create/': '/auth/login/?next=/create/',
            f'/posts/{PostURLTests.post_without_group.id}/edit/': (
                '/auth/login/?next=/posts/'
                f'{PostURLTests.post_without_group.id}/edit/'),
        }
        for url, redirect_url in url_names.items():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    redirect_url
                )

    def test_post_create_url_exists_at_desired_location(self):
        """Страница /creat/ доступна авторизованному пользователю."""
        response = PostURLTests.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_url(self):
        """Страница /posts/<int:post_id>/edit/ редактирования поста автора."""
        response = PostURLTests.authorized_client.get(
            f'/posts/{PostURLTests.post_without_group.id}/edit/'
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_redirect_another_user(self):
        response = PostURLTests.authorized_client.get(
            f'/posts/{PostURLTests.post_another_user.id}/edit/'
        )
        self.assertRedirects(
            response,
            f'/posts/{PostURLTests.post_another_user.id}/'
        )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/group_slug/': 'posts/group_list.html',
            '/profile/IvanIvanov/': 'posts/profile.html',
            f'/posts/{PostURLTests.post_without_group.id}/':
                'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{PostURLTests.post_without_group.id}/edit/':
                 'posts/create_post.html',
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_add_comment_url_unauthorized_user(self):
        """
        Проверяем перенаправление неавторизованного пользователя
        со страницы добавления комментария
        """
        response = self.client.get(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': Post.objects.first().id})
        )
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{Post.objects.first().id}/comment/'
        )
