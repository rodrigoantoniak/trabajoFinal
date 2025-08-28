from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.http import (
    HttpRequest,
    HttpResponseForbidden,
    JsonResponse
)
from django.shortcuts import render

from django_hosts import reverse_host

from .hosts import (
    nombre_apis6,
    nombre_apis4,
    nombre_administrador6,
    nombre_administrador4
)


def failure(
    request: HttpRequest,
    reason: str = ''
) -> HttpResponseForbidden:
    huesped: str = request.get_host().partition(':')[0]
    if (huesped == reverse_host(settings.DEFAULT_HOST)):
        formulario: AuthenticationForm = AuthenticationForm(request)
        formulario.cleaned_data = {}
        formulario.add_error(
            None,
            'El tiempo para rellenar el formulario ha expirado'
        )
        redireccion: str = request.GET.get('siguiente', '')
        return render(
            request,
            'cuentas/iniciar_sesion.html',
            {
                'form': formulario,
                'siguiente': redireccion if redireccion != '' else '/'
            },
            status=403
        )
    if (
        huesped == reverse_host(nombre_administrador6) or
        huesped == reverse_host(nombre_administrador4)
    ):
        formulario: AuthenticationForm = AuthenticationForm(request)
        formulario.cleaned_data = {}
        formulario.add_error(None, 'CSRF: error')
        redireccion: str = request.GET.get('next', '')
        return render(
            request,
            'admin/login.html',
            {
                'form': formulario,
                'next': redireccion if redireccion != '' else '/'
            },
            status=403
        )
    if (
        huesped == reverse_host(nombre_apis6) or
        huesped == reverse_host(nombre_apis4)
    ):
        return JsonResponse(
            status=403,
            data={
                'codigo': 'Acceso denegado',
                'excepcion': 'Hubo una falla al verificar CSRF,'
                             ' abortando la solicitud'
            },
            headers={
                'Content-Language': 'es-AR'
            }
        )
    raise PermissionDenied(
        'Hubo una falla al verificar CSRF, abortando la solicitud'
    )
