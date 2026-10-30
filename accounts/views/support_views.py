from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsSupportStaff
from tickets.models import Ticket, TicketHistory

User = get_user_model()

# Ticket lifecycle: New -> In Progress -> Resolved -> Closed
# (Resolved ticket ko wapas In Progress me la sakte hain, reopen ke liye)
# In Progress se seedha Closed bhi ja sakta hai (e.g. duplicate / invalid ticket)
ALLOWED_TRANSITIONS = {
    Ticket.Status.NEW: {Ticket.Status.IN_PROGRESS},
    Ticket.Status.IN_PROGRESS: {Ticket.Status.RESOLVED, Ticket.Status.CLOSED},
    Ticket.Status.RESOLVED: {Ticket.Status.CLOSED, Ticket.Status.IN_PROGRESS},
    Ticket.Status.CLOSED: set(),
}


class SupportTicketSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.username', read_only=True)
    assigned_to = serializers.CharField(
        source='assigned_to.username', read_only=True, default=None
    )
    assigned_to_id = serializers.IntegerField(read_only=True)
    category_name = serializers.CharField(
        source='category.name', read_only=True, default=None
    )

    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'description', 'category', 'category_name',
            'priority', 'status', 'created_by', 'assigned_to', 'assigned_to_id',
            'created_at', 'updated_at', 'resolved_at',
        ]
        # Support staff sirf status aur priority badal sakta hai
        read_only_fields = [
            'title', 'description', 'category', 'created_by', 'assigned_to',
            'assigned_to_id', 'created_at', 'updated_at', 'resolved_at',
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
        return Ticket.objects.filter(
            assigned_to=self.request.user
        ).select_related('category', 'created_by', 'assigned_to')

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


class SupportStaffSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'name']

    def get_name(self, obj):
        return obj.get_full_name() or obj.username


class SupportStaffListView(generics.ListAPIView):
    """
    GET /api/support/staff/
    Active support staff ki list (apne aap ko chhodkar), reassign dropdown ke liye.
    """
    serializer_class = SupportStaffSerializer
    permission_classes = [IsSupportStaff]
    pagination_class = None

    def get_queryset(self):
        return (
            User.objects.filter(role='support', is_active=True)
            .exclude(pk=self.request.user.pk)
            .order_by('username')
        )


class SupportTicketReassignView(APIView):
    """
    POST /api/support/tickets/<id>/reassign/   body: {"assigned_to": <user id>}
    Support staff apna assigned ticket kisi dusre active support staff ko de sakta hai.
    Sirf wahi staff reassign kar sakta hai jisko ticket abhi assigned hai.
    Closed ticket reassign nahi hota.
    """
    permission_classes = [IsSupportStaff]

    @transaction.atomic
    def post(self, request, pk, *args, **kwargs):
        ticket = get_object_or_404(
            Ticket.objects.select_for_update(), pk=pk, assigned_to=request.user
        )

        if ticket.status == Ticket.Status.CLOSED:
            raise ValidationError('A closed ticket cannot be reassigned.')

        target_id = request.data.get('assigned_to')
        if not str(target_id or '').isdigit():
            raise ValidationError({'assigned_to': 'Select a support staff member.'})

        if int(target_id) == request.user.pk:
            raise ValidationError(
                {'assigned_to': 'This ticket is already assigned to you.'}
            )

        target = User.objects.filter(
            pk=int(target_id), role='support', is_active=True
        ).first()
        if target is None:
            raise ValidationError(
                {'assigned_to': 'Selected user is not an active support staff member.'}
            )

        old_name = request.user.username
        ticket.assigned_to = target
        # signals.py is flag ko dekh kar "reassigned by ..." notification bhejta hai
        ticket._reassigned_by = request.user
        ticket.save(update_fields=['assigned_to', 'updated_at'])

        TicketHistory.objects.create(
            ticket=ticket, changed_by=request.user, field='assigned_to',
            old_value=old_name, new_value=target.username,
        )

        data = SupportTicketSerializer(ticket, context={'request': request}).data
        return Response(
            {'detail': f'Ticket reassigned to {target.username}.', 'ticket': data},
            status=status.HTTP_200_OK,
        )
