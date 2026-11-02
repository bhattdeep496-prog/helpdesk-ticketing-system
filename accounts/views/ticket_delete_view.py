from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets.models import Ticket


class TicketDeleteView(APIView):
    """
    DELETE /api/tickets/<id>/delete/

    - Admin: kisi bhi ticket ko delete kar sakta hai.
    - Customer: sirf apna ticket, aur sirf jab tak status 'New' hai.
    - Support staff: delete nahi kar sakta.
    Ticket ke comments, history aur attachments bhi hat jaate hain
    (files disk se bhi hataayi jaati hain).
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        user = request.user
        ticket = get_object_or_404(Ticket, pk=pk)

        if user.is_helpdesk_admin:
            pass
        elif ticket.created_by_id == user.id:
            if ticket.status != Ticket.Status.NEW:
                raise PermissionDenied(
                    'You can delete a ticket only while its status is "New".'
                )
        else:
            # Dusre ke ticket ka pata hi na chale
            return Response({'detail': 'Not found.'}, status=404)

        # Files disk se bhi hatao (database row delete hone par file apne aap nahi hatti)
        for attachment in ticket.attachments.all():
            attachment.file.delete(save=False)
        ticket.delete()
        return Response({'detail': 'Ticket deleted.'}, status=200)
