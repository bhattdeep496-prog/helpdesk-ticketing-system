from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets.models import Comment, Ticket
from tickets.site_settings import SystemSettings

User = get_user_model()


class TicketFollowUpView(APIView):
    """
    POST /api/tickets/<id>/follow-up/    body: {"message": "optional text"}

    Customer dabaye  -> ticket ke assigned staff ko follow-up jata hai
                        (assign na ho to admins ko). Sirf apne ticket par.
    Admin / Staff    -> follow-up nahi kar sakta (sirf customers ke liye hai).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        user = request.user
        ticket = get_object_or_404(Ticket, pk=pk)

        if not user.is_customer:
            raise PermissionDenied('Only customers can send follow-ups.')

        if ticket.status == Ticket.Status.CLOSED:
            raise ValidationError('A closed ticket cannot be followed up.')

        if ticket.created_by_id != user.id:
            raise PermissionDenied('You can only follow up on your own tickets.')

        message = (request.data.get('message') or '').strip()[:500]

        if ticket.assigned_to is not None:
            recipients = [ticket.assigned_to]
        else:
            recipients = list(
                User.objects.filter(is_active=True).filter(Q(role='admin') | Q(is_superuser=True))
            )

        names = ', '.join(r.username for r in recipients) or 'no one'

        body = 'Follow-up requested: please share an update on this ticket.'
        if message:
            body += f' {message}'

        Comment.objects.create(
            ticket=ticket, author=user, body=body, is_internal=False
        )

        emails = [r.email for r in recipients if r.email]
        if emails and SystemSettings.load().notifications_enabled:
            send_mail(
                subject=f'[Ticket #{ticket.pk}] Follow-up: {ticket.title}',
                message=(
                    f'{user.username} has sent a follow-up on ticket #{ticket.pk}: {ticket.title}.\n\n'
                    + (f'Message: {message}\n\n' if message else '')
                    + f'Open it here: {settings.SITE_URL}/tickets/{ticket.pk}/\n'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=emails,
                fail_silently=True,
            )

        return Response({'detail': f'Follow-up sent to {names}.'})
