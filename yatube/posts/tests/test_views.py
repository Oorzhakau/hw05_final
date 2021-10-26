import shutil
import tempfile
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.another_user = User.objects.create_user(username='StepanStepin')
        cls.second_another_user = User.objects.create_user(username='Vasilii')
        cls.user = User.objects.create_user(username='IvanIvanov')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug-group',
            description='Тестовое описание группы',
        )
        cls.another_group = Group.objects.create(
            title='Тестовая группа another',
            slug='test-slug-another-group',
            description='Тестовое описание группы another',
        )
        arr_posts = [
            Post(
                author=cls.another_user,
                text=f'Пост {i}',
            )
            for i in range(1, 7)]
        arr_posts.extend([
            Post(
                author=cls.user,
                text=f'Пост группы {i}',
                group=cls.group,
            ) for i in range(7, 13)])
        Post.objects.bulk_create(arr_posts)
        for ind, post in enumerate(Post.objects.all()):
            post.pub_date += timedelta(ind)
            post.save()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsPagesTests.user)

    def compare_two_posts(self, first_post: Post, second_post: Post) -> None:
        self.assertEqual(first_post.id, second_post.id)
        self.assertEqual(first_post.text, second_post.text)
        self.assertEqual(first_post.author, second_post.author)
        self.assertEqual(first_post.group, second_post.group)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={
                    'slug': PostsPagesTests.group.slug
                }): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={
                    'username': PostsPagesTests.user.username
                }): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={
                    'post_id': Post.objects.first().id
                }): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={
                    'post_id': Post.objects.filter(
                        author=PostsPagesTests.user)[0].id
                }): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_posts_index_page_content_has_post_list(self):
        """Стартовая страница содержит список всех постов."""
        response = self.authorized_client.get(reverse('posts:index'))
        posts_list = response.context['page_obj'].object_list
        posts_all = Post.objects.all()
        for ind, post in enumerate(posts_list):
            self.compare_two_posts(posts_all[ind], post)

    def test_posts_group_list_page_content_only_group_posts(self):
        """Страница группы содержит посты группы."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': PostsPagesTests.group.slug}
            )
        )
        posts_list = response.context['page_obj'].object_list
        posts_group = Post.objects.filter(group=PostsPagesTests.group)
        for ind, post in enumerate(posts_list):
            self.compare_two_posts(posts_group[ind], post)

    def test_posts_profile_page_content_only_user_posts(self):
        """Странице пользователя содержит посты пользователя."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': PostsPagesTests.user.username}
            )
        )
        posts_list = response.context['page_obj'].object_list
        posts_author = Post.objects.filter(author=PostsPagesTests.user)
        for ind, post in enumerate(posts_list):
            self.compare_two_posts(posts_author[ind], post)

    def test_posts_post_detail_page_content_one_post(self):
        """Странице поста содержит пост с выбранным id."""
        post_testing = Post.objects.last()
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': post_testing.id}
            )
        )
        post = response.context['post']
        self.compare_two_posts(post, post_testing)

    def test_posts_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        post_testing = Post.objects.filter(author=PostsPagesTests.user)[0]
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': post_testing.id}
            )
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_posts_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_pages_after_add_post_without_image(self):
        """
        Проверка добавления поста на страницы:
        / - главную
        /profile/<str:username>/ - страницу профайла
        /group/<slug:slug>/ - постов группы
        """
        post = Post.objects.create(
            author=PostsPagesTests.user,
            text='Дополнительный пост',
            group=PostsPagesTests.group,
        )
        post.pub_date += timedelta(days=20)
        post.save()
        pages = [
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': PostsPagesTests.group.slug}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': PostsPagesTests.user.username}
            )
        ]
        for page in pages:
            with self.subTest(reverse_name=page):
                response = self.authorized_client.get(page)
                new_posts = response.context['page_obj'].object_list[0]
                self.assertEqual(new_posts.text, "Дополнительный пост")
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': PostsPagesTests.another_group.slug}
            )
        )
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_pages_after_add_post_with_image(self):
        """
        Проверка добавления поста с картинкой на страницы:
        / - главную
        /profile/<str:username>/ - страницу профайла
        /group/<slug:slug>/ - постов группы
        /posts/<int:post_id>/ - подробной информации о посте.
        """
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        post = Post.objects.create(
            text="Пост с изображением",
            author=PostsPagesTests.user,
            group=PostsPagesTests.group,
            image=uploaded,
        )
        post.pub_date = Post.objects.first().pub_date + timedelta(days=1)
        post.save()
        pages = {
            reverse('posts:index'): 'page_obj',
            reverse(
                'posts:profile',
                kwargs={'username': PostsPagesTests.user.username}
            ): 'page_obj',
            reverse(
                'posts:group_list',
                kwargs={'slug': PostsPagesTests.group.slug}
            ): 'page_obj',
            reverse('posts:post_detail', kwargs={'post_id': post.id}): 'post',
        }
        for page, field in pages.items():
            with self.subTest(reverse_name=page):
                response = self.authorized_client.get(page)
                if field != 'post':
                    new_posts = response.context[field].object_list[0]
                else:
                    new_posts = response.context[field]
                self.compare_two_posts(new_posts, post)

    def test_add_comment_authorized_user(self):
        """
        Добавление комментария к посту авторизованным пользователем.
        """
        post = Post.objects.first()
        comment = Comment.objects.create(
            post=post,
            author=PostsPagesTests.user,
            text='Комментарий',
        )
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': post.id})
        )
        self.assertEqual(response.context['comments'][0].post, comment.post)
        self.assertEqual(response.context['comments'][0].author,
                         comment.author)
        self.assertEqual(response.context['comments'][0].text, comment.text)

    def test_index_page_cache(self):
        new_post = Post.objects.create(
            text='Новый Пост для проверки кеша',
            author=PostsPagesTests.user,
            group=PostsPagesTests.group,
        )
        new_post.pub_date = Post.objects.first().pub_date + timedelta(days=1)
        new_post.save()
        response = self.authorized_client.get(reverse('posts:index'))
        self.compare_two_posts(
            new_post, response.context['page_obj'].object_list[0])
        new_post.delete()
        response_afther_del_new_post = self.authorized_client.get(
            reverse('posts:index'))
        self.assertEqual(
            response.content, response_afther_del_new_post.content)
        cache.clear()
        response_afther_clear_cache = self.authorized_client.get(
            reverse('posts:index'))
        self.assertNotEquals(
            response_afther_clear_cache, response_afther_del_new_post.content)

    def test_follow_authorized_client(self):
        """
        Авторизованный пользователь может подписываться на других
        пользователей и удалять их из подписок.
        """
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': PostsPagesTests.another_user.username})
        )
        follow = Follow.objects.filter(
            user=PostsPagesTests.user,
            author=PostsPagesTests.another_user
        )
        self.assertIsNotNone(follow)
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': PostsPagesTests.another_user.username})
        )
        follow = Follow.objects.filter(
            user=PostsPagesTests.user,
            author=PostsPagesTests.another_user
        )
        self.assertFalse(follow.exists())

    def test_follow_correct_context_after_author_add_new_post(self):
        """
        Новая запись пользователя появляется в ленте тех, кто на него подписан
        и не появляется в ленте тех, кто не подписан.
        """
        new_post = Post.objects.create(
            text='Пост от автора в ленте',
            author=PostsPagesTests.another_user,
        )
        new_post.pub_date = Post.objects.first().pub_date + timedelta(days=1)
        new_post.save()
        Follow.objects.create(
            user=PostsPagesTests.user,
            author=PostsPagesTests.another_user)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.compare_two_posts(
            response.context['page_obj'].object_list[0],
            new_post)
        self.authorized_client.force_login(PostsPagesTests.second_another_user)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertFalse(response.context['page_obj'].object_list.exists())


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='IvanIvanov')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug-group',
            description='Тестовое описание группы',
        )
        arr_posts = [
            Post(
                author=cls.user,
                group=cls.group,
                text=f'Пост {i}',
            )
            for i in range(1, 14)
        ]
        Post.objects.bulk_create(arr_posts)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PaginatorViewsTest.user)

    def test_first_page_contains_ten_records(self):
        """
        Пагинатор первой страниц из списка, отображает по 10 объектов:
        index - стартовой страницы;
        group_list - страницы постов группы;
        profile - страницы постов пользователя.
        """
        list_address = [
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': PaginatorViewsTest.group.slug}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': PaginatorViewsTest.user.username}
            ),
        ]
        for address in list_address:
            response = self.authorized_client.get(address)
            self.assertEqual(
                len(response.context['page_obj']), settings.POST_COUNT,
                f'{response.context}'
            )

    def test_second_page_contains_three_records(self):
        """
        Проверка пагинатора страниц (последней страницы):
        index - стартовой страницы;
        group_list - страницы постов группы;
        profile - страницы постов пользователя.
        Должно отображаться 3 объекта.
        """
        list_address = [
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': PaginatorViewsTest.group.slug}),
            reverse(
                'posts:profile',
                kwargs={'username': PaginatorViewsTest.user.username}),
        ]
        for address in list_address:
            response = self.authorized_client.get(address + '?page=2')
            self.assertEqual(
                len(response.context['page_obj']),
                Post.objects.count() % settings.POST_COUNT
            )
