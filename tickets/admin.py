from django.contrib import admin

from .models import Attachment, Category, Comment, Ticket


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "priority", "status",
        "created_by", "assigned_to", "created_at",
    )
    list_filter = ("status", "priority", "category")
    search_fields = ("title", "description", "created_by__username")
    inlines = [CommentInline, AttachmentInline]


admin.site.register(Category)
admin.site.register(Comment)
admin.site.register(Attachment)