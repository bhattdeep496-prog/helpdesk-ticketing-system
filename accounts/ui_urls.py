from django.urls import path

from accounts.ui_views import (
    DashboardPageView,
    LoginPageView,
    NewTicketPageView,
    TicketDetailPageView,
    TicketsPageView,
)

urlpatterns = [
    path('', LoginPageView.as_view(), name='ui-home'),
    path('login/', LoginPageView.as_view(), name='ui-login'),
    path('dashboard/', DashboardPageView.as_view(), name='ui-dashboard'),
    path('tickets/', TicketsPageView.as_view(), name='ui-tickets'),
    path('tickets/new/', NewTicketPageView.as_view(), name='ui-ticket-new'),
    path('tickets/<int:pk>/', TicketDetailPageView.as_view(), name='ui-ticket-detail'),
]