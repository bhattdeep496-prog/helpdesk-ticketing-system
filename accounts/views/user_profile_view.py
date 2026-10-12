from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from django.contrib.auth import get_user_model

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    total_tickets = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'date_joined', 'total_tickets',
        ]
        # Ye fields user khud change nahi kar sakta
        # (khaas karke role, warna customer khud ko admin bana lega)
        read_only_fields = ['id', 'username', 'role', 'date_joined']

    def get_total_tickets(self, obj):
        return obj.created_tickets.count()

    def validate_email(self, value):
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(email__iexact=value).exists():
            raise serializers.ValidationError('This email is already in use.')
        return value


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/profile/   -> logged-in user ki profile
    PATCH /api/profile/   -> email, first_name, last_name update karna
    Header: Authorization: Token <your_token>
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user