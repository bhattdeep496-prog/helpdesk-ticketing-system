from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from accounts.views.admin_views import IsAdminOrReadOnly
from tickets.models import Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class AdminTagListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/admin/tags/   -> sab tags (login wala koi bhi user dekh sakta hai)
    POST /api/admin/tags/   -> naya tag (sirf Admin)
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]


class AdminTagDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /api/admin/tags/<id>/   (edit aur delete sirf Admin)
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]