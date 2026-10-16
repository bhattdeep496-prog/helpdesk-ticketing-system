"""Admin settings (spec 3.10): ek hi row wala SystemSettings model."""
from django.db import models


class SystemSettings(models.Model):
    allow_public_registration = models.BooleanField(default=True)
    max_upload_size_mb = models.PositiveIntegerField(default=5)
    max_files_per_request = models.PositiveIntegerField(default=5)
    allowed_file_types = models.CharField(
        max_length=200,
        default='gif,jpeg,jpg,pdf,png',
        help_text='Comma se alag extensions, jaise: jpg,png,pdf',
    )
    notifications_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'System settings'
        verbose_name_plural = 'System settings'

    def __str__(self):
        return 'System settings'

    def save(self, *args, **kwargs):
        # Hamesha sirf ek row (id=1)
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Settings row delete nahi hone dena
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def allowed_types_list(self):
        return [
            t.strip().lower().lstrip('.')
            for t in self.allowed_file_types.split(',')
            if t.strip()
        ]