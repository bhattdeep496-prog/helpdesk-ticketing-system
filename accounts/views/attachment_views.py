import os

from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTicketParticipant
from tickets.models import Attachment, Ticket
from tickets.site_settings import SystemSettings


def can_delete_attachment(user, attachment):
    """Sirf upload karne wala ya admin file hata sakta hai."""
    return bool(user.is_helpdesk_admin or attachment.uploaded_by_id == user.id)


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.CharField(source='uploaded_by.username', read_only=True)
    filename = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ['id', 'filename', 'url', 'uploaded_by', 'uploaded_at', 'can_delete']

    def get_filename(self, obj):
        return os.path.basename(obj.file.name)

    def get_url(self, obj):
        request = self.context.get('request')
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url

    def get_can_delete(self, obj):
        request = self.context.get('request')
        return bool(request and can_delete_attachment(request.user, obj))


def get_ticket_for_user(request, view, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    permission = IsTicketParticipant()
    if not permission.has_object_permission(request, view, ticket):
        raise PermissionDenied(permission.message)
    return ticket


class TicketAttachmentView(APIView):
    """
    GET  /api/tickets/<id>/attachments/   -> list files of a ticket
    POST /api/tickets/<id>/attachments/   -> upload one or MORE files
         (multipart/form-data, field name: "files", repeat it for many files)

    Files ki count aur size par koi limit nahi hai.
    Sirf file type (extension) check hota hai (Admin settings me allowed types).

    Access: ticket ka owner (customer), assigned support staff, aur Admin.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk, *args, **kwargs):
        ticket = get_ticket_for_user(request, self, pk)
        data = AttachmentSerializer(
            ticket.attachments.select_related('uploaded_by'),
            many=True, context={'request': request},
        ).data
        return Response(data)

    def post(self, request, pk, *args, **kwargs):
        ticket = get_ticket_for_user(request, self, pk)

        if ticket.status == Ticket.Status.CLOSED:
            raise ValidationError('Files cannot be added to a closed ticket.')

        # Sirf allowed file types admin settings (database) se aate hain
        cfg = SystemSettings.load()
        allowed = {
            '.' + t.strip().lower().lstrip('.')
            for t in cfg.allowed_types_list()
            if t.strip()
        }

        files = request.FILES.getlist('files')
        if not files:
            raise ValidationError(
                {'files': 'Please upload at least one file (field name: "files").'}
            )

        # Pehle sab validate karo, phir save (ek bhi galat ho to koi save nahi)
        errors = []
        for f in files:
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in allowed:
                errors.append(
                    f"{f.name}: type not allowed. Allowed: "
                    f"{', '.join(sorted(allowed))}"
                )
        if errors:
            raise ValidationError({'files': errors})

        created = [
            Attachment.objects.create(
                ticket=ticket, file=f, uploaded_by=request.user
            )
            for f in files
        ]
        data = AttachmentSerializer(
            created, many=True, context={'request': request}
        ).data
        return Response(data, status=status.HTTP_201_CREATED)


class TicketAttachmentDeleteView(APIView):
    """
    DELETE /api/tickets/<id>/attachments/<attachment_id>/
    Galat upload ki hui file hatao. Sirf upload karne wala ya Admin hata sakta hai,
    aur closed ticket par nahi.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, attachment_id, *args, **kwargs):
        ticket = get_ticket_for_user(request, self, pk)
        attachment = get_object_or_404(Attachment, pk=attachment_id, ticket=ticket)

        if not can_delete_attachment(request.user, attachment):
            raise PermissionDenied('You can only remove files that you uploaded.')
        if ticket.status == Ticket.Status.CLOSED:
            raise ValidationError('Files cannot be removed from a closed ticket.')

        attachment.file.delete(save=False)   # disk se file bhi hatao
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)