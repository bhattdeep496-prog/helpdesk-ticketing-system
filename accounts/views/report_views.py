from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin, IsAdminOrSupport
from accounts.report_builders import csv_bytes, pdf_bytes
from accounts.views.dashboard_views import by_category, by_priority, by_status
from accounts.views.ticket_search_view import TicketSearchView
from tickets.models import Priority, Ticket, TicketHistory

MAX_EXPORT_ROWS = 5000
MAX_SUMMARY_DAYS = 366

EXPORT_HEADERS = [
    'ID', 'Title', 'Status', 'Priority', 'Category',
    'Created By', 'Assigned To', 'Created At', 'Updated At', 'Resolved At',
]
# PDF me kam columns (page me fit hone ke liye) - total 273 mm
PDF_HEADERS = [
    'ID', 'Title', 'Status', 'Priority', 'Category',
    'Created By', 'Assigned To', 'Created At',
]
PDF_COL_WIDTHS_MM = [12, 90, 24, 22, 32, 30, 30, 33]


def _fmt(dt):
    return timezone.localtime(dt).strftime('%Y-%m-%d %H:%M') if dt else ''


def _filename(extension):
    stamp = timezone.localtime().strftime('%Y%m%d_%H%M')
    return f'tickets_report_{stamp}.{extension}'


def _export_tickets(request):
    """
    /api/tickets/ jaisa hi queryset (wahi search + filters, wahi role scope),
    bas bina pagination ke, max MAX_EXPORT_ROWS tak.
    """
    view = TicketSearchView()
    view.request = request
    view.args = ()
    view.kwargs = {}
    return list(view.get_queryset()[:MAX_EXPORT_ROWS])


def _priority_names():
    return dict(Priority.objects.values_list('slug', 'name'))


def _rows(tickets, full=True):
    names = _priority_names()
    for t in tickets:
        row = [
            t.id,
            t.title,
            t.get_status_display(),
            names.get(t.priority, t.priority),
            t.category.name if t.category else '',
            t.created_by.username,
            t.assigned_to.username if t.assigned_to else '',
            _fmt(t.created_at),
        ]
        if full:
            row += [_fmt(t.updated_at), _fmt(t.resolved_at)]
        yield row


class TicketsCSVExportView(APIView):
    """
    GET /api/reports/tickets/csv/?status=resolved&created_from=2026-10-01 ...
    Wahi filters jo /api/tickets/ me hain. Admin aur Support Staff ke liye.
    (Admin: sab tickets, Support: sirf apni assigned tickets.)
    """
    permission_classes = [IsAdminOrSupport]

    def get(self, request, *args, **kwargs):
        tickets = _export_tickets(request)
        content = csv_bytes(EXPORT_HEADERS, _rows(tickets, full=True))
        response = HttpResponse(content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{_filename("csv")}"'
        return response


class TicketsPDFExportView(APIView):
    """GET /api/reports/tickets/pdf/?...   (same filters as CSV export)"""
    permission_classes = [IsAdminOrSupport]

    def get(self, request, *args, **kwargs):
        tickets = _export_tickets(request)
        filters = request.query_params.urlencode() or 'none'
        subtitle = (
            f'Generated: {_fmt(timezone.now())}  |  '
            f'Tickets: {len(tickets)}  |  Filters: {filters}'
        )
        try:
            content = pdf_bytes(
                'Helpdesk Tickets Report', subtitle,
                PDF_HEADERS, _rows(tickets, full=False), PDF_COL_WIDTHS_MM,
            )
        except ImportError:
            return Response(
                {'error': 'PDF export needs the reportlab package. '
                          'Run: pip install reportlab'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        response = HttpResponse(content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{_filename("pdf")}"'
        return response


def _date_param(params, name):
    value = params.get(name)
    if not value:
        return None
    parsed = parse_date(value)
    if parsed is None:
        raise ValidationError({name: 'Use the date format YYYY-MM-DD.'})
    return parsed


class SummaryReportView(APIView):
    """
    GET /api/reports/summary/?from=2026-10-01&to=2026-10-14   (Admin only)
    Default: aakhri 30 din.

    opened   = us period me bani tickets
    resolved = us period me Resolved hui tickets
    closed   = us period me Closed hui tickets (status history se)
    daily    = din-ba-din numbers (chart ke liye)
    """
    permission_classes = [IsAdmin]

    def get(self, request, *args, **kwargs):
        params = request.query_params
        date_to = _date_param(params, 'to') or timezone.localdate()
        date_from = _date_param(params, 'from') or (date_to - timedelta(days=29))

        if date_from > date_to:
            raise ValidationError({'from': "'from' cannot be after 'to'."})
        if (date_to - date_from).days + 1 > MAX_SUMMARY_DAYS:
            raise ValidationError(
                {'from': f'Period can be at most {MAX_SUMMARY_DAYS} days.'}
            )

        opened_qs = Ticket.objects.filter(
            created_at__date__gte=date_from, created_at__date__lte=date_to
        )
        resolved_qs = Ticket.objects.filter(
            resolved_at__date__gte=date_from, resolved_at__date__lte=date_to
        )
        closed_events = TicketHistory.objects.filter(
            field='status', new_value=Ticket.Status.CLOSED,
            created_at__date__gte=date_from, created_at__date__lte=date_to,
        )

        # Din-ba-din counts
        def per_day(qs, field):
            rows = (
                qs.annotate(day=TruncDate(field)).values('day')
                .annotate(n=Count('id')).order_by()
            )
            return {r['day']: r['n'] for r in rows}

        opened_by_day = per_day(opened_qs, 'created_at')
        resolved_by_day = per_day(resolved_qs, 'resolved_at')
        closed_by_day = per_day(closed_events, 'created_at')

        daily = []
        day = date_from
        while day <= date_to:
            daily.append({
                'date': day.isoformat(),
                'opened': opened_by_day.get(day, 0),
                'resolved': resolved_by_day.get(day, 0),
                'closed': closed_by_day.get(day, 0),
            })
            day += timedelta(days=1)

        # Average resolution time (hours) us period me resolve hui tickets ka
        seconds = [
            (resolved - created).total_seconds()
            for created, resolved in resolved_qs.values_list('created_at', 'resolved_at')
        ]
        avg_hours = round(sum(seconds) / len(seconds) / 3600, 2) if seconds else None

        return Response({
            'period': {'from': date_from.isoformat(), 'to': date_to.isoformat()},
            'opened': opened_qs.count(),
            'resolved': resolved_qs.count(),
            'closed': closed_events.values('ticket_id').distinct().count(),
            'avg_resolution_hours': avg_hours,
            'opened_by_status': by_status(opened_qs),
            'opened_by_priority': by_priority(opened_qs),
            'opened_by_category': by_category(opened_qs),
            'daily': daily,
        })