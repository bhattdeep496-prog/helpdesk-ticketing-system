from django.utils import timezone
from rest_framework import generics, serializers

from accounts.permissions import IsAdmin
from tickets.models import Ticket, TicketHistory


class AdminTicketDetailSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.username', read_only=True)
    assigned_to = serializers.CharField(
        source='assigned_to.username', read_only=True, default=None
    )
    category_name = serializers.CharField(
        source='category.name', read_only=True, default=None
    )
    tag_names = serializers.SlugRelatedField(
        source='tags', many=True, read_only=True, slug_field='name'
    )

    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'description', 'category', 'category_name',
            'priority', 'status', 'tag_names',
            'created_by', 'assigned_to', 'created_at', 'updated_at', 'resolved_at',
        ]
        read_only_fields = [
            'id', 'created_by', 'assigned_to', 'category_name', 'tag_names',
            'created_at', 'updated_at', 'resolved_at',
        ]


class AdminTicketDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/admin/tickets/<id>/   -> full ticket details
    PATCH  /api/admin/tickets/<id>/   -> title, description, category, priority, status
    DELETE /api/admin/tickets/<id>/   -> ticket (comments/history ke saath) delete

    Assign karne ke liye /api/admin/tickets/<id>/assign/ use karo.
    Admin status ko kisi bhi value par set kar sakta hai (flow rules support staff
    ke liye hain). Status/priority badalne par history me entry banti hai.
    """
    queryset = Ticket.objects.select_related(
        'created_by', 'assigned_to', 'category'
    ).prefetch_related('tags')
    serializer_class = AdminTicketDetailSerializer
    permission_classes = [IsAdmin]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def perform_update(self, serializer):
        ticket = serializer.instance
        old_status, old_priority = ticket.status, ticket.priority
        new_status = serializer.validated_data.get('status', old_status)

        extra = {}
        if new_status == Ticket.Status.RESOLVED and old_status != Ticket.Status.RESOLVED:
            extra['resolved_at'] = timezone.now()
        elif new_status == Ticket.Status.CLOSED and old_status not in (
            Ticket.Status.RESOLVED, Ticket.Status.CLOSED
        ):
            # Ticket closed without going through resolved — set resolved_at now
            extra['resolved_at'] = timezone.now()
        elif (new_status in (Ticket.Status.NEW, Ticket.Status.IN_PROGRESS)
              and old_status in (Ticket.Status.RESOLVED, Ticket.Status.CLOSED)):
            extra['resolved_at'] = None  # ticket dobara khul gaya

        ticket = serializer.save(**extra)

        user = self.request.user
        if ticket.status != old_status:
            TicketHistory.objects.create(
                ticket=ticket, changed_by=user, field='status',
                old_value=old_status, new_value=ticket.status,
            )
        if ticket.priority != old_priority:
            TicketHistory.objects.create(
                ticket=ticket, changed_by=user, field='priority',
                old_value=old_priority, new_value=ticket.priority,
            )