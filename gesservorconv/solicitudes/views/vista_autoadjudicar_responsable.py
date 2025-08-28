from typing import Any, Dict, Self
from django.contrib import messages
from django.contrib.postgres.functions import TransactionNow
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from ..models import (
    SolicitudServicio,
    ComitenteSolicitud,
    ResponsableSolicitud
)

from cuentas.models import Comitente, ResponsableTecnico, Secretario

from gesservorconv.mixins import MixinAccesoRequerido


class VistaAutoadjudicarResponsable(
    MixinAccesoRequerido,
    TemplateView
):
    template_name: str = "solicitudes/autoadjudicar_responsable.html"

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
        if not SolicitudServicio.objects.filter(
            Q(id_solicitud=solicitud)
        ).exists():
            messages.error(
                "No existe la solicitud de servicio"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_responsable")
            )
        if ResponsableSolicitud.objects.filter(
            Q(responsable_tecnico__usuario_responsable=request.user) &
            Q(solicitud_servicio__id_solicitud=solicitud) &
            Q(tiempo_decision_responsable__isnull=False)
        ).exists():
            messages.error(
                "Usted ya ha decidido sobre si es Responsable Técnico o no"
                " en esta solicitud de servicio"
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
        contexto["solicitud_servicio"] = SolicitudServicio.objects.get(
            Q(id_solicitud=solicitud)
        )
        contexto["usuario_responsable"] = ResponsableTecnico.objects.get(
            Q(usuario_responsable=request.user)
        )
        return render(
            request,
            self.template_name,
            contexto
        )

    def post(self: Self, request: HttpRequest, solicitud: int) -> HttpResponse:
        responsable_tecnico: ResponsableTecnico = ResponsableTecnico.objects.get(
            Q(usuario_responsable=request.user)
        )
        organizacion_responsable_tecnico: str = request.POST.get(
            "organizacion_responsable_tecnico", ""
        )
        organizacion: int = int(organizacion_responsable_tecnico)
        responsable_solicitud: ResponsableSolicitud = \
            ResponsableSolicitud(
                responsable_tecnico=responsable_tecnico,
                solicitud_servicio=SolicitudServicio.objects.get(
                    Q(id_solicitud=solicitud)
                ),
                razon_social_responsable=(
                    responsable_tecnico.razones_sociales_responsable[
                        organizacion-1
                    ] if organizacion > 0 else None
                ),
                cuit_organizacion_responsable=(
                    responsable_tecnico.cuit_organizaciones_responsable[
                        organizacion-1
                    ] if organizacion > 0 else None
                ),
                puesto_organizacion_responsable=(
                    responsable_tecnico.puestos_organizaciones_responsable[
                        organizacion-1
                    ] if organizacion > 0 else None
                ),
                tiempo_decision_responsable=TransactionNow(),
                tiempo_decision_comitente=None,
                aceptacion_responsable=True,
                aceptacion_comitente=False
            )
        solicitud_servicio: SolicitudServicio = \
            SolicitudServicio.objects.get(
                id_solicitud=solicitud
            )
        with transaction.atomic():
            responsable_solicitud.save()
            solicitud_servicio.save()
        messages.success(
            request,
            "Se ha autoadjudicado en la solicitud de servicio"
        )
        return HttpResponseRedirect(
            reverse_lazy("solicitudes:lista_solicitudes_responsable")
        )
