"""Email notifications (spec 3.9). Development me email terminal me print hota hai."""
import logging

from django.conf import settings
from django.core.mail import send_mail

log = logging.getLogger(__name__)


def notifications_enabled():
    """settings.py me NOTIFICATIONS_ENABLED = False karne par sab emails band."""
    return getattr(settings, 'NOTIFICATIONS_ENABLED', True)


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


def notify_ticket_created(ticket):
    """Customer ko confirmation: ticket ban gayi."""
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