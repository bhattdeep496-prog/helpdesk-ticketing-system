from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.db.utils import OperationalError, ProgrammingError

DEFAULT_PRIORITIES = [("Low", 1), ("Medium", 2), ("High", 3), ("Critical", 4)]


def create_default_priorities(sender, **kwargs):
    """`migrate` ke baad, agar koi priority nahi hai to 4 default priorities banao."""
    from .models import Priority

    try:
        if Priority.objects.exists():
            return
        for name, level in DEFAULT_PRIORITIES:
            Priority.objects.create(name=name, level=level)
    except (OperationalError, ProgrammingError):
        # table abhi bani nahi (partial migrate), skip
        pass


class TicketsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tickets"

    def ready(self):
        post_migrate.connect(create_default_priorities, sender=self)