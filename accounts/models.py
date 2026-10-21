from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user with a role: customer / agent / admin."""

    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        SUPPORT = "support", "Support Staff"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.CUSTOMER
    )

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_support_staff(self):
        return self.role == self.Role.SUPPORT

    @property
    def is_helpdesk_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    def save(self, *args, **kwargs):
        # createsuperuser se bana user UI me bhi admin dikhe
        if self.is_superuser and self.role == self.Role.CUSTOMER:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"