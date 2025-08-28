from django.urls import path

from channels.routing import URLRouter

from .consumers import ConsumidorNotificaciones

websocket_urlpatterns: URLRouter = URLRouter([
    path('notificaciones/', ConsumidorNotificaciones.as_asgi())
])
