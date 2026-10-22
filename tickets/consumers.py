"""WebSocket consumer: har logged-in user ko apne personal 'group' me daalta hai."""
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        await self.accept()
        if not user or not user.is_authenticated:
            # accept ke baad close, taaki browser ko code 4401 mile aur wo dobara try na kare
            await self.close(code=4401)
            return
        self.group = f'user_{user.pk}'
        await self.channel_layer.group_add(self.group, self.channel_name)

    async def disconnect(self, code):
        group = getattr(self, 'group', None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def notify(self, event):
        """notifications.push() ka group_send yahan aata hai aur browser ko forward hota hai."""
        await self.send_json({'type': 'notification', 'notification': event['payload']})
