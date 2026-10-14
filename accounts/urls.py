from unicodedata import name
from django.urls import path
from accounts.views.login_view import LoginView
from accounts.views.logout_view import LogoutView
from accounts.views.forgot_reset_view import ForgotPasswordView, ResetPasswordView
from accounts.views.change_password_view import ChangePasswordView
from accounts.views.reset_password_view import PasswordResetView, PasswordResetConfirmView
from accounts.views.my_tickets_view import MyTicketsView, MyTicketDetailView
from accounts.views.user_profile_view import UserProfileView
from accounts.views.register_view import RegisterView
from accounts.views.comment_views import TicketCommentView
from accounts.views.priority_views import PriorityListCreateView, PriorityDetailView
from accounts.views.admin_ticket_views import (
    AdminTicketListView,
    AdminAssignTicketView,
    AdminAutoAssignTicketView,
)
from accounts.views.attachment_views import TicketAttachmentView
# pyrefly: ignore [missing-import]
from accounts.views.admin_views import (
    AdminUserListCreateView,
    AdminUserDetailView,
    AdminCategoryListCreateView,
    AdminCategoryDetailView,
)
from accounts.views.dashboard_views import (
    DashboardView,
    AdminDashboardView,
    SupportDashboardView,
    CustomerDashboardView,
)
from accounts.views.support_views import (
    SupportTicketListView,
    SupportTicketDetailView,
)
from accounts.views.ticket_history_view import MyTicketHistoryView


urlpatterns = [
    #accounts 
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('chage-password/', ChangePasswordView.as_view(), name='chage-password'),



    #my tickets
    path('my-tickets/', MyTicketsView.as_view(), name='my-tickets'),
    path('my-tickets/<int:ticket_id>/', MyTicketDetailView.as_view(), name='my-ticket-detail'),



    #user profile
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


      # 3.3 Comments
    path("tickets/<int:pk>/comments/", TicketCommentView.as_view(), name="ticket-comments"),
 
    # 3.4 Priorities (Categories ke endpoints /api/admin/categories/ pe pehle se hain)
    path("priorities/", PriorityListCreateView.as_view(), name="priorities"),
    path("priorities/<int:pk>/", PriorityDetailView.as_view(), name="priority-detail"),


    # 3.5 Dashboards
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("dashboard/admin/", AdminDashboardView.as_view(), name="dashboard-admin"),
    path("dashboard/support/", SupportDashboardView.as_view(), name="dashboard-support"),
    path("dashboard/me/", CustomerDashboardView.as_view(), name="dashboard-customer"),
 
 
 

]
