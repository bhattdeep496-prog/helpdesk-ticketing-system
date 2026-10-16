from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from tickets.models import Priority, Ticket

ALLOWED_ORDERING = {
    'id', '-id', 'created_at', '-created_at',
    'updated_at', '-updated_at', 'status', '-status',
}


class TicketPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class TicketListSerializer(serializers.ModelSerializer):
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
    description_preview = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'description_preview', 'status', 'priority',
            'category', 'category_name', 'tag_names', 'created_by',
            'assigned_to', 'created_at', 'updated_at', 'resolved_at',
        ]
        read_only_fields = fields

    def get_description_preview(self, obj):
        text = obj.description or ''
        return text if len(text) <= 120 else text[:120] + '...'


def _csv(params, name):
    """'?status=new,in_progress' -> ['new', 'in_progress']"""
    value = params.get(name)
    if not value:
        return []
    return [v.strip() for v in value.split(',') if v.strip()]


def _date(params, name):
    value = params.get(name)
    if not value:
        return None
    parsed = parse_date(value)  # sirf YYYY-MM-DD
    if parsed is None:
        raise ValidationError({name: 'Use the date format YYYY-MM-DD.'})
    return parsed


class TicketSearchView(generics.ListAPIView):
    """
    GET /api/tickets/    (paginated: count, next, previous, results)

    Kaun kya dekhta hai:
      Admin -> sab tickets | Support Staff -> assigned tickets | Customer -> apni tickets

    SEARCH
      ?search=<text>      ticket ID (12 ya #12), title, description ya comment ke keyword.
                          (Customer ke liye internal notes search me nahi aate.)
    FILTERS (comma se multiple values: ?status=new,in_progress)
      ?status=            new / in_progress / resolved / closed
      ?priority=          priority slug (low, medium, high, critical ...)
      ?category=          category id(s), ya 'none' (bina category)
      ?tag=               tag ka naam (bug ya bug,urgent), kisi ek bhi tag wali tickets
      ?assigned_to=       (sirf Admin) user id ya 'unassigned'
      ?created_from=YYYY-MM-DD   &   ?created_to=YYYY-MM-DD   (date range, dono inclusive)
    ORDERING & PAGES
      ?ordering=-created_at (default) | created_at | id | updated_at | status
      ?page=2   ?page_size=20 (max 100)
    """
    serializer_class = TicketListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TicketPagination

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params
        is_staff_side = user.is_helpdesk_admin or user.is_support_staff

        # 1) Role ke hisaab se base queryset
        if user.is_helpdesk_admin:
            qs = Ticket.objects.all()
        elif user.is_support_staff:
            qs = Ticket.objects.filter(assigned_to=user)
        else:
            qs = Ticket.objects.filter(created_by=user)

        # 2) Search (ID / title / description / comments)
        search = params.get('search', '').strip()
        if search:
            condition = Q(title__icontains=search) | Q(description__icontains=search)
            number = search.lstrip('#')
            if number.isdigit():
                condition |= Q(pk=int(number))
            if is_staff_side:
                condition |= Q(comments__body__icontains=search)
            else:
                condition |= Q(
                    comments__body__icontains=search, comments__is_internal=False
                )
            qs = qs.filter(condition).distinct()

        # 3) Filters
        statuses = _csv(params, 'status')
        if statuses:
            invalid = [s for s in statuses if s not in Ticket.Status.values]
            if invalid:
                raise ValidationError(
                    {'status': f"Invalid status: {', '.join(invalid)}. "
                               f"Use: {', '.join(Ticket.Status.values)}"}
                )
            qs = qs.filter(status__in=statuses)

        priorities = _csv(params, 'priority')
        if priorities:
            known = set(Priority.objects.values_list('slug', flat=True))
            invalid = [p for p in priorities if p not in known]
            if invalid:
                raise ValidationError(
                    {'priority': f"Invalid priority: {', '.join(invalid)}."}
                )
            qs = qs.filter(priority__in=priorities)

        categories = _csv(params, 'category')
        if categories:
            ids = [int(c) for c in categories if c.isdigit()]
            wants_none = 'none' in categories
            if len(ids) + int(wants_none) != len(categories):
                raise ValidationError(
                    {'category': "Use category ids (e.g. 1,2) or 'none'."}
                )
            condition = Q(category_id__in=ids)
            if wants_none:
                condition |= Q(category__isnull=True)
            qs = qs.filter(condition)

        tag_names = _csv(params, 'tag')
        if tag_names:
            tag_condition = Q()
            for name in tag_names:
                tag_condition |= Q(tags__name__iexact=name)
            qs = qs.filter(tag_condition).distinct()

        assigned = params.get('assigned_to')
        if assigned and user.is_helpdesk_admin:
            if assigned == 'unassigned':
                qs = qs.filter(assigned_to__isnull=True)
            elif assigned.isdigit():
                qs = qs.filter(assigned_to_id=int(assigned))
            else:
                raise ValidationError(
                    {'assigned_to': "Use a user id or 'unassigned'."}
                )

        date_from = _date(params, 'created_from')
        date_to = _date(params, 'created_to')
        if date_from and date_to and date_from > date_to:
            raise ValidationError(
                {'created_from': 'created_from cannot be after created_to.'}
            )
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        # 4) Ordering
        ordering = params.get('ordering', '-created_at')
        if ordering not in ALLOWED_ORDERING:
            raise ValidationError(
                {'ordering': f"Use one of: {', '.join(sorted(ALLOWED_ORDERING))}"}
            )

        return (
            qs.select_related('category', 'created_by', 'assigned_to')
            .prefetch_related('tags')
            .order_by(ordering, '-id')
        )