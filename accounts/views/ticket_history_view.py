from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from tickets.models import Ticket, TicketHistory


class TicketHistorySerializer(serializers.ModelSerializer):
    changed_by = serializers.CharField(
        source='changed_by.username', read_only=True, default=None
    )

    class Meta:
        model = TicketHistory
        fields = ['id', 'field', 'old_value', 'new_value', 'changed_by', 'created_at']


class MyTicketHistoryView(generics.ListAPIView):
    """
    GET /api/my-tickets/<id>/history/
    Status/priority history of one of MY tickets (customer view).
    """
    serializer_class = TicketHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        ticket = get_object_or_404(
            Ticket, pk=self.kwargs['pk'], created_by=self.request.user
        )
        return TicketHistory.objects.filter(ticket=ticket).select_related('changed_by')