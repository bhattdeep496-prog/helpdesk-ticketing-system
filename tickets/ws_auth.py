"""
WebSocket login: browser token URL ke query me bhejta hai: /ws/notifications/?token=<key>
(Token wahi hai jo REST API me use hota hai.)
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _user_for_token(key):
    from rest_framework.authtoken.models import Token
    try:
        user = Token.objects.select_related('user').get(key=key).user
    except Token.DoesNotExist:
        return AnonymousUser()
    return user if user.is_active else AnonymousUser()


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get('query_string', b'').decode())
        key = (query.get('token') or [''])[0]
        scope['user'] = await _user_for_token(key) if key else AnonymousUser()
        return await super().__call__(scope, receive, send)
