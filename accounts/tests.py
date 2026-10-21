
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from tickets.models import Priority, Ticket

User = get_user_model()


class AuthTests(APITestCase):
    def setUp(self):
        self.username = 'testuser'
        self.password = 'password123'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email='test@example.com'
        )
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')

    def test_login_success(self):
        data = {'username': self.username, 'password': self.password}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['username'], self.username)

    def test_login_invalid_credentials(self):
        data = {'username': self.username, 'password': 'wrongpassword'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_logout_authenticated(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        response = self.client.post(self.logout_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_logout_unauthenticated(self):
        response = self.client.post(self.logout_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PriorityModelTests(APITestCase):
    def test_default_priorities_created_after_migrate(self):
        expected = {
            'low': ('Low', 1),
            'medium': ('Medium', 2),
            'high': ('High', 3),
            'critical': ('Critical', 4),
        }

        for slug, (name, level) in expected.items():
            priority = Priority.objects.filter(slug=slug).first()
            self.assertIsNotNone(priority, f'{name} priority missing')
            self.assertEqual(priority.name, name)
            self.assertEqual(priority.level, level)

    def test_priority_slug_generated_from_name(self):
        priority = Priority.objects.create(name='Blocker', level=5)
        self.assertEqual(priority.slug, 'blocker')

    def test_inactive_priority_can_be_saved(self):
        priority = Priority.objects.create(
            name='Urgent',
            level=5,
            is_active=False
        )
        self.assertFalse(priority.is_active)


class PriorityAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            password='AdminPass123!',
            email='admin@example.com',
            role='admin'
        )
        self.customer = User.objects.create_user(
            username='customer',
            password='CustomerPass123!',
            email='customer@example.com',
            role='customer'
        )

        
        self.priority, created = Priority.objects.get_or_create(
            slug='medium',
            defaults={
               'name': 'Medium',
               'level': 2,
            }
        )

        self.list_url = reverse('priority-list-create')
        self.detail_url = reverse(
            'priority-detail',
            kwargs={'pk': self.priority.pk}
        )

    def test_admin_can_create_priority(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.list_url,
            {'name': 'Blocker', 'level': 5},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Priority.objects.filter(slug='blocker').exists()
        )

    def test_customer_cannot_create_priority(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            self.list_url,
            {'name': 'Blocker', 'level': 5},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_sees_only_active_priorities(self):
        Priority.objects.create(
            name='Hidden',
            level=5,
            is_active=False
        )
        self.client.force_authenticate(user=self.customer)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_slugs = [item['slug'] for item in response.data]
        self.assertNotIn('hidden', returned_slugs)

    def test_admin_can_see_inactive_priorities(self):
        inactive = Priority.objects.create(
            name='Hidden',
            level=5,
            is_active=False
        )
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_slugs = [item['slug'] for item in response.data]
        self.assertIn(inactive.slug, returned_slugs)

    def test_customer_cannot_update_priority(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.patch(
            self.detail_url,
            {'level': 3},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_deactivate_priority(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.detail_url,
            {'is_active': False},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.priority.refresh_from_db()
        self.assertFalse(self.priority.is_active)

    def test_admin_cannot_delete_priority_used_by_ticket(self):
        ticket = Ticket.objects.create(
            title='Test ticket',
            description='Testing priority deletion',
            priority=self.priority.slug,
            created_by=self.customer
        )

        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            Priority.objects.filter(pk=self.priority.pk).exists()
        )
