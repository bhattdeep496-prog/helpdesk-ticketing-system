from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from tickets.models import Ticket, TicketHistory

User = get_user_model()


class AdminTicketSerializer(serializers.ModelSerializer):
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
            'id', 'title', 'priority', 'status', 'category', 'category_name',
            'created_by', 'assigned_to', 'assigned_to_id',
            'created_at', 'updated_at', 'resolved_at',
        ]
        read_only_fields = fields


class AssignSerializer(serializers.Serializer):
    # null bhejne par ticket unassign ho jata hai
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='support', is_active=True),
        allow_null=True,
    )


def assign_ticket(ticket, staff, changed_by):
    """Ticket ko staff (ya None) ko assign karo aur history me likho."""
    if ticket.status == Ticket.Status.CLOSED:
        raise ValidationError('A closed ticket cannot be reassigned.')

    old = ticket.assigned_to
    if (old and staff and old.pk == staff.pk) or (old is None and staff is None):
        return ticket

    ticket.assigned_to = staff
    ticket.save(update_fields=['assigned_to', 'updated_at'])

    TicketHistory.objects.create(
        ticket=ticket,
        changed_by=changed_by,
        field='assigned_to',
        old_value=old.username if old else '-',
        new_value=staff.username if staff else '-',
    )
    return ticket


class AdminTicketListView(generics.ListAPIView):
    """
    GET /api/admin/tickets/   -> all tickets
    Filters: ?status=new  ?priority=high  ?category=1
             ?assigned_to=<user id> or ?assigned_to=unassigned
             ?search=<id or title>
    """
    serializer_class = AdminTicketSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = Ticket.objects.select_related('category', 'created_by', 'assigned_to')
        params = self.request.query_params

        if params.get('status'):
            qs = qs.filter(status=params['status'])
        if params.get('priority'):
            qs = qs.filter(priority=params['priority'])
        if params.get('category'):
            qs = qs.filter(category_id=params['category'])

        assigned = params.get('assigned_to')
        if assigned == 'unassigned':
            qs = qs.filter(assigned_to__isnull=True)
        elif assigned and assigned.isdigit():
            qs = qs.filter(assigned_to_id=int(assigned))

        search = params.get('search')
        if search:
            condition = Q(title__icontains=search)
            if search.isdigit():
                condition |= Q(pk=int(search))
            qs = qs.filter(condition)

        return qs


class AdminAssignTicketView(APIView):
    """
    PATCH /api/admin/tickets/<id>/assign/   (MANUAL assignment)
    Body: {"assigned_to": <support user id>}   or   {"assigned_to": null}
    """
    permission_classes = [IsAdmin]

    def patch(self, request, pk, *args, **kwargs):
        ticket = get_object_or_404(Ticket, pk=pk)
        serializer = AssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assign_ticket(ticket, serializer.validated_data['assigned_to'], request.user)
        return Response(AdminTicketSerializer(ticket).data)


class AdminAutoAssignTicketView(APIView):
    """
    POST /api/admin/tickets/<id>/auto-assign/   (AUTO assignment)
    Ticket us active support staff ko milta hai jiske paas
    sabse kam open (New / In Progress) tickets hain.
    """
    permission_classes = [IsAdmin]

    def post(self, request, pk, *args, **kwargs):
        ticket = get_object_or_404(Ticket, pk=pk)

        staff = (
            User.objects.filter(role='support', is_active=True)
            .annotate(
                open_count=Count(
                    'assigned_tickets',
                    filter=Q(assigned_tickets__status__in=[
                        Ticket.Status.NEW, Ticket.Status.IN_PROGRESS,
                    ]),
                )
            )
            .order_by('open_count', 'id')
            .first()
        )
        if staff is None:
            return Response(
                {'error': 'No active support staff available.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assign_ticket(ticket, staff, request.user)
        return Response(AdminTicketSerializer(ticket).data)