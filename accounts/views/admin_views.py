from django.contrib.auth import get_user_model, password_validation
from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (SAFE_METHODS, BasePermission,
                                        IsAuthenticated)

from accounts.permissions import IsAdmin
from tickets.models import Category

User = get_user_model()


# ------------------------------------------------------------------ users
class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'is_active', 'password', 'date_joined',
        ]
        read_only_fields = ['id', 'date_joined']

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError(
                {'password': 'Password is required when creating a user.'}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class AdminUserListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/admin/users/   -> list users (?role=support&is_active=true&search=ali)
    POST /api/admin/users/   -> create a user with a role (Admin only)
    """
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = User.objects.all().order_by('id')
        params = self.request.query_params

        role = params.get('role')
        is_active = params.get('is_active')
        search = params.get('search')

        if role:
            qs = qs.filter(role=role)
        if is_active in ('true', 'false'):
            qs = qs.filter(is_active=(is_active == 'true'))
        if search:
            qs = qs.filter(username__icontains=search) | qs.filter(
                email__icontains=search
            )
        return qs


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/admin/users/<id>/  -> user details
    PATCH /api/admin/users/<id>/  -> change role / deactivate / edit details
    Users are deactivated (is_active=false), never deleted.
    """
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.all()
    http_method_names = ['get', 'patch', 'head', 'options']

    def perform_update(self, serializer):
        instance = serializer.instance
        data = serializer.validated_data

        # Admin apne aap ko lock-out na kar le
        if instance.pk == self.request.user.pk:
            if data.get('is_active') is False:
                raise ValidationError('You cannot deactivate your own account.')
            new_role = data.get('role')
            if new_role and new_role != instance.role and instance.role == 'admin':
                raise ValidationError('You cannot remove your own admin role.')

        serializer.save()


# ------------------------------------------------------------- categories
class IsAdminOrReadOnly(BasePermission):
    """Everyone logged in can read categories; only Admin can change them."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_helpdesk_admin


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class AdminCategoryListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/admin/categories/  -> any logged-in user (needed to create tickets)
    POST /api/admin/categories/  -> Admin only
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class AdminCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET for all logged-in users; PATCH/DELETE for Admin only."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]