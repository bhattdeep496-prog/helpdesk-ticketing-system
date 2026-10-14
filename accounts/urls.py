from unicodedata import name
from django.urls import path
from accounts.views.login_view import LoginView
from accounts.views.logout_view import LogoutView
from accounts.views.forgot_reset_view import ForgotPasswordView, ResetPasswordView
from accounts.views.change_password_view import ChangePasswordView
from accounts.views.reset_password_view import PasswordResetView, PasswordResetConfirmView
from accounts.views.my_tickets_view import MyTicketsView, MyTicketDetailView
from accounts.views.user_profile_view import UserProfileView
# pyrefly: ignore [missing-import]
from accounts.views.admin_views import (
    AdminUserListCreateView,
    AdminUserDetailView,
    AdminCategoryListCreateView,
    AdminCategoryDetailView,
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
 
    # Customer
    path("my-tickets/<int:pk>/history/", MyTicketHistoryView.as_view(), name="my-ticket-history"),

]
