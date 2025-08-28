from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.contrib.postgres.functions import TransactionNow
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from typing import Any, Dict, Optional, Self

from ..models import (
    SolicitudServicio,
    ComitenteSolicitud,
    ResponsableSolicitud
)

from cuentas.models import (
    Comitente,
    ResponsableTecnico,
    Secretario
)

from gesservorconv.mixins import MixinAccesoRequerido


class VistaDecisionResponsables(
    MixinAccesoRequerido,
    UserPassesTestMixin,
    TemplateView
):
    template_name: str = "solicitudes/decidir_responsables.html"

    def test_func(self: Self) -> bool:
        return Comitente.objects.filter(
            usuario_comitente=self.request.user
        ).exists

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
        if ComitenteSolicitud.objects.filter(
            Q(solicitud_servicio__id_solicitud=solicitud) &
            Q(aceptacion=False)
        ).exists():
            messages.error(
                request,
                "No todos los Comitentes aceptaron su rol en la solicitud de"
                " servicio"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        if ResponsableSolicitud.objects.filter(
            Q(solicitud_servicio__id_solicitud=solicitud)
        ).exists():
            messages.error(
                request,
                "Ya hay Responsables Técnicos en la solicitud de servicio"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        if SolicitudServicio.objects.filter(
            Q(id_solicitud=solicitud) &
            Q(cancelacion_solicitud__isnull=False)
        ).exists():
            messages.error(
                request,
                "Este servicio se encuentra cancelado"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        if SolicitudServicio.objects.filter(
            Q(id_solicitud=solicitud) &
            (
                Q(solicitud_suspendida__isnull=True) |
                Q(solicitud_suspendida=True)
            )
        ).exists():
            messages.error(
                request,
                "Este servicio se encuentra suspendido"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        contexto: Dict[str, Any] = {}
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
        contexto["solicitud"] = solicitud
        contexto["responsables_solicitud"] = \
            ResponsableTecnico.objects.exclude(
                usuario_responsable__id__in=ComitenteSolicitud.objects.filter(
                    solicitud_servicio__id_solicitud=solicitud
                ).values_list(
                    "comitente__usuario_comitente__id",
                    flat=True
                )
            )
        return render(
            request,
            self.template_name,
            contexto
        )

    def post(
        self: Self,
        request: HttpRequest,
        solicitud: int
    ) -> HttpResponse:
        solicitud_servicio: SolicitudServicio = \
            SolicitudServicio.objects.get(
                id_solicitud=solicitud
            )
        autoadjudicados: Optional[str] = request.POST.get(
            "autoadjudicados"
        )
        responsables: list[str] = []
        if (
            "responsables" in dict(
                request.POST.lists()
            )
        ):
            responsables = dict(
                request.POST.lists()
            )["responsables"]
        with transaction.atomic():
            partes: tuple[str, str, str]
            responsable: ResponsableTecnico
            indice: int
            responsable_solicitud: ResponsableSolicitud
            if autoadjudicados:
                solicitud_servicio.responsables_autoadjudicados = True
                solicitud_servicio.autoadjudicacion_abierta = True
            else:
                for responsable_tecnico in responsables:
                    partes = responsable_tecnico.partition(":")
                    responsable = ResponsableTecnico.objects.get(
                        cuil_responsable=partes[0]
                    )
                    indice = int(partes[2])
                    responsable_solicitud = ResponsableSolicitud(
                        responsable_tecnico=responsable,
                        solicitud_servicio=solicitud_servicio,
                        razon_social_responsable=(
                            responsable.razones_sociales_responsable[
                                indice-1
                            ] if indice > 0 else None
                        ),
                        cuit_organizacion_responsable=(
                            responsable.cuit_organizaciones_responsable[
                                indice-1
                            ] if indice > 0 else None
                        ),
                        puesto_organizacion_responsable=(
                            responsable.puestos_organizaciones_responsable[
                                indice-1
                            ] if indice > 0 else None
                        ),
                        tiempo_decision_comitente=TransactionNow(),
                        tiempo_decision_responsable=None,
                        aceptacion_comitente=True,
                        aceptacion_responsable=False
                    )
                    responsable_solicitud.save()
            solicitud_servicio.save()
        messages.success(
            request,
            "La solicitud se encuentra abierta para los Responsables Técnicos"
            if autoadjudicados
            else "Ha seleccionado a los Responsables Técnicos correctamente"
        )
        return HttpResponseRedirect(
            reverse_lazy("solicitudes:lista_solicitudes_comitente")
        )
