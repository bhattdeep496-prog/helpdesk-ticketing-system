"""In-app notifications API (bell icon): list + mark read. Har user sirf apni dekhta hai."""
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets.models import Notification
from tickets.notifications import serialize_notification


class NotificationListView(APIView):
    """GET /api/notifications/  -> {"unread_count": 2, "results": [latest 20]}"""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Notifications'])
    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        return Response({
            'unread_count': qs.filter(is_read=False).count(),
            'results': [serialize_notification(n) for n in qs[:20]],
        })


class NotificationReadView(APIView):
    """POST /api/notifications/read/  {"ids": [1, 2]}  (ids na do to sab read ho jaate hain)"""
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, tags=['Notifications'])
    def post(self, request):
        qs = Notification.objects.filter(user=request.user, is_read=False)
        ids = request.data.get('ids')
        if isinstance(ids, list):
            qs = qs.filter(pk__in=[i for i in ids if isinstance(i, int)])
        qs.update(is_read=True)
        unread = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': unread})
