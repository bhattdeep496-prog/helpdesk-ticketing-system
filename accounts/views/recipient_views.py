from django.contrib.auth import get_user_model
from rest_framework import generics, serializers
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets.models import TicketRecipient

User = get_user_model()

# Sirf yehi roles customer ke dropdown mein aa sakte hain
RECIPIENT_ROLES = ('support', 'admin')


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, 'role', None) == 'admin'
        )


def _name(user):
    return user.get_full_name() or user.username


class AdminRecipientSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = TicketRecipient
        fields = ['id', 'user', 'label', 'is_active', 'username', 'role', 'display_name']
        # default unique error ki jagah neeche validate_user ka saaf message
        extra_kwargs = {'user': {'validators': []}}

    def get_display_name(self, obj):
        return obj.display_name

    def validate_label(self, value):
        return value.strip()

    def validate_user(self, user):
        if user.role not in RECIPIENT_ROLES or not user.is_active:
            raise serializers.ValidationError(
                'Only an active support staff member or admin can be added.'
            )
        if self.instance is None and TicketRecipient.objects.filter(user=user).exists():
            raise serializers.ValidationError('This person is already in the list.')
        return user

    def update(self, instance, validated_data):
        validated_data.pop('user', None)   # edit mein user nahi badalta, sirf label / on-off
        return super().update(instance, validated_data)


class AdminRecipientListCreateView(generics.ListCreateAPIView):
    """
    GET  /admin/recipients/   -> all recipients (on and off)
    POST /admin/recipients/   -> {"user": <user id>, "label": "optional", "is_active": true}
    """
    serializer_class = AdminRecipientSerializer
    permission_classes = [IsAdminRole]
    pagination_class = None
    queryset = TicketRecipient.objects.select_related('user')


class AdminRecipientDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /admin/recipients/<id>/
    PATCH: {"label": "...", "is_active": false}. Delete sirf dropdown se hatata hai, user ko nahi.
    """
    serializer_class = AdminRecipientSerializer
    permission_classes = [IsAdminRole]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
    queryset = TicketRecipient.objects.select_related('user')


class AdminRecipientCandidatesView(APIView):
    """
    GET /admin/recipients/candidates/
    Active support staff / admins jo abhi list mein nahi hain ("Add" dropdown ke liye).
    """
    permission_classes = [IsAdminRole]

    def get(self, request):
        users = (
            User.objects.filter(role__in=RECIPIENT_ROLES, is_active=True)
            .exclude(ticket_recipient__isnull=False)
            .order_by('role', 'username')
        )
        return Response([
            {'id': u.pk, 'username': u.username, 'name': _name(u), 'role': u.role}
            for u in users
        ])


class TicketRecipientChoicesView(generics.ListAPIView):
    """
    GET /ticket-recipients/
    Customer ke "Send ticket to" dropdown ki list (sirf ON wale, active users).
    """
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def list(self, request, *args, **kwargs):
        rows = TicketRecipient.objects.filter(
            is_active=True, user__is_active=True, user__role__in=RECIPIENT_ROLES,
        ).select_related('user')
        return Response([{'id': r.pk, 'name': r.display_name} for r in rows])
