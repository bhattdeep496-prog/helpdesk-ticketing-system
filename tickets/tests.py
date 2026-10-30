import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from tickets.models import Notification, Priority, Tag, Ticket
from tickets.site_settings import SystemSettings

User = get_user_model()


class BaseAPITest(TestCase):
    """Common setup: users of each role, a priority, a tag, and a temp media folder."""

    def setUp(self):
        media = tempfile.mkdtemp()
        self.enterContext(override_settings(MEDIA_ROOT=media))
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)

        self.admin = User.objects.create_user('admin1', 'a@x.com', 'pass12345', role='admin')
        self.support = User.objects.create_user('support1', 's@x.com', 'pass12345', role='support')
        self.customer = User.objects.create_user('cust1', 'c@x.com', 'pass12345', role='customer')
        self.customer2 = User.objects.create_user('cust2', 'c2@x.com', 'pass12345', role='customer')

        Priority.objects.get_or_create(name='Medium', defaults={'level': 2})
        self.tag = Tag.objects.create(name='bug')

    def client_for(self, user):
        client = APIClient()
        token, _ = Token.objects.get_or_create(user=user)
        client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        return client

    def make_ticket(self, user, **extra):
        data = {'title': 'Printer broken', 'description': 'It will not print.', 'priority': 'medium'}
        data.update(extra)
        return self.client_for(user).post('/api/my-tickets/', data, format='json')


class AuthTests(BaseAPITest):
    def test_login_returns_token(self):
        res = APIClient().post('/api/login/', {'username': 'cust1', 'password': 'pass12345'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('token', res.data)

    def test_login_wrong_password_is_rejected(self):
        res = APIClient().post('/api/login/', {'username': 'cust1', 'password': 'wrong'}, format='json')
        self.assertEqual(res.status_code, 401)

    def test_login_requires_both_fields(self):
        res = APIClient().post('/api/login/', {'username': 'cust1'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_token_gives_access_and_anonymous_does_not(self):
        self.assertEqual(self.client_for(self.customer).get('/api/my-tickets/').status_code, 200)
        self.assertIn(APIClient().get('/api/my-tickets/').status_code, (401, 403))


class TicketTests(BaseAPITest):
    def test_customer_creates_ticket_with_tag(self):
        res = self.make_ticket(self.customer, tags=[self.tag.id])
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'new')
        self.assertEqual(res.data['tag_names'], ['bug'])
        self.assertEqual(Ticket.objects.get(pk=res.data['id']).created_by, self.customer)

    def test_invalid_priority_is_rejected(self):
        res = self.make_ticket(self.customer, priority='does_not_exist')
        self.assertEqual(res.status_code, 400)

    def test_customer_cannot_see_another_customers_ticket(self):
        ticket_id = self.make_ticket(self.customer).data['id']
        other = self.client_for(self.customer2)
        self.assertEqual(other.get(f'/api/my-tickets/{ticket_id}/').status_code, 404)
        self.assertEqual(other.get('/api/tickets/').data['count'], 0)

    def test_admin_sees_all_tickets(self):
        self.make_ticket(self.customer)
        self.make_ticket(self.customer2)
        res = self.client_for(self.admin).get('/api/tickets/')
        self.assertEqual(res.data['count'], 2)

    def test_search_by_keyword(self):
        self.make_ticket(self.customer, title='VPN is down')
        self.make_ticket(self.customer, title='Invoice question')
        res = self.client_for(self.customer).get('/api/tickets/?search=vpn')
        self.assertEqual(res.data['count'], 1)

    def test_filter_by_tag(self):
        self.make_ticket(self.customer, tags=[self.tag.id])
        self.make_ticket(self.customer)
        client = self.client_for(self.customer)
        self.assertEqual(client.get('/api/tickets/?tag=bug').data['count'], 1)
        self.assertEqual(client.get('/api/tickets/?tag=nothing').data['count'], 0)

    def test_customer_can_edit_only_while_new(self):
        ticket_id = self.make_ticket(self.customer).data['id']
        Ticket.objects.filter(pk=ticket_id).update(status='in_progress')
        res = self.client_for(self.customer).patch(
            f'/api/my-tickets/{ticket_id}/', {'title': 'Changed'}, format='json')
        self.assertEqual(res.status_code, 403)


class TagTests(BaseAPITest):
    def test_admin_can_create_tag(self):
        res = self.client_for(self.admin).post('/api/admin/tags/', {'name': 'urgent'}, format='json')
        self.assertEqual(res.status_code, 201)

    def test_customer_cannot_create_tag(self):
        res = self.client_for(self.customer).post('/api/admin/tags/', {'name': 'urgent'}, format='json')
        self.assertIn(res.status_code, (401, 403))

    def test_duplicate_tag_is_rejected(self):
        res = self.client_for(self.admin).post('/api/admin/tags/', {'name': 'bug'}, format='json')
        self.assertEqual(res.status_code, 400)


class AttachmentTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.ticket_id = self.make_ticket(self.customer).data['id']
        self.url = f'/api/tickets/{self.ticket_id}/attachments/'

    def upload(self, *files, user=None):
        client = self.client_for(user or self.customer)
        return client.post(self.url, {'files': list(files)}, format='multipart')

    def test_valid_upload(self):
        res = self.upload(SimpleUploadedFile('shot.png', b'x' * 100, content_type='image/png'))
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(res.data), 1)

    def test_disallowed_file_type_is_rejected(self):
        res = self.upload(SimpleUploadedFile('virus.exe', b'x' * 10))
        self.assertEqual(res.status_code, 400)

    def test_too_many_files_are_rejected(self):
        cfg = SystemSettings.load()
        cfg.max_files_per_request = 1
        cfg.save()
        res = self.upload(
            SimpleUploadedFile('a.png', b'x'), SimpleUploadedFile('b.png', b'x'))
        self.assertEqual(res.status_code, 400)

    def test_file_over_size_limit_is_rejected(self):
        cfg = SystemSettings.load()
        cfg.max_upload_size_mb = 1
        cfg.save()
        res = self.upload(SimpleUploadedFile('big.png', b'x' * (2 * 1024 * 1024)))
        self.assertEqual(res.status_code, 400)

    def test_other_customer_cannot_upload_to_ticket(self):
        res = self.upload(SimpleUploadedFile('a.png', b'x'), user=self.customer2)
        self.assertIn(res.status_code, (403, 404))


class AdminSettingsTests(BaseAPITest):
    def test_customer_cannot_open_settings(self):
        res = self.client_for(self.customer).get('/api/admin/settings/')
        self.assertIn(res.status_code, (401, 403))

    def test_admin_can_update_settings(self):
        res = self.client_for(self.admin).patch(
            '/api/admin/settings/', {'max_upload_size_mb': 3}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(SystemSettings.load().max_upload_size_mb, 3)

    def test_settings_validation(self):
        res = self.client_for(self.admin).patch(
            '/api/admin/settings/', {'max_upload_size_mb': 999}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_public_registration_can_be_switched_off(self):
        self.client_for(self.admin).patch(
            '/api/admin/settings/', {'allow_public_registration': False}, format='json')
        res = APIClient().post(
            '/api/register/',
            {'username': 'newuser', 'email': 'n@x.com', 'password': 'pass12345'},
            format='json')
        self.assertEqual(res.status_code, 403)


class WebUITests(BaseAPITest):
    def test_ui_pages_render(self):
        client = APIClient()
        for url in ('/', '/login/', '/dashboard/', '/tickets/', '/tickets/new/', '/tickets/1/'):
            self.assertEqual(client.get(url).status_code, 200, url)


class EmailStatusAndDashboardExtrasTests(BaseAPITest):
    """Email status/test API (3.10) and dashboard data used by the new dashboard cards (3.5)."""

    def test_email_status_admin_only_and_no_password(self):
        r = self.client_for(self.customer).get('/api/admin/email-status/')
        self.assertEqual(r.status_code, 403)
        r = self.client_for(self.admin).get('/api/admin/email-status/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(r.json()['mode'], ('smtp', 'console'))
        self.assertFalse(any('password' in k.lower() for k in r.json()))

    def test_email_test_sends_mail_to_admin(self):
        from django.core import mail
        self.admin.email = 'boss@example.com'
        self.admin.save()
        r = self.client_for(self.admin).post('/api/admin/email-test/', {}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(mail.outbox[-1].to, ['boss@example.com'])

    def test_email_test_needs_admin_email(self):
        self.admin.email = ''
        self.admin.save()
        r = self.client_for(self.admin).post('/api/admin/email-test/', {}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_admin_dashboard_has_category_and_staff_performance(self):
        r = self.client_for(self.admin).get('/api/dashboard/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('by_category', r.json())
        self.assertIn('staff_performance', r.json())



class InAppNotificationTests(BaseAPITest):
    """Bell notifications (database) + live push. WebSocket fail ho to bhi ticket ka kaam chalna chahiye."""

    def new_ticket(self):
        return Ticket.objects.create(
            title='Printer broken', description='x', created_by=self.customer, priority='medium'
        )

    def test_new_ticket_notifies_customer(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.new_ticket()
        self.assertEqual(Notification.objects.filter(user=self.customer, kind='created').count(), 1)

    def test_status_change_notifies_customer(self):
        with self.captureOnCommitCallbacks(execute=True):
            t = self.new_ticket()
        with self.captureOnCommitCallbacks(execute=True):
            t.status = Ticket.Status.IN_PROGRESS
            t.save()
        self.assertTrue(Notification.objects.filter(user=self.customer, kind='status').exists())

    def test_assignment_notifies_staff(self):
        with self.captureOnCommitCallbacks(execute=True):
            t = self.new_ticket()
        with self.captureOnCommitCallbacks(execute=True):
            t.assigned_to = self.support
            t.save()
        self.assertTrue(Notification.objects.filter(user=self.support, kind='assigned').exists())

    def test_api_returns_only_own_and_mark_read(self):
        Notification.objects.create(user=self.customer, kind='created', message='mine')
        Notification.objects.create(user=self.customer2, kind='created', message='not mine')
        client = self.client_for(self.customer)
        r = client.get('/api/notifications/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['unread_count'], 1)
        self.assertEqual([n['message'] for n in r.json()['results']], ['mine'])
        r = client.post('/api/notifications/read/', {}, format='json')
        self.assertEqual(r.json()['unread_count'], 0)
        # doosre user ki notification touch nahi hui
        self.assertEqual(Notification.objects.filter(user=self.customer2, is_read=False).count(), 1)

    def test_notifications_need_login(self):
        self.assertEqual(APIClient().get('/api/notifications/').status_code, 401)

    def test_broken_channel_layer_does_not_break_ticket_creation(self):
        from unittest import mock
        with mock.patch('channels.layers.get_channel_layer', side_effect=RuntimeError('redis down')):
            with self.captureOnCommitCallbacks(execute=True):
                t = self.new_ticket()
        self.assertTrue(Ticket.objects.filter(pk=t.pk).exists())
        self.assertEqual(Notification.objects.filter(user=self.customer).count(), 1)


class FollowUpTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        res = self.make_ticket(self.customer)
        self.ticket_id = res.data['id']
        self.url = f'/api/tickets/{self.ticket_id}/follow-up/'

    def test_customer_can_send_follow_up(self):
        res = self.client_for(self.customer).post(self.url, {'message': 'Any update?'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Follow-up sent', res.data['detail'])

    def test_admin_cannot_send_follow_up(self):
        res = self.client_for(self.admin).post(self.url, {'message': 'Admin check'}, format='json')
        self.assertEqual(res.status_code, 403)
        self.assertIn('Only customers can send follow-ups', res.data.get('detail', ''))

    def test_support_cannot_send_follow_up(self):
        res = self.client_for(self.support).post(self.url, {'message': 'Staff check'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_customer_cannot_follow_up_on_another_customer_ticket(self):
        res = self.client_for(self.customer2).post(self.url, {'message': 'Intruder'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_cannot_follow_up_on_closed_ticket(self):
        Ticket.objects.filter(pk=self.ticket_id).update(status='closed')
        res = self.client_for(self.customer).post(self.url, {'message': 'Reopen please'}, format='json')
        self.assertEqual(res.status_code, 400)
