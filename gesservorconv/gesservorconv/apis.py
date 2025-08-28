from django.http import JsonResponse
from django.urls import URLPattern, URLResolver, include, path

from .controllers import ControladorBase, ControladorCierreSesion


urlpatterns: list[URLPattern | URLResolver] = [
    path('', ControladorBase.as_view(), name='indice'),
    path('', include('favicon.urls')),
    path(
        'cerrar_sesion/',
        ControladorCierreSesion.as_view(),
        name='cierre_sesion'
    ),
    path('cuentas/', include('cuentas.apis')),
]

handler400 = lambda request, exception: JsonResponse(
    status=400,
    data={
        'codigo': 'Mala peticion',
        'excepcion': exception.args[0]
    },
    headers={
        'Content-Language': 'es-AR'
    }
)
handler403 = lambda request, exception: JsonResponse(
    status=403,
    data={
        'codigo': 'Acceso denegado',
        'excepcion': exception.args[0]
    },
    headers={
        'Content-Language': 'es-AR'
    }
)
handler404 = lambda request, exception: JsonResponse(
    status=404,
    data={
        'codigo': 'No encontrado',
        'excepcion': exception.args[0]
    },
    headers={
        'Content-Language': 'es-AR'
    }
)
handler500 = lambda request: JsonResponse(
    status=500,
    data={
        'codigo': 'Error interno de servidor'
    },
    headers={
        'Content-Language': 'es-AR'
    }
)
