from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.postgres.functions import TransactionNow
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from typing import Any, Dict, Self

from ..models import ComitenteSolicitud, SolicitudServicio

from cuentas.models import (
    Comitente,
    ResponsableTecnico,
    Secretario
)

from gesservorconv.mixins import MixinAccesoRequerido


class VistaRecuperarSolicitudComitente(
    UserPassesTestMixin,
    MixinAccesoRequerido,
    TemplateView
):
    template_name: str = "solicitudes/recuperar_solicitud_comitente.html"

    def test_func(self: Self) -> bool:
        return Comitente.objects.filter(
            Q(usuario_comitente=self.request.user) & (
                Q(habilitado_comitente__isnull=False) &
                Q(habilitado_comitente=True)
            ) | (
                Q(habilitado_organizaciones_comitente__len__gt=0) &
                Q(habilitado_organizaciones_comitente__overlap=[True])
            )
        ).exists()

    def handle_no_permission(self: Self) -> HttpResponse:
        if self.request.user.is_anonymous:
            direccion: str = (
                reverse_lazy("cuentas:iniciar_sesion") +
                "?siguiente=" + self.request.path
            )
            if self.request.htmx:
                return HttpResponse(
                    self.request.get_full_path(),
                    headers={
                        "HX-Redirect": direccion
                    }
                )
            return HttpResponseRedirect(direccion)
        if self.request.user.is_staff or self.request.user.is_superuser:
            logout(self.request)
            messages.error(
                self.request,
                (
                    "El usuario %(nombre)s no tiene permiso a"
                    " esta página. Por ello, se ha cerrado"
                    " la sesión."
                ) % {
                    "nombre": self.request.user.username
                }
            )
            return HttpResponseRedirect(
                reverse_lazy("cuentas:iniciar_sesion")
            )
        return HttpResponseRedirect(
            reverse_lazy('cuentas:perfil')
        )

    def get_context_data(
        self: Self,
        **kwargs: Dict[str, Any]
    ):
        contexto: Dict[str, Any] = super().get_context_data(**kwargs)
        contexto["usuario"] = self.request.user
        contexto["comitente"] = Comitente.objects.filter(
            Q(usuario_comitente=self.request.user) &
            (
                Q(habilitado_comitente=True) |
                Q(habilitado_organizaciones_comitente__contains=[
                    True
                ])
            )
        ).exists() if Comitente.objects.filter(
            Q(usuario_comitente=self.request.user) &
            Q(usuario_comitente__is_active=True)
        ).exists() else None
        contexto["responsable"] = ResponsableTecnico.objects.filter(
            Q(usuario_responsable=self.request.user) &
            (
                Q(habilitado_responsable=True) |
                Q(habilitado_organizaciones_responsable__contains=[
                    True
                ])
            )
        ).exists() if ResponsableTecnico.objects.filter(
            Q(usuario_responsable=self.request.user) &
            Q(usuario_responsable__is_active=True)
        ).exists() else None
        contexto["secretario"] = Secretario.objects.filter(
            Q(usuario_secretario=self.request.user) &
            Q(habilitado_secretario=True)
        ).exists() if Secretario.objects.filter(
            Q(usuario_secretario=self.request.user) &
            Q(usuario_secretario__is_active=True)
        ).exists() else None
        contexto["staff"] = self.request.user.is_staff
        contexto["admin"] = self.request.user.is_superuser
        return contexto

    def get(self: Self, request: HttpRequest, solicitud: int) -> HttpResponse:
        if not SolicitudServicio.objects.filter(
            Q(id_solicitud=solicitud)
        ).exists():
            messages.error(
                request,
                "No existe la solicitud de servicio"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        if not ComitenteSolicitud.objects.filter(
            Q(comitente__usuario_comitente=request.user) &
            Q(solicitud_servicio__id_solicitud=solicitud) &
            Q(aceptacion=True)
        ).exists():
            messages.error(
                request,
                "Usted no es Comitente en este servicio"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        contexto: Dict[str, Any] = self.get_context_data(
            solicitud_servicio=SolicitudServicio.objects.get(
                id_solicitud=solicitud
            )
        )
        return render(
            request,
            self.template_name,
            contexto
        )

    def post(self: Self, request: HttpRequest, solicitud: int) -> HttpResponse:
        if not SolicitudServicio.objects.filter(
            Q(id_solicitud=solicitud)
        ).exists():
            messages.error(
                request,
                "No existe la solicitud de servicio"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        if not ComitenteSolicitud.objects.filter(
            Q(comitente__usuario_comitente=request.user) &
            Q(solicitud_servicio__id_solicitud=solicitud) &
            Q(aceptacion=True)
        ).exists():
            messages.error(
                request,
                "Usted no es Comitente en este servicio"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        solicitud_servicio: SolicitudServicio = SolicitudServicio.objects.get(
            id_solicitud=solicitud
        )
        solicitud_servicio.solicitud_suspendida = False
        solicitud_servicio.ultima_accion_solicitud = TransactionNow()
        solicitud_servicio.save()
        messages.success(
            request,
            "Se ha recuperado la solicitud correctamente"
        )
        return HttpResponseRedirect(
            reverse_lazy('solicitudes:lista_solicitudes_comitente')
        )
