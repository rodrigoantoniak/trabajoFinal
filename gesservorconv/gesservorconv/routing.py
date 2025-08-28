from django.urls import path

from channels.routing import URLRouter

from cuentas import routing as cuentas_routing

websocket_urlpatterns: URLRouter = URLRouter([
    path('cuenta/', cuentas_routing.websocket_urlpatterns)
])
