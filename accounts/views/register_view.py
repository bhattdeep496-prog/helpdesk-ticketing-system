from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets.site_settings import SystemSettings

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'password', 'password2',
        ]
        extra_kwargs = {'email': {'required': True}}

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('This email is already registered.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {'password2': 'Passwords do not match.'}
            )
        candidate = User(username=attrs.get('username'), email=attrs.get('email'))
        password_validation.validate_password(attrs['password'], candidate)
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        # Public registration se hamesha Customer banta hai.
        # Role koi bhi request se nahi le sakta (security).
        return User.objects.create_user(
            password=password, role=User.Role.CUSTOMER, **validated_data
        )


class RegisterView(APIView):
    """
    POST /api/register/
    {"username": "...", "email": "...", "password": "...", "password2": "..."}

    Naya user hamesha 'customer' role ke saath banta hai.
    settings.py me ALLOW_PUBLIC_REGISTRATION = False karne par ye band ho jata hai,
    aur sirf Admin hi /api/admin/users/ se accounts bana sakta hai.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        if not SystemSettings.load().allow_public_registration:
            return Response(
                {'error': 'Public registration is disabled. '
                          'Please ask an admin to create your account.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                'message': 'Registration successful.',
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                },
            },
            status=status.HTTP_201_CREATED,
        )