from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsTicketParticipant
from tickets.models import Comment, Ticket
from tickets.notifications import push


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='author.username', read_only=True)
    author_role = serializers.CharField(source='author.role', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'author', 'author_role', 'body', 'is_internal', 'created_at']
        read_only_fields = ['id', 'author', 'author_role', 'created_at']

    def validate_body(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Comment cannot be empty.')
        return value


def notify_new_comment(comment):
    """
    Naye (non-internal) comment ka email dusre side ko bhejo.
    Customer likhe -> assigned support ko; staff likhe -> customer ko.
    Development me email server terminal me print hota hai.
    """
    ticket = comment.ticket
    author = comment.author

    if author.pk == ticket.created_by_id:
        target = ticket.assigned_to
    else:
        target = ticket.created_by

    if target and target.pk != author.pk:
        push(target, 'comment',
             f'New comment on ticket #{ticket.pk} from {author.username}', ticket)

    if target and target.email and target.pk != author.pk:
        send_mail(
            subject=f'[Ticket #{ticket.pk}] New comment: {ticket.title}',
            message=f'{author.username} wrote:\n\n{comment.body}',
            from_email=None,
            recipient_list=[target.email],
            fail_silently=True,
        )


class TicketCommentView(APIView):
    """
    GET  /api/tickets/<id>/comments/   -> comment thread (mini chat)
    POST /api/tickets/<id>/comments/   -> {"body": "...", "is_internal": false}

    - Ticket ka owner (customer), assigned support staff aur Admin hi use kar sakte hain.
    - Internal notes sirf staff likh aur dekh sakta hai, customer ko nahi dikhte.
    - Closed ticket par naya comment nahi likh sakte.
    """
    permission_classes = [IsAuthenticated]

    def _get_ticket(self, request, pk):
        ticket = get_object_or_404(
            Ticket.objects.select_related('created_by', 'assigned_to'), pk=pk
        )
        permission = IsTicketParticipant()
        if not permission.has_object_permission(request, self, ticket):
            raise PermissionDenied(permission.message)
        return ticket

    def get(self, request, pk, *args, **kwargs):
        ticket = self._get_ticket(request, pk)
        comments = ticket.comments.select_related('author')
        if request.user.is_customer:
            comments = comments.filter(is_internal=False)
        return Response(CommentSerializer(comments, many=True).data)

    def post(self, request, pk, *args, **kwargs):
        ticket = self._get_ticket(request, pk)

        if ticket.status == Ticket.Status.CLOSED:
            raise ValidationError('Comments cannot be added to a closed ticket.')

        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get('is_internal') and request.user.is_customer:
            raise PermissionDenied('Customers cannot add internal notes.')

        comment = serializer.save(ticket=ticket, author=request.user)

        if not comment.is_internal:
            notify_new_comment(comment)

        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)