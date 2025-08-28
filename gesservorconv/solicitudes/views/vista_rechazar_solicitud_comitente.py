from typing import Any, Dict, Self
from django.contrib import messages
from django.contrib.postgres.functions import TransactionNow
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from ..models import ComitenteSolicitud, SolicitudServicio

from cuentas.models import Comitente, ResponsableTecnico, Secretario

from gesservorconv.mixins import MixinAccesoRequerido


class VistaRechazarSolicitudComitente(
    MixinAccesoRequerido,
    TemplateView
):
    template_name: str = "solicitudes/rechazar_solicitud_comitente.html"

    def handle_no_permission(self) -> HttpResponse:
        messages.error(
            self.request,
            (
                "Para acceder a esta página, necesita"
                " iniciar sesión."
            )
        )
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

    def get(self: Self, request: HttpRequest, solicitud: int) -> HttpResponse:
        if not ComitenteSolicitud.objects.filter(
            Q(comitente__usuario_comitente=request.user) &
            Q(solicitud_servicio__id_solicitud=solicitud) &
            Q(tiempo_decision__isnull=True)
        ).exists():
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
        if not ComitenteSolicitud.objects.filter(
            Q(comitente__usuario_comitente=request.user) &
            Q(solicitud_servicio__id_solicitud=solicitud) &
            Q(tiempo_decision__isnull=True)
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
        comitente_solicitud: ComitenteSolicitud = \
            ComitenteSolicitud.objects.get(
                Q(comitente__usuario_comitente=request.user) &
                Q(solicitud_servicio__id_solicitud=solicitud)
            )
        solicitud_servicio: SolicitudServicio = \
            SolicitudServicio.objects.get(
                id_solicitud=solicitud
            )
        comitente_solicitud.tiempo_decision = TransactionNow()
        solicitud_servicio.cancelacion_solicitud = TransactionNow()
        with transaction.atomic():
            comitente_solicitud.save()
            solicitud_servicio.save()
        messages.error(
            request,
            "Ha rechazado ser Comitente en la solicitud de servicio"
            " definitivamente"
        )
        return HttpResponseRedirect(
            reverse_lazy("solicitudes:lista_solicitudes_comitente")
        )
