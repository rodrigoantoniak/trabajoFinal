from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import generic

from typing import Optional, Self

from ..tokens import generador_token_activacion_cuenta


class VistaActivacionCuenta(generic.View):
    def get(
        self: Self,
        request: HttpRequest,
        uidb64: str,
        token: str
    ) -> HttpResponse:
        usuario: Optional[User]
        respuesta: HttpResponse = HttpResponseRedirect(
            reverse_lazy('cuentas:iniciar_sesion')
        )
        try:
            uid: str = force_str(
                urlsafe_base64_decode(uidb64)
            )
            usuario = User.objects.get(pk=uid)
        except (
            TypeError, ValueError, OverflowError,
            User.DoesNotExist, ValidationError
        ):
            messages.error(
                request,
                'El enlace no es válido para activar una cuenta'
                ' de usuario.'
            )
            return respuesta
        if (
            usuario is None or
            not generador_token_activacion_cuenta.revisar_token(
                usuario,
                token
            )
        ):
            messages.error(
                request,
                'El enlace no es válido para activar una cuenta'
                ' de usuario.'
            )
            return respuesta
        usuario.is_active = True
        usuario.save()
        messages.success(
            request,
            'El usuario ha sido activado correctamente.'
            ' Ahora, puede iniciar sesión con él.'
        )
        return respuesta
