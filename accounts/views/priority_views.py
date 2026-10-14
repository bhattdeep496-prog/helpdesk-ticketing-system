from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError

from accounts.views.admin_views import IsAdminOrReadOnly
from tickets.models import Priority, Ticket


class PrioritySerializer(serializers.ModelSerializer):
    class Meta:
        model = Priority
        fields = ['id', 'name', 'slug', 'level', 'is_active']
        read_only_fields = ['id', 'slug']


class PriorityListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/priorities/   -> sab logged-in users (dropdown ke liye).
                               Admin ko inactive bhi dikhte hain.
    POST /api/priorities/   -> Admin: {"name": "Blocker", "level": 5}
    """
    serializer_class = PrioritySerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = Priority.objects.all()
        if not self.request.user.is_helpdesk_admin:
            qs = qs.filter(is_active=True)
        return qs


class PriorityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/priorities/<id>/   -> sab logged-in users
    PATCH  /api/priorities/<id>/   -> Admin: name, level, is_active badalna
    DELETE /api/priorities/<id>/   -> Admin (agar kisi ticket me use ho raha ho to nahi)
    """
    serializer_class = PrioritySerializer
    permission_classes = [IsAdminOrReadOnly]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = Priority.objects.all()
        if not self.request.user.is_helpdesk_admin:
            qs = qs.filter(is_active=True)
        return qs

    def perform_destroy(self, instance):
        if Ticket.objects.filter(priority=instance.slug).exists():
            raise ValidationError(
                'This priority is used by existing tickets. '
                'Set is_active to false instead of deleting it.'
            )
        instance.delete()