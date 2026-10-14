from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, serializers

from accounts.permissions import IsSupportStaff
from tickets.models import Ticket, TicketHistory

# Ticket lifecycle: New -> In Progress -> Resolved -> Closed
# (Resolved ticket ko wapas In Progress me la sakte hain, reopen ke liye)
ALLOWED_TRANSITIONS = {
    Ticket.Status.NEW: {Ticket.Status.IN_PROGRESS},
    Ticket.Status.IN_PROGRESS: {Ticket.Status.RESOLVED},
    Ticket.Status.RESOLVED: {Ticket.Status.CLOSED, Ticket.Status.IN_PROGRESS},
    Ticket.Status.CLOSED: set(),
}


class SupportTicketSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.username', read_only=True)
    assigned_to = serializers.CharField(
        source='assigned_to.username', read_only=True, default=None
    )
    category_name = serializers.CharField(
        source='category.name', read_only=True, default=None
    )

    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'description', 'category', 'category_name',
            'priority', 'status', 'created_by', 'assigned_to',
            'created_at', 'updated_at', 'resolved_at',
        ]
        # Support staff sirf status aur priority badal sakta hai
        read_only_fields = [
            'title', 'description', 'category', 'created_by', 'assigned_to',
            'created_at', 'updated_at', 'resolved_at',
        ]

    def validate_status(self, new_status):
        current = self.instance.status
        if new_status == current:
            return new_status
        if new_status not in ALLOWED_TRANSITIONS.get(current, set()):
            raise serializers.ValidationError(
                f"Cannot move a ticket from '{current}' to '{new_status}'."
            )
        return new_status


class SupportTicketListView(generics.ListAPIView):
    """
    GET /api/support/tickets/
    Tickets assigned to the logged-in support staff.
    Filters: ?status=new  ?priority=high  ?category=1  ?search=<id or title>
    """
    serializer_class = SupportTicketSerializer
    permission_classes = [IsSupportStaff]

    def get_queryset(self):
        qs = Ticket.objects.filter(assigned_to=self.request.user)
        params = self.request.query_params

        if params.get('status'):
            qs = qs.filter(status=params['status'])
        if params.get('priority'):
            qs = qs.filter(priority=params['priority'])
        if params.get('category'):
            qs = qs.filter(category_id=params['category'])

        search = params.get('search')
        if search:
            condition = Q(title__icontains=search)
            if search.isdigit():
                condition |= Q(pk=int(search))
            qs = qs.filter(condition)

        return qs.select_related('category', 'created_by', 'assigned_to')


class SupportTicketDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/support/tickets/<id>/   -> ticket details
    PATCH /api/support/tickets/<id>/   -> {"status": "...", "priority": "..."}
    Only tickets assigned to this staff member are visible.
    """
    serializer_class = SupportTicketSerializer
    permission_classes = [IsSupportStaff]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        return Ticket.objects.filter(assigned_to=self.request.user)

    def perform_update(self, serializer):
        ticket = serializer.instance
        old_status, old_priority = ticket.status, ticket.priority
        new_status = serializer.validated_data.get('status', old_status)

        extra = {}
        if new_status == Ticket.Status.RESOLVED and old_status != Ticket.Status.RESOLVED:
            extra['resolved_at'] = timezone.now()
        elif old_status == Ticket.Status.RESOLVED and new_status == Ticket.Status.IN_PROGRESS:
            extra['resolved_at'] = None

        ticket = serializer.save(**extra)

        # History me likho kya badla
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