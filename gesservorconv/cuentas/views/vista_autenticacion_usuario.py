from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import base36_to_int, urlsafe_base64_decode
from django.views.generic import FormView

from typing import Any, Dict, Self, Optional
from datetime import datetime

from ..models import Comitente, ResponsableTecnico, Secretario
from ..tokens import generador_token_autenticacion_usuario


class VistaAutenticacionUsuario(
    UserPassesTestMixin,
    FormView
):
    template_name: str = "cuentas/autenticar_usuario.html"

    def test_func(self: Self) -> bool:
        return self.request.user.is_anonymous

    def handle_no_permission(self: Self) -> HttpResponse:
        if self.request.user.is_staff:
            return HttpResponseRedirect(
                reverse_lazy("auditoria:index")
            )
        return HttpResponseRedirect(
            reverse_lazy("cuentas:perfil")
        )

    def get_context_data(self: Self, **kwargs: Dict[str, Any]):
        contexto: Dict[str, Any] = {}
        contexto["siguiente"] = self.request.GET.get("siguiente")
        return contexto

    def get_success_url(self: Self) -> str:
        if self.request.user.is_staff or self.request.user.is_superuser:
            return reverse_lazy("auditoria:index")
        if self.request.user.groups.filter(
            name="ayudante"
        ).exists():
            return reverse_lazy("cuentas:ayudante")
        if Secretario.objects.filter(
            usuario_secretario=self.request.user,
            habilitado_secretario=True
        ).exists():
            return reverse_lazy("cuentas:secretario")
        if (
            self.request.user.groups.filter(
                name="comitente"
            ).exists() and
            not self.request.user.groups.filter(
                name="responsable_tecnico"
            ).exists()
        ):
            return reverse_lazy("cuentas:comitente")
        if (
            self.request.user.groups.filter(
                name="responsable_tecnico"
            ).exists() and
            not self.request.user.groups.filter(
                name="comitente"
            ).exists()
        ):
            return reverse_lazy("cuentas:responsable_tecnico")
        return reverse_lazy("cuentas:perfil")

    def get(
        self: Self,
        request: HttpRequest,
        uidb64: str,
        token: str
    ) -> HttpResponse:
        respuesta: HttpResponse = HttpResponseRedirect(
            reverse_lazy("cuentas:iniciar_sesion")
        )
        uid: str = force_str(
            urlsafe_base64_decode(uidb64)
        )
        if not User.objects.filter(pk=uid).exists():
            messages.error(
                request,
                "El enlace no es válido para autenticar una cuenta"
                " de usuario."
            )
            return respuesta
        partes: tuple[str, str, str] = token.partition("-")
        if (partes[1] != "-") or ("-" in partes[2]):
            messages.error(
                request,
                "El enlace no es válido para autenticar una cuenta"
                " de usuario."
            )
            return respuesta
        mt_b36: str = partes[0]
        mt: int
        try:
            mt = base36_to_int(mt_b36)
        except ValueError:
            messages.error(
                request,
                "El enlace no es válido para autenticar una cuenta"
                " de usuario."
            )
            return respuesta
        if int(
            (datetime.now() - datetime(2001, 1, 1)).total_seconds()
        ) - mt > settings.PASSWORD_RESET_TIMEOUT:
            messages.error(
                request,
                "El enlace ya ha expirado para ser utilizado en la"
                " autenticación de una cuenta de usuario."
            )
            return respuesta
        clave: str = partes[2]
        if len(clave) != 32:
            messages.error(
                request,
                "El token no es válido para ser utilizado en la"
                " autenticación de una cuenta de usuario."
            )
            return respuesta
        return render(
            request,
            self.template_name,
            self.get_context_data()
        )

    def post(
        self: Self,
        request: HttpRequest,
        uidb64: str,
        token: str
    ) -> HttpResponse:
        usuario: User
        respuesta: HttpResponse = HttpResponseRedirect(
            reverse_lazy("cuentas:iniciar_sesion")
        )
        try:
            uid: str = force_str(
                urlsafe_base64_decode(uidb64)
            )
            usuario = User.objects.get(pk=uid)
        except (
            TypeError,
            ValueError,
            OverflowError,
            User.DoesNotExist,
            ValidationError
        ):
            messages.error(
                request,
                "El enlace no es válido para autenticar ninguna cuenta"
                " de usuario. Vuelva a intentar un nuevo inicio de sesión."
            )
            return respuesta
        codigo: Optional[str] = request.POST.get("codigo")
        if codigo is None:
            messages.error(
                request,
                "La petición no contiene ningún código para autenticar la"
                " cuenta de usuario. Vuelva a intentar un nuevo"
                " inicio de sesión."
            )
            return self.render_to_response({})
        if not generador_token_autenticacion_usuario.revisar_token(
            usuario, token, codigo
        ):
            messages.error(
                request,
                "El código de autenticación es incorrecto o el enlace"
                " no es válido."
            )
            return self.render_to_response({})
        login(request, usuario)
        messages.success(
            request,
            "Ha iniciado sesión correctamente como %(username)s" % {
                "username": usuario.username
            }
        )
        redireccion: Optional[str] = request.POST.get("siguiente")
        return HttpResponseRedirect(
            redireccion
            if redireccion and redireccion.startswith("/")
            else self.get_success_url()
        )
