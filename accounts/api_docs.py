"""
Swagger / OpenAPI documentation ke annotations.

Views ke code ko chhuye bina, yahan se har endpoint ko tag, description,
request body aur filters ka documentation diya jata hai.
accounts/urls.py is file ko import karti hai.
"""
import importlib
import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers

log = logging.getLogger(__name__)


def _apply(module_path, class_name, decorator):
    """View class par decorator lagao. Class na mile to skip (docs API ko na todein)."""
    try:
        module = importlib.import_module(module_path)
        view = getattr(module, class_name)
    except (ImportError, AttributeError) as exc:
        log.warning('API docs skipped for %s.%s (%s)', module_path, class_name, exc)
        return None
    decorator(view)
    return getattr(module, class_name)


def _serializer(module_path, class_name):
    try:
        return getattr(importlib.import_module(module_path), class_name)
    except (ImportError, AttributeError):
        return OpenApiTypes.OBJECT


V = 'accounts.views.'

# --------------------------------------------------------------- common
TICKET_FILTERS = [
    OpenApiParameter(
        'search', str,
        description='Ticket ID (12 ya #12), title, description ya comment ka keyword.',
    ),
    OpenApiParameter(
        'status', str,
        description='Comma se multiple: new, in_progress, resolved, closed.',
    ),
    OpenApiParameter(
        'priority', str,
        description='Comma se multiple priority slugs (low, medium, high, critical, ...).',
    ),
    OpenApiParameter(
        'category', str, description="Category id(s) comma se, ya 'none' (bina category)."
    ),
    OpenApiParameter(
        'created_from', OpenApiTypes.DATE, description='YYYY-MM-DD (is din ko mila kar).'
    ),
    OpenApiParameter(
        'created_to', OpenApiTypes.DATE, description='YYYY-MM-DD (is din ko mila kar).'
    ),
    OpenApiParameter(
        'ordering', str,
        enum=['-created_at', 'created_at', '-updated_at', 'updated_at',
              '-id', 'id', '-status', 'status'],
        description='Default: -created_at.',
    ),
]
ADMIN_ASSIGNED_FILTER = OpenApiParameter(
    'assigned_to', str,
    description="(Sirf Admin) staff user id ya 'unassigned'.",
)

MESSAGE_RESPONSE = {200: OpenApiTypes.OBJECT}


def tag(name):
    return extend_schema(tags=[name])


# ------------------------------------------------------------------ Auth
_apply(V + 'login_view', 'LoginView', extend_schema_view(
    get=extend_schema(
        tags=['Auth'], summary='Login endpoint info', auth=[],
        responses=MESSAGE_RESPONSE,
    ),
    post=extend_schema(
        tags=['Auth'], summary='Login (token lo)', auth=[],
        description='Username aur password do, response me `token` milta hai. '
                    'Baaki requests me header lagao: `Authorization: Token <token>`.',
        request=inline_serializer('LoginRequest', {
            'username': serializers.CharField(),
            'password': serializers.CharField(),
        }),
        responses=MESSAGE_RESPONSE,
    ),
))

_apply(V + 'register_view', 'RegisterView', extend_schema(
    tags=['Auth'], summary='Register (hamesha Customer role)', auth=[],
    description='Naya account hamesha `customer` role ke saath banta hai. '
                'Admin ne public registration band kiya ho to 403 aata hai.',
    request=_serializer(V + 'register_view', 'RegisterSerializer'),
    responses={201: OpenApiTypes.OBJECT},
))

_apply(V + 'logout_view', 'LogoutView', extend_schema(
    tags=['Auth'], summary='Logout (token delete)', request=None,
    responses=MESSAGE_RESPONSE,
))

_apply(V + 'forgot_reset_view', 'ForgotPasswordView', extend_schema(
    tags=['Auth'], summary='Password reset email bhejo', auth=[],
    request=inline_serializer('ForgotPasswordRequest', {
        'email': serializers.EmailField(),
    }),
    responses=MESSAGE_RESPONSE,
))
_apply(V + 'forgot_reset_view', 'ResetPasswordView', extend_schema(
    tags=['Auth'], summary='Email wale uid + token se naya password set karo', auth=[],
    request=inline_serializer('ResetPasswordRequest', {
        'uid': serializers.CharField(),
        'token': serializers.CharField(),
        'new_password': serializers.CharField(),
    }),
    responses=MESSAGE_RESPONSE,
))
_apply(V + 'change_password_view', 'ChangePasswordView', extend_schema(
    tags=['Auth'], summary='Password badlo (logged-in user)',
    request=inline_serializer('ChangePasswordRequest', {
        'old_password': serializers.CharField(),
        'new_password': serializers.CharField(),
    }),
    responses=MESSAGE_RESPONSE,
))
_apply(V + 'user_profile_view', 'UserProfileView', tag('Auth'))

# ----------------------------------------------------------- Customer
_apply(V + 'my_tickets_view', 'MyTicketsView', extend_schema(
    tags=['Customer tickets'],
    description='GET: meri tickets (filters: status, priority, search). POST: nayi ticket.',
))
_apply(V + 'my_tickets_view', 'MyTicketDetailView', tag('Customer tickets'))
_apply(V + 'ticket_history_view', 'MyTicketHistoryView', tag('Customer tickets'))

# --------------------------------------------- Tickets (all roles) / search
_apply(V + 'ticket_search_view', 'TicketSearchView', extend_schema(
    tags=['Tickets'], summary='Search & filter tickets (role ke hisaab se)',
    description='Admin ko sab tickets, Support Staff ko assigned tickets, '
                'Customer ko apni tickets milti hain. Result pages me aata hai.',
    parameters=TICKET_FILTERS + [ADMIN_ASSIGNED_FILTER],
))

_comment_serializer = _serializer(V + 'comment_views', 'CommentSerializer')
_apply(V + 'comment_views', 'TicketCommentView', extend_schema_view(
    get=extend_schema(
        tags=['Comments & attachments'], summary='Ticket ka comment thread',
        description='Customer ko internal notes nahi dikhte.',
        responses=_comment_serializer(many=True)
        if _comment_serializer is not OpenApiTypes.OBJECT else OpenApiTypes.OBJECT,
    ),
    post=extend_schema(
        tags=['Comments & attachments'], summary='Comment likho',
        description='`is_internal=true` sirf Support Staff / Admin laga sakta hai.',
        request=_comment_serializer, responses={201: _comment_serializer},
    ),
))

_attachment_serializer = _serializer(V + 'attachment_views', 'AttachmentSerializer')
_apply(V + 'attachment_views', 'TicketAttachmentView', extend_schema_view(
    get=extend_schema(
        tags=['Comments & attachments'], summary='Ticket ki files ki list',
        responses=_attachment_serializer(many=True)
        if _attachment_serializer is not OpenApiTypes.OBJECT else OpenApiTypes.OBJECT,
    ),
    post=extend_schema(
        tags=['Comments & attachments'], summary='Ek ya zyada files upload karo',
        description='Field naam `files` (repeat kar sakte ho). Allowed: jpg, jpeg, png, '
                    'gif, pdf. Har file max 5 MB, ek baar me max 5 files.',
        request={'multipart/form-data': inline_serializer('AttachmentUploadRequest', {
            'files': serializers.ListField(child=serializers.FileField()),
        })},
        responses={201: _attachment_serializer(many=True)
                   if _attachment_serializer is not OpenApiTypes.OBJECT
                   else OpenApiTypes.OBJECT},
    ),
))

# ------------------------------------------------------------ Support
_apply(V + 'support_views', 'SupportTicketListView', extend_schema(
    tags=['Support staff'], summary='Mujhe assigned tickets',
    parameters=TICKET_FILTERS[:4],
))
_apply(V + 'support_views', 'SupportTicketDetailView', extend_schema(
    tags=['Support staff'],
    description='PATCH: sirf `status` aur `priority`. Flow: New -> In Progress -> '
                'Resolved -> Closed.',
))

# -------------------------------------------------------------- Admin
for _cls in ('AdminUserListCreateView', 'AdminUserDetailView',
             'AdminCategoryListCreateView', 'AdminCategoryDetailView'):
    _apply(V + 'admin_views', _cls, tag('Admin: users & categories'))
_apply(V + 'admin_views', 'AdminUserListCreateView', extend_schema(
    tags=['Admin: users & categories'],
    parameters=[
        OpenApiParameter('role', str, enum=['admin', 'support', 'customer']),
        OpenApiParameter('is_active', bool),
        OpenApiParameter('search', str, description='Username ya email.'),
    ],
))

for _cls in ('PriorityListCreateView', 'PriorityDetailView'):
    _apply(V + 'priority_views', _cls, tag('Priorities'))

_apply(V + 'admin_ticket_views', 'AdminTicketListView', extend_schema(
    tags=['Admin: tickets'], summary='Saari tickets',
    parameters=TICKET_FILTERS[:5] + [ADMIN_ASSIGNED_FILTER],
))
_apply(V + 'admin_ticket_detail_view', 'AdminTicketDetailView', tag('Admin: tickets'))
_apply(V + 'admin_ticket_views', 'AdminAssignTicketView', extend_schema(
    tags=['Admin: tickets'], summary='Ticket manually assign karo',
    description='`{"assigned_to": <support user id>}` ya `null` (unassign).',
    request=_serializer(V + 'admin_ticket_views', 'AssignSerializer'),
    responses=_serializer(V + 'admin_ticket_views', 'AdminTicketSerializer'),
))
_apply(V + 'admin_ticket_views', 'AdminAutoAssignTicketView', extend_schema(
    tags=['Admin: tickets'], summary='Ticket auto-assign karo',
    description='Sabse kam open tickets wale active support staff ko milta hai.',
    request=None,
    responses=_serializer(V + 'admin_ticket_views', 'AdminTicketSerializer'),
))

# ---------------------------------------------------------- Dashboards
for _cls in ('DashboardView', 'AdminDashboardView',
             'SupportDashboardView', 'CustomerDashboardView'):
    _apply(V + 'dashboard_views', _cls, extend_schema(
        tags=['Dashboards'], responses=OpenApiTypes.OBJECT,
    ))

# ------------------------------------------------------------- Reports
_apply(V + 'report_views', 'SummaryReportView', extend_schema(
    tags=['Reports'], summary='Summary report (opened / resolved / closed)',
    parameters=[
        OpenApiParameter('from', OpenApiTypes.DATE, description='YYYY-MM-DD'),
        OpenApiParameter('to', OpenApiTypes.DATE, description='YYYY-MM-DD'),
    ],
    responses=OpenApiTypes.OBJECT,
))
_apply(V + 'report_views', 'TicketsCSVExportView', extend_schema(
    tags=['Reports'], summary='Tickets CSV export',
    parameters=TICKET_FILTERS + [ADMIN_ASSIGNED_FILTER],
    responses={(200, 'text/csv'): OpenApiTypes.BINARY},
))
_apply(V + 'report_views', 'TicketsPDFExportView', extend_schema(
    tags=['Reports'], summary='Tickets PDF export',
    parameters=TICKET_FILTERS + [ADMIN_ASSIGNED_FILTER],
    responses={(200, 'application/pdf'): OpenApiTypes.BINARY},
))
