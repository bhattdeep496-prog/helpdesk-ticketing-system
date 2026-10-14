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

# Upload rules (spec: images, PDFs)
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf'}
MAX_FILE_SIZE_MB = 5
MAX_FILES_PER_REQUEST = 5


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.CharField(source='uploaded_by.username', read_only=True)
    filename = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ['id', 'filename', 'url', 'uploaded_by', 'uploaded_at']

    def get_filename(self, obj):
        return os.path.basename(obj.file.name)

    def get_url(self, obj):
        request = self.context.get('request')
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url


class TicketAttachmentView(APIView):
    """
    GET  /api/tickets/<id>/attachments/   -> list files of a ticket
    POST /api/tickets/<id>/attachments/   -> upload one or MORE files
         (multipart/form-data, field name: "files", repeat it for many files)

    Access: ticket ka owner (customer), assigned support staff, aur Admin.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def _get_ticket(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        permission = IsTicketParticipant()
        if not permission.has_object_permission(request, self, ticket):
            raise PermissionDenied(permission.message)
        return ticket

    def get(self, request, pk, *args, **kwargs):
        ticket = self._get_ticket(request, pk)
        data = AttachmentSerializer(
            ticket.attachments.select_related('uploaded_by'),
            many=True, context={'request': request},
        ).data
        return Response(data)

    def post(self, request, pk, *args, **kwargs):
        ticket = self._get_ticket(request, pk)

        if ticket.status == Ticket.Status.CLOSED:
            raise ValidationError('Files cannot be added to a closed ticket.')

        files = request.FILES.getlist('files')
        if not files:
            raise ValidationError(
                {'files': 'Please upload at least one file (field name: "files").'}
            )
        if len(files) > MAX_FILES_PER_REQUEST:
            raise ValidationError(
                {'files': f'You can upload at most {MAX_FILES_PER_REQUEST} files at a time.'}
            )

        # Pehle sab validate karo, phir save (ek bhi galat ho to koi save nahi)
        errors = []
        for f in files:
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                errors.append(
                    f"{f.name}: type not allowed. Allowed: "
                    f"{', '.join(sorted(ALLOWED_EXTENSIONS))}"
                )
            elif f.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                errors.append(f'{f.name}: larger than {MAX_FILE_SIZE_MB} MB.')
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