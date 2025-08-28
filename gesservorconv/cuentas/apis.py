from django.urls import URLPattern, URLResolver, path

from .controllers import ControladorUsuario

urlpatterns: list[URLPattern | URLResolver] = [
    path('', ControladorUsuario.as_view(), name='usuarios')
]
