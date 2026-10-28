"""Admin settings API (spec 3.10): sirf admin padh aur badal sakta hai."""
from django.conf import settings as dj_settings
from django.core.mail import send_mail
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from tickets.site_settings import SystemSettings


class SystemSettingsSerializer(serializers.ModelSerializer):
    max_upload_size_mb = serializers.IntegerField(min_value=1, max_value=50)
    max_files_per_request = serializers.IntegerField(min_value=1, max_value=20)

    class Meta:
        model = SystemSettings
        fields = [
            'allow_public_registration',
            'max_upload_size_mb',
            'max_files_per_request',
            'allowed_file_types',
            'notifications_enabled',
            'updated_at',
        ]
        read_only_fields = ['updated_at']

    def validate_allowed_file_types(self, value):
        types = [t.strip().lower().lstrip('.') for t in value.split(',') if t.strip()]
        if not types:
            raise serializers.ValidationError('Kam se kam ek file type do.')
        for t in types:
            if not t.isalnum():
                raise serializers.ValidationError(f'Galat file type: {t}')
        return ','.join(types)


class SystemSettingsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(responses=SystemSettingsSerializer, tags=['Admin settings'])
    def get(self, request):
        data = SystemSettingsSerializer(SystemSettings.load()).data
        return Response(data)

    @extend_schema(
        request=SystemSettingsSerializer,
        responses=SystemSettingsSerializer,
        tags=['Admin settings'],
    )
    def patch(self, request):
        obj = SystemSettings.load()
        serializer = SystemSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class EmailStatusView(APIView):
    """
    GET /api/admin/email-status/  (Admin only)
    Email server ki current settings dikhata hai (password kabhi nahi).
    Settings environment variables se aati hain (EMAIL_HOST, EMAIL_PORT ...),
    isliye yahan sirf padh sakte hain.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(tags=['Admin settings'])
    def get(self, request):
        backend = getattr(dj_settings, 'EMAIL_BACKEND', '')
        is_smtp = backend.endswith('smtp.EmailBackend')
        return Response({
            'mode': 'smtp' if is_smtp else 'console',
            'backend': backend,
            'host': getattr(dj_settings, 'EMAIL_HOST', '') if is_smtp else '',
            'port': getattr(dj_settings, 'EMAIL_PORT', None) if is_smtp else None,
            'use_tls': getattr(dj_settings, 'EMAIL_USE_TLS', False) if is_smtp else False,
            'use_ssl': getattr(dj_settings, 'EMAIL_USE_SSL', False) if is_smtp else False,
            'username': getattr(dj_settings, 'EMAIL_HOST_USER', '') if is_smtp else '',
            'from_email': getattr(dj_settings, 'DEFAULT_FROM_EMAIL', ''),
        })


class EmailTestView(APIView):
    """POST /api/admin/email-test/  (Admin only): apne email par test mail bhejta hai."""
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(request=None, tags=['Admin settings'])
    def post(self, request):
        to = request.user.email
        if not to:
            return Response(
                {'error': 'Pehle apni profile me email address add karo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            send_mail(
                'Deskly test email',
                'Congratulations! Your email settings are working.',
                None,  # DEFAULT_FROM_EMAIL
                [to],
                fail_silently=False,
            )
        except Exception as exc:  # SMTP errors: wrong host/password etc.
            return Response(
                {'error': f'Email send failed: {exc}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'message': f'Test email sent to {to}.'})
