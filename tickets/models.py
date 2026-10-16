from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify



class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Admin-managed tags (optional) jo tickets par lagaye ja sakte hain."""
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Priority(models.Model):
    """Admin-defined priority levels (default: Low, Medium, High, Critical)."""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, editable=False)
    level = models.PositiveSmallIntegerField(
        default=1, help_text="Higher number = more urgent."
    )
    is_active = models.BooleanField(
        default=True, help_text="Inactive priorities cannot be used on new tickets."
    )

    class Meta:
        ordering = ["level", "id"]
        verbose_name_plural = "priorities"

    def save(self, *args, **kwargs):
        # slug sirf pehli baar bante waqt banta hai, tickets isi ko store karte hain
        if not self.slug:
            self.slug = slugify(self.name).replace("-", "_")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


def validate_priority(value):
    """Ticket ki priority kisi active Priority ka slug honi chahiye."""
    if not Priority.objects.filter(slug=value, is_active=True).exists():
        raise ValidationError(f"'{value}' is not a valid priority.")


class Ticket(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tickets",
    )
    priority = models.CharField(
        max_length=50, default="medium", validators=[validate_priority]
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="created_tickets",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assigned_tickets",
        limit_choices_to={"role": "support"},
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="tickets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} {self.title}"


class Comment(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    body = models.TextField()
    is_internal = models.BooleanField(
        default=False, help_text="Internal note: only staff can see it."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on #{self.ticket_id}"


class Attachment(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="attachments/%Y/%m/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name


class TicketHistory(models.Model):
    """Log of status/priority/assignment changes, so users can see a ticket's history."""
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="history"
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    field = models.CharField(max_length=30)
    old_value = models.CharField(max_length=100)
    new_value = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "ticket history"

    def __str__(self):
        return f"#{self.ticket_id}: {self.field} {self.old_value} -> {self.new_value}"

from .site_settings import SystemSettings  #noqa: F401