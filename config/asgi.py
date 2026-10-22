"""
ASGI config: normal HTTP + WebSocket (real-time notifications) dono yahin se chalte hain.
Run (local): python manage.py runserver      (settings me 'daphne' hone par ASGI chalta hai)
Run (production): daphne -b 0.0.0.0 -p $PORT config.asgi:application
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Django pehle load hona chahiye, uske baad hi models/routing import karo
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from tickets.routing import websocket_urlpatterns  # noqa: E402
from tickets.ws_auth import TokenAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        TokenAuthMiddleware(URLRouter(websocket_urlpatterns))
    ),
})
