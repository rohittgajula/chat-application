"""
ASGI config for chat_service project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chat_app.routing
from chat_app.middleware import JWTAuthMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_service.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # Django views
    "websocket": JWTAuthMiddleware(
        URLRouter(
            chat_app.routing.websocket_urlpatterns
        )
    ),
})
