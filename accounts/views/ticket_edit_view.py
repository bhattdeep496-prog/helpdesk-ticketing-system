from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets.models import Ticket, TicketHistory


class TicketEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category', 'priority', 'tags']


class TicketEditView(APIView):
    """
    PATCH /api/tickets/<id>/edit/
    Body (sab optional): title, description, category, priority, tags

    - Admin: kisi bhi ticket ko edit kar sakta hai.
    - Customer: sirf apna ticket, aur sirf jab tak status 'New' hai.
    - Support staff: edit nahi kar sakta.
    Status, assigned_to jaisi cheezein yahan se nahi badalti.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        user = request.user
        ticket = get_object_or_404(Ticket, pk=pk)

        if user.is_helpdesk_admin:
            pass
        elif ticket.created_by_id == user.id:
            if ticket.status != Ticket.Status.NEW:
                raise PermissionDenied(
                    'You can edit a ticket only while its status is "New".'
                )
        else:
            # Dusre ke ticket ka pata hi na chale
            return Response({'detail': 'Not found.'}, status=404)

        old_priority = ticket.priority
        serializer = TicketEditSerializer(ticket, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save()

        if ticket.priority != old_priority:
            TicketHistory.objects.create(
                ticket=ticket, changed_by=user, field='priority',
                old_value=old_priority, new_value=ticket.priority,
            )
        return Response({'detail': 'Ticket updated.'}, status=200)
