from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.postgres.functions import TransactionNow
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from typing import Any, Dict, Self

from ..models import SolicitudServicio, ComitenteSolicitud

from cuentas.models import Comitente, ResponsableTecnico, Secretario

from gesservorconv.mixins import MixinAccesoRequerido


class VistaAceptarSolicitudComitente(
    MixinAccesoRequerido,
    UserPassesTestMixin,
    TemplateView
):
    template_name: str = "solicitudes/aceptar_solicitud_comitente.html"

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

    def get(self: Self, request: HttpRequest, solicitud: int) -> HttpResponse:
        if not SolicitudServicio.objects.filter(
            Q(id_solicitud=solicitud)
        ).exists():
            messages.error(
                "No existe la solicitud de servicio"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        if not ComitenteSolicitud.objects.filter(
            Q(comitente__usuario_comitente=request.user) &
            Q(solicitud_servicio__id_solicitud=solicitud)
        ).exists():
            messages.error(
                "Usted no es Comitente en este servicio"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        if ComitenteSolicitud.objects.filter(
            Q(comitente__usuario_comitente=request.user) &
            Q(solicitud_servicio__id_solicitud=solicitud) &
            Q(tiempo_decision__isnull=False)
        ).exists():
            messages.error(
                "Usted ya ha decidido sobre si es Comitente o no en esta"
                " solicitud de servicio"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        if SolicitudServicio.objects.filter(
            Q(id_solicitud=solicitud) &
            Q(cancelacion_solicitud__isnull=False)
        ).exists():
            messages.error(
                "Este servicio se encuentra cancelado"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        if SolicitudServicio.objects.filter(
            Q(id_solicitud=solicitud) &
            Q(solicitud_suspendida__isnull=False) &
            Q(solicitud_suspendida=True)
        ).exists():
            messages.error(
                "Este servicio se encuentra suspendido"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        contexto: Dict[str, Any] = {}
        contexto["usuario"] = request.user
        contexto["comitente"] = Comitente.objects.filter(
            Q(usuario_comitente=request.user) &
            (
                Q(habilitado_comitente=True) |
                Q(habilitado_organizaciones_comitente__contains=[
                    True
                ])
            )
        ).exists() if Comitente.objects.filter(
            Q(usuario_comitente=request.user) &
            Q(usuario_comitente__is_active=True)
        ).exists() else None
        contexto["responsable"] = ResponsableTecnico.objects.filter(
            Q(usuario_responsable=request.user) &
            (
                Q(habilitado_responsable=True) |
                Q(habilitado_organizaciones_responsable__contains=[
                    True
                ])
            )
        ).exists() if ResponsableTecnico.objects.filter(
            Q(usuario_responsable=request.user) &
            Q(usuario_responsable__is_active=True)
        ).exists() else None
        contexto["secretario"] = Secretario.objects.filter(
            Q(usuario_secretario=request.user) &
            Q(habilitado_secretario=True)
        ).exists() if Secretario.objects.filter(
            Q(usuario_secretario=request.user) &
            Q(usuario_secretario__is_active=True)
        ).exists() else None
        contexto["staff"] = request.user.is_staff
        contexto["admin"] = request.user.is_superuser
        contexto["comitente_solicitud"] = ComitenteSolicitud.objects.get(
            Q(comitente__usuario_comitente=request.user) &
            Q(solicitud_servicio__id_solicitud=solicitud)
        )
        return render(
            request,
            self.template_name,
            contexto
        )

    def post(self: Self, request: HttpRequest, solicitud: int) -> HttpResponse:
        if not ComitenteSolicitud.objects.filter(
            Q(comitente__usuario_comitente=request.user) &
            Q(solicitud_servicio__id_solicitud=solicitud) &
            Q(tiempo_decision__isnull=True)
        ).exists():
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        solicitud_servicio: SolicitudServicio = \
            SolicitudServicio.objects.get(
                id_solicitud=solicitud
            )
        comitente_solicitud: ComitenteSolicitud = \
            ComitenteSolicitud.objects.get(
                Q(comitente__usuario_comitente=request.user) &
                Q(solicitud_servicio=solicitud_servicio)
            )
        comitente_solicitud.tiempo_decision = TransactionNow()
        comitente_solicitud.aceptacion = True
        if not ComitenteSolicitud.objects.filter(
            Q(solicitud_servicio=solicitud_servicio) &
            Q(aceptacion=False)
        ).exclude(
            Q(comitente__usuario_comitente=request.user)
        ).exists():
            solicitud_servicio.solicitud_suspendida = False
        with transaction.atomic():
            comitente_solicitud.save()
            solicitud_servicio.save()
        messages.success(
            request,
            "Ha aceptado ser Comitente en la solicitud de servicio"
            " correctamente"
        )
        return HttpResponseRedirect(
            reverse_lazy("solicitudes:lista_solicitudes_comitente")
        )
