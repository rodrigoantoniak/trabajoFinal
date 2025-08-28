"""
ASGI config for servorges project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter
from channels.security.websocket import AllowedHostsOriginValidator

from .handlers import ManejadorASGI, obtener_aplicacion_asgi
from .routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gesservorconv.settings')

manejador_asgi: ManejadorASGI = obtener_aplicacion_asgi()
application: ProtocolTypeRouter = ProtocolTypeRouter({
    'http': manejador_asgi,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            websocket_urlpatterns
        )
    )
})
