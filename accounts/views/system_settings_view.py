"""Admin settings API (spec 3.10): sirf admin padh aur badal sakta hai."""
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
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