"""Email notifications (spec 3.9). Development me email terminal me print hota hai."""
import logging

from django.conf import settings
from django.core.mail import send_mail


log = logging.getLogger(__name__)


def notifications_enabled():
    """Admin settings (database) me notifications_enabled False ho to sab emails band."""
    from .site_settings import SystemSettings
    return SystemSettings.load().notifications_enabled


def _name(user):
    return user.get_full_name() or user.username


def _status_label(value):
    from .models import Ticket
    try:
        return Ticket.Status(value).label
    except ValueError:
        return value


def _send(user, subject, message):
    if not notifications_enabled():
        return
    if user is None or not user.is_active or not user.email:
        return
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=None,
            recipient_list=[user.email],
        )
    except Exception:
        # Email fail ho to bhi ticket ka kaam na ruke
        log.exception('Could not send notification email to %s', user.email)


def serialize_notification(n):
    return {
        'id': n.pk,
        'kind': n.kind,
        'message': n.message,
        'ticket_id': n.ticket_id,
        'url': f'/tickets/{n.ticket_id}/' if n.ticket_id else '/tickets/',
        'is_read': n.is_read,
        'created_at': n.created_at.isoformat(),
    }


def push(user, kind, message, ticket=None):
    """
    In-app notification: database me save karo (bell icon ke liye) aur WebSocket se
    live bhejo. Yahan kuch bhi fail ho to ticket ka kaam kabhi nahi rukta.
    """
    if user is None or not user.is_active:
        return
    try:
        from .models import Notification
        note = Notification.objects.create(
            user=user, ticket=ticket, kind=kind, message=message[:255],
        )
    except Exception:
        log.exception('Could not save notification for %s', user)
        return
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        if layer is None:  # CHANNEL_LAYERS settings me nahi hai: bell phir bhi chalta hai
            return
        async_to_sync(layer.group_send)(
            f'user_{user.pk}',
            {'type': 'notify', 'payload': serialize_notification(note)},
        )
    except Exception:
        log.exception('Could not push live notification to %s', user)


def notify_ticket_created(ticket):
    """Customer ko confirmation: ticket ban gayi."""
    push(ticket.created_by, 'created',
         f'Ticket #{ticket.pk} created: {ticket.title}', ticket)
    _send(
        ticket.created_by,
        f'[Ticket #{ticket.pk}] We received your request: {ticket.title}',
        f'Hello {_name(ticket.created_by)},\n\n'
        f'Your ticket has been created.\n\n'
        f'Ticket:   #{ticket.pk} {ticket.title}\n'
        f'Priority: {ticket.priority}\n'
        f'Status:   {_status_label(ticket.status)}\n\n'
        f'Our support team will get back to you soon.',
    )


def notify_status_changed(ticket, old_status):
    """Ticket ke owner (customer) ko: status badal gaya."""
    push(ticket.created_by, 'status',
         f'Ticket #{ticket.pk}: {_status_label(old_status)} \u2192 {_status_label(ticket.status)}',
         ticket)
    _send(
        ticket.created_by,
        f'[Ticket #{ticket.pk}] Status changed: '
        f'{_status_label(old_status)} -> {_status_label(ticket.status)}',
        f'Hello {_name(ticket.created_by)},\n\n'
        f'The status of your ticket has changed.\n\n'
        f'Ticket: #{ticket.pk} {ticket.title}\n'
        f'Status: {_status_label(old_status)} -> {_status_label(ticket.status)}',
    )


def notify_assigned(ticket):
    """Support staff ko: nayi ticket assign hui."""
    staff = ticket.assigned_to
    push(staff, 'assigned', f'Ticket #{ticket.pk} assigned to you: {ticket.title}', ticket)
    _send(
        staff,
        f'[Ticket #{ticket.pk}] Assigned to you: {ticket.title}',
        f'Hello {_name(staff)},\n\n'
        f'A ticket has been assigned to you.\n\n'
        f'Ticket:   #{ticket.pk} {ticket.title}\n'
        f'Customer: {ticket.created_by.username}\n'
        f'Priority: {ticket.priority}\n'
        f'Status:   {_status_label(ticket.status)}',
    )