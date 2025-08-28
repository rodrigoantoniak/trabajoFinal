from django.conf import settings
from django.http import JsonResponse, HttpRequest, HttpResponse

from django_hosts import reverse_host

from .hosts import (
    nombre_apis6,
    nombre_apis4,
    nombre_administrador6,
    nombre_administrador4
)


def view(request: HttpRequest) -> HttpResponse:
    huesped: str = request.get_host().partition(':')[0]
    if (huesped == reverse_host(settings.DEFAULT_HOST)):
        respuesta: HttpResponse = HttpResponse(
            status=429
        )
        respuesta.headers['Retry-After'] = 3600
        return respuesta
    if (
        huesped == reverse_host(nombre_administrador6) or
        huesped == reverse_host(nombre_administrador4)
    ):
        respuesta: HttpResponse = HttpResponse(
            status=429
        )
        respuesta.headers['Retry-After'] = 3600
        return respuesta
    if (
        huesped == reverse_host(nombre_apis6) or
        huesped == reverse_host(nombre_apis4)
    ):
        respuesta: JsonResponse = JsonResponse(
            status=429,
            data={
                'codigo': 'Demasiadas peticiones',
                'excepcion': 'Se ha excedido el numero de peticiones'
                             ' en este sitio'
            },
            headers={
                'Content-Language': 'es-AR'
            }
        )
        respuesta.headers['Retry-After'] = 3600
        return respuesta
