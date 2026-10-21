
from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.db.utils import OperationalError, ProgrammingError

DEFAULT_PRIORITIES = [
    ("Low", 1),
    ("Medium", 2),
    ("High", 3),
    ("Critical", 4),
]


def create_default_priorities(sender, **kwargs):
    """Create missing default priorities after migrations."""
    from .models import Priority

    try:
        for name, level in DEFAULT_PRIORITIES:
            slug = name.lower()

            Priority.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "level": level,
                },
            )
    except (OperationalError, ProgrammingError):
        pass


class TicketsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tickets"

    def ready(self):
        post_migrate.connect(
            create_default_priorities,
            sender=self,
            dispatch_uid="tickets.create_default_priorities",
        )

        from . import signals  # noqa: F401
