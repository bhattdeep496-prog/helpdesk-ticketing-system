"""
Ticket save hone par emails (API, admin panel, kahin se bhi badlo - sab jagah chalta hai):
  - nayi ticket        -> customer ko confirmation (aur assigned ho to staff ko bhi)
  - status badla       -> customer ko
  - staff assign hua   -> us support staff ko
"""
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Ticket
from .notifications import (
    notify_assigned, notify_status_changed, notify_ticket_created,
)


@receiver(pre_save, sender=Ticket)
def remember_old_values(sender, instance, **kwargs):
    instance._old_status = None
    instance._old_assigned_to_id = None
    if instance.pk:
        old = (
            Ticket.objects.filter(pk=instance.pk)
            .values('status', 'assigned_to_id').first()
        )
        if old:
            instance._old_status = old['status']
            instance._old_assigned_to_id = old['assigned_to_id']


@receiver(post_save, sender=Ticket)
def send_ticket_notifications(sender, instance, created, **kwargs):
    ticket = instance

    if created:
        def after_create():
            notify_ticket_created(ticket)
            if ticket.assigned_to_id:
                notify_assigned(ticket)
        transaction.on_commit(after_create)
        return

    old_status = getattr(ticket, '_old_status', None)
    old_assigned = getattr(ticket, '_old_assigned_to_id', None)

    status_changed = old_status is not None and old_status != ticket.status
    newly_assigned = (
        ticket.assigned_to_id is not None and ticket.assigned_to_id != old_assigned
    )

    if status_changed or newly_assigned:
        def after_update():
            if status_changed:
                notify_status_changed(ticket, old_status)
            if newly_assigned:
                notify_assigned(ticket)
        transaction.on_commit(after_update)