from django.contrib.auth import logout
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class LogoutView(APIView):
    """
    API endpoint for user logout.
    Requires Token authentication. Deletes the active auth token and clears the session.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(
            {'message': 'Send a POST request with Authorization header ("Token <your_token>") to log out.'},
            status=status.HTTP_200_OK
        )

    def post(self, request, *args, **kwargs):
        # Delete user's auth token
        if hasattr(request.user, 'auth_token'):
            request.user.auth_token.delete()

        # Flush any session cookies if present
        logout(request)

        return Response(
            {'message': 'Successfully logged out.'},
            status=status.HTTP_200_OK
        )
