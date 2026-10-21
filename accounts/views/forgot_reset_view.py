from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from rest_framework.authtoken.models import Token

User = get_user_model()


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

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
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

        # Same response either way, so nobody can find out which emails exist.
        return Response(
            {'message': 'If this email is registered, a reset link has been sent.'},
            status=status.HTTP_200_OK,
        )


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
