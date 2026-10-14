from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin, IsCustomer, IsSupportStaff
from tickets.models import Category, Priority, Ticket

User = get_user_model()

OPEN_STATUSES = [Ticket.Status.NEW, Ticket.Status.IN_PROGRESS]


# ------------------------------------------------------------ helpers
def _counts(qs, field):
    """{field_value: number_of_tickets}"""
    rows = qs.values(field).annotate(n=Count('id')).order_by()
    return {row[field]: row['n'] for row in rows}


def by_status(qs):
    counts = _counts(qs, 'status')
    return [
        {'status': value, 'label': label, 'count': counts.get(value, 0)}
        for value, label in Ticket.Status.choices
    ]


def by_priority(qs):
    counts = _counts(qs, 'priority')
    rows = []
    for p in Priority.objects.all():
        count = counts.pop(p.slug, 0)
        if p.is_active or count:
            rows.append({'priority': p.slug, 'name': p.name, 'count': count})
    for slug, count in counts.items():  # purani/anjaan priority (safety)
        rows.append({'priority': slug, 'name': slug, 'count': count})
    return rows


def by_category(qs):
    counts = _counts(qs, 'category_id')
    rows = [
        {'category_id': c.id, 'category': c.name, 'count': counts.pop(c.id, 0)}
        for c in Category.objects.all()
    ]
    uncategorized = counts.pop(None, 0)
    if uncategorized:
        rows.append(
            {'category_id': None, 'category': 'Uncategorized', 'count': uncategorized}
        )
    return rows


def recent(qs, limit=5):
    return list(
        qs.order_by('-created_at').values(
            'id', 'title', 'status', 'priority', 'created_at'
        )[:limit]
    )


# ----------------------------------------------------------- builders
def build_admin_dashboard():
    tickets = Ticket.objects.all()

    # Staff performance: har support staff ke tickets
    staff = (
        User.objects.filter(role='support', is_active=True)
        .annotate(
            assigned_total=Count('assigned_tickets'),
            open_tickets=Count(
                'assigned_tickets',
                filter=Q(assigned_tickets__status__in=OPEN_STATUSES),
            ),
            resolved_tickets=Count(
                'assigned_tickets',
                filter=Q(assigned_tickets__status=Ticket.Status.RESOLVED),
            ),
            closed_tickets=Count(
                'assigned_tickets',
                filter=Q(assigned_tickets__status=Ticket.Status.CLOSED),
            ),
        )
        .order_by('-closed_tickets', '-resolved_tickets', 'id')
    )

    # Average resolution time (hours) per staff
    durations = {}
    resolved_rows = Ticket.objects.filter(
        assigned_to__isnull=False, resolved_at__isnull=False
    ).values_list('assigned_to_id', 'created_at', 'resolved_at')
    for staff_id, created, resolved in resolved_rows:
        durations.setdefault(staff_id, []).append(
            (resolved - created).total_seconds()
        )

    staff_performance = []
    for s in staff:
        secs = durations.get(s.id, [])
        avg_hours = round(sum(secs) / len(secs) / 3600, 2) if secs else None
        staff_performance.append({
            'staff_id': s.id,
            'username': s.username,
            'assigned_total': s.assigned_total,
            'open': s.open_tickets,
            'resolved': s.resolved_tickets,
            'closed': s.closed_tickets,
            'avg_resolution_hours': avg_hours,
        })

    return {
        'role': 'admin',
        'total_tickets': tickets.count(),
        'open_tickets': tickets.filter(status__in=OPEN_STATUSES).count(),
        'unassigned_tickets': tickets.filter(assigned_to__isnull=True)
        .exclude(status=Ticket.Status.CLOSED).count(),
        'by_status': by_status(tickets),
        'by_priority': by_priority(tickets),
        'by_category': by_category(tickets),
        'staff_performance': staff_performance,
    }


def build_support_dashboard(user):
    tickets = Ticket.objects.filter(assigned_to=user)
    base = '/api/support/tickets/'

    # Quick filters: label + kitne tickets + seedha URL
    quick_filters = [
        {'label': row['label'], 'count': row['count'],
         'url': f"{base}?status={row['status']}"}
        for row in by_status(tickets)
    ]
    quick_filters += [
        {'label': f"Priority: {row['name']}", 'count': row['count'],
         'url': f"{base}?priority={row['priority']}"}
        for row in by_priority(tickets) if row['count']
    ]
    quick_filters += [
        {'label': f"Category: {row['category']}", 'count': row['count'],
         'url': f"{base}?category={row['category_id']}"}
        for row in by_category(tickets)
        if row['count'] and row['category_id'] is not None
    ]

    return {
        'role': 'support',
        'assigned_total': tickets.count(),
        'open_tickets': tickets.filter(status__in=OPEN_STATUSES).count(),
        'by_status': by_status(tickets),
        'by_priority': by_priority(tickets),
        'by_category': by_category(tickets),
        'quick_filters': quick_filters,
        'recent_tickets': recent(tickets),
    }


def build_customer_dashboard(user):
    tickets = Ticket.objects.filter(created_by=user)
    return {
        'role': 'customer',
        'total_tickets': tickets.count(),
        'open_tickets': tickets.filter(status__in=OPEN_STATUSES).count(),
        'by_status': by_status(tickets),
        'recent_tickets': recent(tickets, limit=10),
    }


# -------------------------------------------------------------- views
class AdminDashboardView(APIView):
    """GET /api/dashboard/admin/  (Admin only)"""
    permission_classes = [IsAdmin]

    def get(self, request, *args, **kwargs):
        return Response(build_admin_dashboard())


class SupportDashboardView(APIView):
    """GET /api/dashboard/support/  (Support Staff only)"""
    permission_classes = [IsSupportStaff]

    def get(self, request, *args, **kwargs):
        return Response(build_support_dashboard(request.user))


class CustomerDashboardView(APIView):
    """GET /api/dashboard/me/  (Customer only)"""
    permission_classes = [IsCustomer]

    def get(self, request, *args, **kwargs):
        return Response(build_customer_dashboard(request.user))


class DashboardView(APIView):
    """GET /api/dashboard/  -> logged-in user ke role ke hisaab se sahi dashboard"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_helpdesk_admin:
            return Response(build_admin_dashboard())
        if user.is_support_staff:
            return Response(build_support_dashboard(user))
        return Response(build_customer_dashboard(user))