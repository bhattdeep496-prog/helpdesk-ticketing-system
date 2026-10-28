import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()
log = logging.getLogger(__name__)


class ForgotPasswordView(APIView):
    """
    POST {"email": "user@example.com"}
    Sends a password reset uid + token to the user's email.
    (In development, the email is printed in the terminal.)
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        if not email:
            return Response(
                {'error': 'Please provide your email.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Sirf DEBUG (local) me response ke saath ek hint jaata hai, taaki pata chale
        # ki mail kyun nahi aayi. Production me user ko kuch nahi bataya jata.
        debug_hint = None

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            try:
                send_mail(
                    subject='Helpdesk - Password Reset',
                    message=(
                        f'Hello {user.username},\n\n'
                        f'Open this link to choose a new password:\n'
                        f'{settings.SITE_URL}/reset-password/?uid={uid}&token={token}\n\n'
                        f'Or use these details with the API:\n'
                        f'uid: {uid}\n'
                        f'token: {token}\n\n'
                        f'If you did not request this, ignore this email.'
                    ),
                    from_email=None,  # uses DEFAULT_FROM_EMAIL
                    recipient_list=[user.email],
                )
                if settings.EMAIL_BACKEND.endswith('console.EmailBackend'):
                    debug_hint = (
                        'Email is in CONSOLE mode: it was only printed in the server '
                        'terminal, it was NOT sent to a real inbox. Set the SMTP '
                        'details (EMAIL_HOST, EMAIL_HOST_USER, ...) in config/settings.py.'
                    )
                    log.warning('Password reset for %s printed to console (no SMTP configured).', user.email)
                else:
                    debug_hint = (
                        f'Email was handed to the mail server ({settings.EMAIL_HOST}). '
                        'If it is not in the inbox, check Spam.'
                    )
                    log.info('Password reset email sent to %s', user.email)
            except Exception as exc:  # wrong SMTP password / host / network
                # 500 dene se pata chal jata ki ye email registered hai, isliye
                # error log karte hain aur user ko same response dete hain.
                log.exception('Password reset email FAILED for %s', user.email)
                debug_hint = f'Sending the email FAILED: {exc}'
        else:
            debug_hint = (
                'No active user has this email address, so nothing was sent. '
                'Use the email saved in the user profile.'
            )
            log.warning('Password reset requested for unknown email: %s', email)

        # Same response either way, so nobody can find out which emails exist.
        data = {'message': 'If this email is registered, a reset link has been sent.'}
        if settings.DEBUG and debug_hint:
            data['debug'] = debug_hint
        return Response(data, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    """
    POST {"uid": "...", "token": "...", "new_password": "..."}
    Sets a new password if uid + token are valid.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not uid or not token or not new_password:
            return Response(
                {'error': 'uid, token and new_password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'error': 'Invalid reset link.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):    
            return Response(
                {'error': 'Token is invalid or has expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response(
                {'error': list(e.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
         user.set_password(new_password)
         user.save(update_fields=['password'])

        Token.objects.filter(user=user).delete()

        return Response(
            {'message': 'Password has been reset. You can now log in.'},
            status=status.HTTP_200_OK,
        )
