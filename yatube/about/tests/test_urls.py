from django.test import Client, TestCase


class StaticURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_author(self):
        """Проверяем страницу об авторе."""
        response = self.guest_client.get('/about/author/')
        self.assertEqual(response.status_code, 200)

    def test_tech(self):
        """Проверяем страницу об используемых технологиях."""
        response = self.guest_client.get('/about/tech/')
        self.assertEqual(response.status_code, 200)
