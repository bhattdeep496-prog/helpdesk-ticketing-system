from .forgot_reset_view import ForgotPasswordView, ResetPasswordView


class PasswordResetView(ForgotPasswordView):
    """POST {"email": "..."}: reset uid + token email pe bhejta hai."""


class PasswordResetConfirmView(ResetPasswordView):
    """POST {"uid": "...", "token": "...", "new_password": "..."}: naya password set karta hai."""