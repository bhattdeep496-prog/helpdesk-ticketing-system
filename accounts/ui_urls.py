from django.urls import path

from accounts.ui_views import (DashboardPageView, ForgotPasswordPageView,
                               LoginPageView, ManageSettingsPageView,
                               ManageSetupPageView, ManageUsersPageView,
                               NewTicketPageView, ProfilePageView,
                               RegisterPageView, ResetPasswordPageView,
                               TicketDetailPageView, TicketsPageView)

urlpatterns = [
    path('', LoginPageView.as_view(), name='ui-home'),
    path('login/', LoginPageView.as_view(), name='ui-login'),
    path('dashboard/', DashboardPageView.as_view(), name='ui-dashboard'),
    path('tickets/', TicketsPageView.as_view(), name='ui-tickets'),
    path('tickets/new/', NewTicketPageView.as_view(), name='ui-ticket-new'),
    path('tickets/<int:pk>/', TicketDetailPageView.as_view(), name='ui-ticket-detail'),

    path('forgot-password/', ForgotPasswordPageView.as_view(), name='ui-forgot-password'),
    path('reset-password/', ResetPasswordPageView.as_view(), name='ui-reset-password'),
    path('register/', RegisterPageView.as_view(), name='ui-register'),
    path('profile/', ProfilePageView.as_view(), name='ui-profile'),
    path('manage/users/', ManageUsersPageView.as_view(), name='ui-manage-users'),
    path('manage/setup/', ManageSetupPageView.as_view(), name='ui-manage-setup'),
    path('manage/settings/', ManageSettingsPageView.as_view(), name='ui-manage-settings'),
]
