from django.contrib import admin

from .models import (
    Attachment, Category, Comment, Priority, Ticket, TicketHistory,
)


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0


class HistoryInline(admin.TabularInline):
    model = TicketHistory
    extra = 0
    readonly_fields = ("changed_by", "field", "old_value", "new_value", "created_at")
    can_delete = False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "priority", "status",
        "created_by", "assigned_to", "created_at",
    )
    list_filter = ("status", "priority", "category")
    search_fields = ("title", "description", "created_by__username")
    inlines = [CommentInline, AttachmentInline, HistoryInline]


@admin.register(Priority)
class PriorityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "level", "is_active")
    list_editable = ("level", "is_active")
    readonly_fields = ("slug",)


admin.site.register(Category)
admin.site.register(Comment)
admin.site.register(Attachment)