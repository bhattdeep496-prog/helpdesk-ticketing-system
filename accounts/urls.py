from django.urls import path
from drf_spectacular.views import (SpectacularAPIView, SpectacularRedocView,
                                   SpectacularSwaggerView)

from accounts.views.admin_ticket_detail_view import AdminTicketDetailView
from accounts.views.admin_ticket_views import (AdminAssignTicketView,
                                               AdminAutoAssignTicketView,
                                               AdminTicketListView)
# pyrefly: ignore [missing-import]
from accounts.views.admin_views import (AdminCategoryDetailView,
                                        AdminCategoryListCreateView,
                                        AdminUserDetailView,
                                        AdminUserListCreateView)
from accounts.views.attachment_views import (TicketAttachmentDeleteView,
                                             TicketAttachmentView)
from accounts.views.change_password_view import ChangePasswordView
from accounts.views.comment_views import TicketCommentView
from accounts.views.dashboard_views import (AdminDashboardView,
                                            CustomerDashboardView,
                                            DashboardView,
                                            SupportDashboardView)
from accounts.views.forgot_reset_view import (ForgotPasswordView,
                                              ResetPasswordView)
from accounts.views.login_view import LoginView
from accounts.views.logout_view import LogoutView
from accounts.views.my_tickets_view import MyTicketDetailView, MyTicketsView
from accounts.views.notification_views import (NotificationListView,
                                               NotificationReadView)
from accounts.views.priority_views import (PriorityDetailView,
                                           PriorityListCreateView)
from accounts.views.register_view import RegisterView
from accounts.views.report_views import (SummaryReportView,
                                         TicketsCSVExportView,
                                         TicketsPDFExportView)
from accounts.views.system_settings_view import (EmailStatusView,
                                                 EmailTestView,
                                                 SystemSettingsView)
from accounts.views.tag_views import AdminTagDetailView, AdminTagListCreateView
from accounts.views.ticket_history_view import MyTicketHistoryView
from accounts.views.ticket_search_view import TicketSearchView
from accounts.views.user_profile_view import UserProfileView
from accounts.views.support_views import (
    SupportTicketListView,
    SupportTicketDetailView,
    SupportStaffListView,
    SupportTicketReassignView,
)
from accounts.views.followup_views import TicketFollowUpView
from accounts.views.recipient_views import (AdminRecipientCandidatesView,
                                            AdminRecipientDetailView,
                                            AdminRecipientListCreateView,
                                            TicketRecipientChoicesView)

try:
    import accounts.api_docs  # noqa: F401  (Swagger annotations)
except Exception as exc:      # docs ki wajah se API kabhi band na ho
    print(f"API docs annotations skipped: {exc}")


urlpatterns = [
    # accounts
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('chage-password/', ChangePasswordView.as_view(), name='chage-password'),  # old (typo) path, kept for compatibility

    # my tickets
    path('my-tickets/', MyTicketsView.as_view(), name='my-tickets'),
    path('my-tickets/<int:ticket_id>/', MyTicketDetailView.as_view(), name='my-ticket-detail'),

    # user profile
    path('user-profile/', UserProfileView.as_view(), name='user-profile'),

    # Admin
    path("admin/users/", AdminUserListCreateView.as_view(), name="admin-users"),
    path("admin/users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/categories/", AdminCategoryListCreateView.as_view(), name="admin-categories"),
    path("admin/categories/<int:pk>/", AdminCategoryDetailView.as_view(), name="admin-category-detail"),

    # Support staff
    path("support/tickets/", SupportTicketListView.as_view(), name="support-tickets"),
    path("support/tickets/<int:pk>/", SupportTicketDetailView.as_view(), name="support-ticket-detail"),
    path("register/", RegisterView.as_view(), name="register"),

    # Customer
    path("my-tickets/<int:pk>/history/", MyTicketHistoryView.as_view(), name="my-ticket-history"),

    # Admin: tickets + assignment (manual / auto)
    path("admin/tickets/", AdminTicketListView.as_view(), name="admin-tickets"),
    path("admin/tickets/<int:pk>/assign/", AdminAssignTicketView.as_view(), name="admin-ticket-assign"),
    path("admin/tickets/<int:pk>/auto-assign/", AdminAutoAssignTicketView.as_view(), name="admin-ticket-auto-assign"),

    # Attachments (customer / assigned support / admin)
    path("tickets/<int:pk>/attachments/", TicketAttachmentView.as_view(), name="ticket-attachments"),
    path("tickets/<int:pk>/attachments/<int:attachment_id>/", TicketAttachmentDeleteView.as_view(), name="ticket-attachment-delete"),
    
    # Follow up & reassign
    path("support/tickets/<int:pk>/reassign/", SupportTicketReassignView.as_view(), name="support-ticket-reassign"),
    path("support/staff/", SupportStaffListView.as_view(), name="support-staff"),
    path("tickets/<int:pk>/follow-up/", TicketFollowUpView.as_view(), name="ticket-follow-up"),

    # 3.3 Comments
    path("tickets/<int:pk>/comments/", TicketCommentView.as_view(), name="ticket-comments"),

    # 3.4 Priorities
    path("priorities/", PriorityListCreateView.as_view(), name="priority-list-create"),
    path("priorities/<int:pk>/", PriorityDetailView.as_view(), name="priority-detail"),

    # 3.5 Dashboards
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("dashboard/admin/", AdminDashboardView.as_view(), name="dashboard-admin"),
    path("dashboard/support/", SupportDashboardView.as_view(), name="dashboard-support"),
    path("dashboard/me/", CustomerDashboardView.as_view(), name="dashboard-customer"),

    # 3.6 Search & Filters
    path("tickets/", TicketSearchView.as_view(), name="tickets-search"),

    # 3.7 Reporting
    path("reports/summary/", SummaryReportView.as_view(), name="report-summary"),
    path("reports/tickets/csv/", TicketsCSVExportView.as_view(), name="report-tickets-csv"),
    path("reports/tickets/pdf/", TicketsPDFExportView.as_view(), name="report-tickets-pdf"),

    # 3.8 Admin ticket CRUD
    path("admin/tickets/<int:pk>/", AdminTicketDetailView.as_view(), name="admin-ticket-detail"),

    # API documentation (Swagger / ReDoc)
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # 3.10 Admin settings
    path('admin/settings/', SystemSettingsView.as_view(), name='admin-settings'),
    path('admin/email-status/', EmailStatusView.as_view(), name='admin-email-status'),
    path('admin/email-test/', EmailTestView.as_view(), name='admin-email-test'),
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/read/', NotificationReadView.as_view(), name='notifications-read'),
    path('admin/tags/', AdminTagListCreateView.as_view(), name='admin-tags'),
    path('admin/tags/<int:pk>/', AdminTagDetailView.as_view(), name='admin-tag-detail'),

    # Ticket recipients ("Send ticket to" dropdown)
    path('admin/recipients/', AdminRecipientListCreateView.as_view(), name='admin-recipients'),
    path('admin/recipients/candidates/', AdminRecipientCandidatesView.as_view(), name='admin-recipient-candidates'),
    path('admin/recipients/<int:pk>/', AdminRecipientDetailView.as_view(), name='admin-recipient-detail'),
    path('ticket-recipients/', TicketRecipientChoicesView.as_view(), name='ticket-recipients'),
]
