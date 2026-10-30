
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

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
        Ticket.objects.create(
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



class PasswordResetFlowTests(APITestCase):
    """Forgot -> reset flow (API + email link) and change-password."""

    def setUp(self):
        self.user = User.objects.create_user(
            'resetme', 'reset@example.com', 'OldPass12345', role='customer'
        )

    def test_forgot_password_sends_link_email(self):
        from django.core import mail
        r = self.client.post(reverse('forgot-password'), {'email': 'reset@example.com'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/reset-password/?uid=', mail.outbox[0].body)

    def test_forgot_password_unknown_email_same_response(self):
        from django.core import mail
        r = self.client.post(reverse('forgot-password'), {'email': 'nobody@example.com'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_forgot_password_mail_failure_does_not_leak_or_crash(self):
        """SMTP down => still 200 (a 500 would reveal that the email is registered)."""
        from unittest import mock
        with mock.patch('accounts.views.forgot_reset_view.send_mail', side_effect=Exception('smtp down')):
            r = self.client.post(reverse('forgot-password'), {'email': 'reset@example.com'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('debug', r.data)  # tests run with DEBUG=False

    def test_forgot_password_debug_hint_only_in_debug(self):
        from django.test import override_settings
        with override_settings(DEBUG=True):
            r = self.client.post(reverse('forgot-password'), {'email': 'nobody@example.com'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('No active user', r.data['debug'])

    def test_reset_password_returns_200_and_changes_password(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        r = self.client.post(
            reverse('reset-password'),
            {'uid': uid, 'token': token, 'new_password': 'BrandNew-98765'},
            format='json',
        )
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNew-98765'))

    def test_reset_password_bad_token(self):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        r = self.client.post(
            reverse('reset-password'),
            {'uid': uid, 'token': 'bad-token', 'new_password': 'BrandNew-98765'},
            format='json',
        )
        self.assertEqual(r.status_code, 400)

    def test_change_password_new_and_old_url(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        r = self.client.post(
            reverse('change-password'),
            {'old_password': 'OldPass12345', 'new_password': 'Another-Pass-5432'},
            format='json',
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn('token', r.data)
        self.assertEqual(reverse('chage-password'), '/api/chage-password/')  # old path still exists


class UIPageTests(APITestCase):
    """Web UI pages render (no template errors) for every role-less visitor."""

    def test_public_pages_render(self):
        for name in ['ui-login', 'ui-register', 'ui-forgot-password', 'ui-reset-password']:
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 200, name)

    def test_app_pages_render(self):
        for name in ['ui-dashboard', 'ui-tickets', 'ui-ticket-new', 'ui-profile',
                     'ui-manage-users', 'ui-manage-setup', 'ui-manage-settings']:
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 200, name)

    def test_login_page_links_to_forgot_and_register(self):
        html = self.client.get(reverse('ui-login')).content.decode()
        self.assertIn('/forgot-password/', html)
        self.assertIn('/register/', html)


class SuperuserRoleTests(APITestCase):
    def test_superuser_gets_admin_role(self):
        u = User.objects.create_superuser('root', 'root@example.com', 'Root-Pass-12345')
        self.assertEqual(u.role, 'admin')



class LoginLockoutTests(APITestCase):
    """5 galat attempts free, 6th par lock (1 min), phir 2 min, 5 min ..."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = User.objects.create_user('lockme', 'l@example.com', 'RightPass-12345')
        self.url = reverse('login')

    def wrong(self, username='lockme'):
        return self.client.post(self.url, {'username': username, 'password': 'nope'}, format='json')

    def test_five_wrong_attempts_then_lock(self):
        for expected_left in (4, 3, 2, 1, 0):
            r = self.wrong()
            self.assertEqual(r.status_code, 401)
            self.assertEqual(r.data['attempts_left'], expected_left)
        r = self.wrong()                      # 6th wrong attempt
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.data['retry_after'], 60)
        self.assertEqual(r['Retry-After'], '60')

    def test_correct_password_also_rejected_while_locked(self):
        for _ in range(6):
            self.wrong()
        r = self.client.post(self.url, {'username': 'lockme', 'password': 'RightPass-12345'}, format='json')
        self.assertEqual(r.status_code, 429)

    def test_lock_time_increases_after_it_expires(self):
        import time
        from unittest import mock
        for _ in range(6):
            self.wrong()                      # 1 minute lock
        later = time.time() + 61              # 1 min baad lock khatam
        with mock.patch('time.time', return_value=later):
            r = self.wrong()                  # phir galat -> ab 2 minute
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.data['retry_after'], 120)

    def test_success_resets_counter(self):
        for _ in range(3):
            self.wrong()
        ok = self.client.post(self.url, {'username': 'lockme', 'password': 'RightPass-12345'}, format='json')
        self.assertEqual(ok.status_code, 200)
        for _ in range(5):                    # fir se 5 free attempts
            self.assertEqual(self.wrong().status_code, 401)

    def test_other_username_not_affected(self):
        User.objects.create_user('other', 'o@example.com', 'Other-Pass-12345')
        for _ in range(6):
            self.wrong()
        r = self.client.post(self.url, {'username': 'other', 'password': 'Other-Pass-12345'}, format='json')
        self.assertEqual(r.status_code, 200)

    def test_unknown_username_is_limited_too_and_case_insensitive(self):
        for _ in range(5):
            self.assertEqual(self.wrong('ghost').status_code, 401)
        self.assertEqual(self.wrong('GHOST').status_code, 429)
