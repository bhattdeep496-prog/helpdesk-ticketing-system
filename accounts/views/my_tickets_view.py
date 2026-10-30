from rest_framework import generics, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from tickets.models import Comment, Ticket, TicketRecipient


class MyCommentSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'author', 'body', 'created_at']


class MyTicketSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.username', read_only=True)
    assigned_to = serializers.CharField(
        source='assigned_to.username', read_only=True, default=None
    )
    category_name = serializers.CharField(
        source='category.name', read_only=True, default=None
    )
    # tags: ticket banate waqt tag ids bhejo (optional), response mein naam bhi milte hain
    tag_names = serializers.SlugRelatedField(
        source='tags', many=True, read_only=True, slug_field='name'
    )
    comments = serializers.SerializerMethodField()
    # "Send ticket to": TicketRecipient ki id. Khali / null = "Any available (admin decides)"
    send_to = serializers.PrimaryKeyRelatedField(
        queryset=TicketRecipient.objects.filter(is_active=True),
        write_only=True, required=False, allow_null=True,
    )

    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'description', 'category', 'category_name',
            'priority', 'tags', 'tag_names', 'status', 'created_by',
            'assigned_to', 'created_at', 'updated_at', 'resolved_at',
            'comments', 'send_to',
        ]
        read_only_fields = [
            'status', 'created_by', 'assigned_to',
            'created_at', 'updated_at', 'resolved_at',
        ]

    def validate_send_to(self, recipient):
        if recipient is None:
            return None
        user = recipient.user
        if not user.is_active or user.role not in ('support', 'admin'):
            raise serializers.ValidationError(
                'This person is not available right now. Please choose someone else.'
            )
        return recipient

    def create(self, validated_data):
        recipient = validated_data.pop('send_to', None)
        if recipient is not None:
            # Customer ne staff chuna hai -> ticket seedha usko assign
            validated_data['assigned_to'] = recipient.user
            validated_data['raised_to_role'] = (
                Ticket.RaisedTo.ADMIN if recipient.user.role == 'admin'
                else Ticket.RaisedTo.SUPPORT
            )
        else:
            # "Any available (admin decides)": ticket unassigned rehti hai,
            # signals.py raised_to_role dekhkar admins ko notification bhejta hai
            validated_data['raised_to_role'] = Ticket.RaisedTo.ADMIN
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Recipient sirf ticket banate waqt chuna ja sakta hai; edit se assignment nahi badalna chahiye
        validated_data.pop('send_to', None)
        return super().update(instance, validated_data)

    def get_comments(self, obj):
        # Customer ko internal notes nahi dikhane
        visible = obj.comments.filter(is_internal=False)
        return MyCommentSerializer(visible, many=True).data


class MyTicketsView(generics.ListCreateAPIView):
    """
    GET  /api/my-tickets/   -> list of my tickets
                               (filters: ?status=new&priority=high&search=text)
    POST /api/my-tickets/   -> create a new ticket (optional: "tags": [1, 2])
    Header: Authorization: Token <your_token>
    """
    serializer_class = MyTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Ticket.objects.filter(created_by=self.request.user)

        status_param = self.request.query_params.get('status')
        priority_param = self.request.query_params.get('priority')
        search = self.request.query_params.get('search')

        if status_param:
            qs = qs.filter(status=status_param)
        if priority_param:
            qs = qs.filter(priority=priority_param)
        if search:
            qs = qs.filter(title__icontains=search)

        return qs.select_related('category', 'assigned_to').prefetch_related('tags')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class MyTicketDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/my-tickets/<id>/   -> ticket details with comments
    PATCH /api/my-tickets/<id>/   -> edit title/description/priority/category/tags
                                     (only while status is 'new')
    """
    serializer_class = MyTicketSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    lookup_url_kwarg = 'ticket_id'   # urls.py mein route <int:ticket_id> hai

    def get_queryset(self):
        # Sirf apne tickets, dusre ke ticket pe 404 milega
        return Ticket.objects.filter(
            created_by=self.request.user
        ).prefetch_related('tags')

    def perform_update(self, serializer):
        if serializer.instance.status != Ticket.Status.NEW:
            raise PermissionDenied(
                'You can edit a ticket only while its status is "New".'
            )
        serializer.save()
