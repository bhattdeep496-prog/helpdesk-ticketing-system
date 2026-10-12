from unicodedata import name
from django.urls import path
from accounts.views.login_view import LoginView
from accounts.views.logout_view import LogoutView
from accounts.views.forgot_reset_view import ForgotPasswordView, ResetPasswordView
from accounts.views.change_password_view import ChangePasswordView
from accounts.views.reset_password_view import PasswordResetView, PasswordResetConfirmView
from accounts.views.my_tickets_view import MyTicketsView, MyTicketDetailView
from accounts.views.user_profile_view import UserProfileView


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
    

]
