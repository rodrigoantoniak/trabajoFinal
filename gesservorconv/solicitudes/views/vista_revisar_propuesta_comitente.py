from typing import Any, Dict, Optional, Self
from django.contrib import messages
from django.contrib.postgres.functions import TransactionNow
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from ..models import (
    DecisionComitentePropuesta,
    DecisionResponsableTecnicoPropuesta,
    SolicitudServicio,
    ComitenteSolicitud,
    PropuestaCompromisos
)

from firmas.models import Convenio, OrdenServicio

from cuentas.models import Comitente, ResponsableTecnico, Secretario

from gesservorconv.mixins import MixinAccesoRequerido


class VistaRevisarPropuestaComitente(
    MixinAccesoRequerido,
    TemplateView
):
    template_name: str = "solicitudes/revisar_propuesta_comitente.html"

    def handle_no_permission(self) -> HttpResponse:
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
        contexto["propuesta_compromisos"] = PropuestaCompromisos.objects.get(
            Q(es_valida_propuesta=True) &
            Q(solicitud_servicio_propuesta__id_solicitud=solicitud)
        )
        return render(
            request,
            self.template_name,
            contexto
        )

    def post(self: Self, request: HttpRequest, solicitud: int) -> HttpResponse:
        solicitud_servicio: SolicitudServicio = \
            SolicitudServicio.objects.get(
                id_solicitud=solicitud
            )
        propuesta_compromisos: PropuestaCompromisos = \
            PropuestaCompromisos.objects.get(
                Q(es_valida_propuesta=True) &
                Q(solicitud_servicio_propuesta=solicitud_servicio)
            )
        decision_comitente_propuesta: DecisionComitentePropuesta = \
            DecisionComitentePropuesta.objects.get(
                Q(propuesta_compromisos=propuesta_compromisos),
                Q(comitente_solicitud__comitente__usuario_comitente=request.user)
            )
        decision_propuesta: Optional[str] = request.POST.get(
            "decision_propuesta"
        )
        if decision_propuesta:
            decision_comitente_propuesta.tiempo_decision_propuesta = TransactionNow()
            if decision_propuesta != "aceptar":
                causa_rechazo_propuesta: str = request.POST.get(
                    "causa_rechazo_propuesta", ""
                )
                propuesta_compromisos.es_valida_propuesta = False
                propuesta_compromisos.causa_rechazo_propuesta = causa_rechazo_propuesta
                '''
                propuesta_compromisos.causa_rechazo_propuesta = causa_rechazo_propuesta
                '''
                if decision_propuesta == "cancelar":
                    solicitud_servicio.cancelacion_solicitud = TransactionNow()
            else:
                decision_comitente_propuesta.aceptacion_propuesta = True
                if not (
                    (
                        DecisionComitentePropuesta.objects.filter(
                            ~Q(comitente_solicitud__comitente__usuario_comitente=request.user) &
                            Q(propuesta_compromisos=propuesta_compromisos)
                        ).exists() and
                        DecisionComitentePropuesta.objects.filter(
                            ~Q(comitente_solicitud__comitente__usuario_comitente=request.user) &
                            Q(propuesta_compromisos=propuesta_compromisos) &
                            ~Q(aceptacion_propuesta=True)
                        ).exists()
                     ) or
                    DecisionResponsableTecnicoPropuesta.objects.filter(
                        Q(propuesta_compromisos=propuesta_compromisos) &
                        ~Q(aceptacion_propuesta=True)
                    ).exists()
                ):
                    if solicitud_servicio.por_convenio:
                        convenio: Convenio = Convenio(
                            solicitud_servicio=solicitud_servicio,
                            archivo_convenio=None,
                            tiempo_creacion_convenio=TransactionNow(),
                            tiempo_subida_convenio=None,
                            cancelacion_convenio=None,
                            causa_cancelacion_convenio=None,
                            convenio_suspendido=False
                        )
                        convenio.save()
                    else:
                        orden_servicio: OrdenServicio = OrdenServicio(
                            solicitud_servicio=solicitud_servicio,
                            numero_orden_servicio=OrdenServicio.objects.order_by(
                                "-numero_orden_servicio"
                            ).first().numero_orden_servicio + 1
                            if OrdenServicio.objects.exists() else 1,
                            tiempo_creacion_orden=TransactionNow(),
                            firma_digital=(
                                all(
                                    DecisionComitentePropuesta.objects.filter(
                                        Q(propuesta_compromisos=propuesta_compromisos)
                                    ).values_list(
                                        "comitente_solicitud__comitente__firma_digital_comitente",
                                        flat=True
                                    )
                                ) and
                                all(
                                    DecisionResponsableTecnicoPropuesta.objects.filter(
                                        Q(propuesta_compromisos=propuesta_compromisos)
                                    ).values_list(
                                        "responsable_solicitud__responsable_tecnico__firma_digital_responsable",
                                        flat=True
                                    )
                                ) and
                                Secretario.objects.filter(
                                    habilitado_secretario=True
                                ).exists() and
                                all(
                                    Secretario.objects.filter(
                                        habilitado_secretario=True
                                    ).values_list(
                                        "firma_digital_secretario",
                                        flat=True
                                    )
                                )
                            ),
                            archivo_orden_original=None,
                            archivo_orden_firmada=None,
                            cancelacion_orden=None,
                            causa_cancelacion_orden=None,
                            orden_suspendida=False
                        )
                        orden_servicio.save()
            with transaction.atomic():
                decision_comitente_propuesta.save()
                propuesta_compromisos.save()
                solicitud_servicio.save()
            messages.success(
                request,
                "Ha decidido sobre la propuesta de compromisos"
            )
            return HttpResponseRedirect(
                reverse_lazy("solicitudes:lista_solicitudes_comitente")
            )
        return HttpResponse("")
