from django.conf import settings
from django.contrib import messages
from django.contrib.postgres.functions import TransactionNow
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import to_locale
from django.views.generic import TemplateView

from babel.numbers import format_decimal, parse_decimal
from decimal import Decimal
from typing import Any, Dict, Self

from ..models import (
    ComitenteSolicitud,
    DecisionComitentePropuesta,
    DecisionResponsableTecnicoPropuesta,
    PropuestaCompromisos,
    ResponsableSolicitud,
    SolicitudServicio
)

from cuentas.models import Comitente, ResponsableTecnico, Secretario

from gesservorconv.mixins import MixinAccesoRequerido
from gesservorconv.views import HtmxHttpRequest


class VistaNuevaPropuesta(
    MixinAccesoRequerido,
    TemplateView
):
    template_name: str = "solicitudes/agregar_propuesta.html"

    def get_context_data(
        self: Self,
        **kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
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

    def get(
        self: Self,
        request: HtmxHttpRequest,
        solicitud: int
    ) -> HttpResponse:
        if request.htmx:
            if (
                request.htmx.trigger_name in [
                    "boton-borrado-compromiso-comitente",
                    "boton-borrado-compromiso-unidad-ejecutora",
                    "boton-borrado-retribucion-economica"
                ]
            ):
                return HttpResponse("")
            contexto: dict[str, Any] = dict()
            indice: str = request.GET.get("numero", "0")
            numero: int = int(indice)
            contexto["indice"] = numero
            if (
                request.htmx.trigger_name ==
                "boton-creado-compromiso-comitente"
            ):
                descripcion: str = request.GET.get(
                    f"creado_descripcion_compromiso_comitente_{indice}",
                    ""
                )
                contexto[
                    "descripcion_compromiso_comitente"
                ] = descripcion.strip()
                return render(
                    request,
                    "parciales/_nuevo_compromiso_comitente.html",
                    contexto
                )
            if (
                request.htmx.trigger_name ==
                "boton-editado-compromiso-comitente"
            ):
                descripcion: str = request.GET.get(
                    f"editado_descripcion_compromiso_comitente_{indice}",
                    ""
                )
                contexto[
                    "descripcion_compromiso_comitente"
                ] = descripcion.strip()
                return render(
                    request,
                    "parciales/_editado_compromiso_comitente.html",
                    contexto
                )
            if (
                request.htmx.trigger_name ==
                "boton-creado-compromiso-unidad-ejecutora"
            ):
                descripcion: str = request.GET.get(
                    f"creado_descripcion_compromiso_unidad_ejecutora_{indice}",
                    ""
                )
                contexto[
                    "descripcion_compromiso_unidad_ejecutora"
                ] = descripcion.strip()
                return render(
                    request,
                    "parciales/_nuevo_compromiso_unidad_ejecutora.html",
                    contexto
                )
            if (
                request.htmx.trigger_name ==
                "boton-editado-compromiso-unidad-ejecutora"
            ):
                descripcion: str = request.GET.get(
                    f"editado_descripcion_compromiso_unidad_ejecutora_{indice}",
                    ""
                )
                contexto[
                    "descripcion_compromiso_unidad_ejecutora"
                ] = descripcion.strip()
                return render(
                    request,
                    "parciales/_editado_compromiso_unidad_ejecutora.html",
                    contexto
                )
            if (
                request.htmx.trigger_name ==
                "boton-creado-retribucion-economica"
            ):
                lenguaje: str = request.GET.get(
                    "local", settings.LANGUAGE_CODE
                )
                descripcion: str = request.GET.get(
                    f"creado_descripcion_retribucion_economica_{indice}",
                    ""
                )
                contexto[
                    "descripcion_retribucion_economica"
                ] = descripcion.strip()
                monto: str = request.GET.get(
                    f"creado_monto_retribucion_economica_{indice}",
                    ""
                )
                contexto[
                    "monto_retribucion_economica"
                ] = format_decimal(
                    Decimal(monto),
                    format="0.00",
                    locale=to_locale(lenguaje),
                    group_separator=False
                )
                contexto[
                    "nuevo_monto"
                ] = format_decimal(
                    0.0,
                    format="0.00",
                    locale=to_locale(lenguaje),
                    group_separator=False
                )
                return render(
                    request,
                    "parciales/_nueva_retribucion_economica.html",
                    contexto
                )
            if (
                request.htmx.trigger_name ==
                "boton-editado-retribucion-economica"
            ):
                descripcion: str = request.GET.get(
                    f"editado_descripcion_retribucion_economica_{indice}",
                    ""
                )
                contexto[
                    "descripcion_retribucion_economica"
                ] = descripcion.strip()
                monto: str = request.GET.get(
                    f"editado_monto_retribucion_economica_{indice}",
                    ""
                )
                contexto[
                    "monto_retribucion_economica"
                ] = Decimal(monto)
                return render(
                    request,
                    "parciales/_editado_retribucion_economica.html",
                    contexto
                )
        return super(
            VistaNuevaPropuesta,
            self
        ).get(request, solicitud=solicitud)

    def post(
        self: Self,
        request: HttpRequest,
        solicitud: int
    ) -> HttpResponse:
        lenguaje: str = request.POST.get(
            "local", settings.LANGUAGE_CODE
        )
        descripciones_compromisos_comitente: list[str] = \
            request.POST.getlist(
                "descripcion_compromiso_comitente",
                []
            )
        descripciones_compromisos_unidad_ejecutora: list[str] = \
            request.POST.getlist(
                "descripcion_compromiso_unidad_ejecutora",
                []
            )
        montos_retribuciones_economicas: list[str] = \
            request.POST.getlist(
                "monto_retribucion_economica",
                []
            )
        descripciones_retribuciones_economicas: list[str] = \
            request.POST.getlist(
                "descripcion_retribucion_economica",
                []
            )
        if (
            descripciones_compromisos_unidad_ejecutora == [] or
            montos_retribuciones_economicas == [] or
            descripciones_retribuciones_economicas == []
        ):
            messages.error(
                request,
                "La propuesta de compromisos está incompleta"
            )
            return super(
                VistaNuevaPropuesta,
                self
            ).get(request, solicitud=solicitud)
        with transaction.atomic():
            propuesta_compromisos: PropuestaCompromisos = \
                PropuestaCompromisos(
                    solicitud_servicio_propuesta=SolicitudServicio.objects.get(
                        id_solicitud=solicitud
                    ),
                    descripciones_compromisos_comitente=[
                        descripcion.strip() for descripcion in
                        descripciones_compromisos_comitente
                    ],
                    descripciones_compromisos_unidad_ejecutora=[
                        descripcion.strip() for descripcion in
                        descripciones_compromisos_unidad_ejecutora
                    ],
                    montos_retribuciones_economicas=[
                        parse_decimal(
                            monto[2:], to_locale(lenguaje)
                        ) for monto in
                        montos_retribuciones_economicas
                    ],
                    descripciones_retribuciones_economicas=[
                        descripcion.strip() for descripcion in
                        descripciones_retribuciones_economicas
                    ],
                    es_valida_propuesta=True
                )
            propuesta_compromisos.save()
            decision_responsable_tecnico_propuesta: DecisionResponsableTecnicoPropuesta
            decision_responsable_tecnico_propuesta = \
                DecisionResponsableTecnicoPropuesta(
                    responsable_solicitud=ResponsableSolicitud.objects.get(
                        responsable_tecnico__usuario_responsable=request.user,
                        solicitud_servicio__id_solicitud=solicitud
                    ),
                    propuesta_compromisos=propuesta_compromisos,
                    tiempo_decision_propuesta=TransactionNow(),
                    aceptacion_propuesta=True
                )
            decision_responsable_tecnico_propuesta.save()
            for responsable_solicitud in ResponsableSolicitud.objects.filter(
                ~Q(
                    responsable_tecnico__usuario_responsable=request.user
                ) &
                Q(solicitud_servicio__id_solicitud=solicitud) &
                Q(aceptacion_comitente=True) &
                Q(aceptacion_responsable=True)
            ):
                decision_responsable_tecnico_propuesta = \
                    DecisionResponsableTecnicoPropuesta(
                        responsable_solicitud=responsable_solicitud,
                        propuesta_compromisos=propuesta_compromisos,
                        tiempo_decision_propuesta=None,
                        aceptacion_propuesta=False
                    )
                decision_responsable_tecnico_propuesta.save()
            decision_comitente_propuesta: DecisionComitentePropuesta
            for comitente_solicitud in ComitenteSolicitud.objects.filter(
                solicitud_servicio__id_solicitud=solicitud,
                aceptacion=True
            ):
                decision_comitente_propuesta = \
                    DecisionComitentePropuesta(
                        comitente_solicitud=comitente_solicitud,
                        propuesta_compromisos=propuesta_compromisos,
                        tiempo_decision_propuesta=None,
                        aceptacion_propuesta=False
                    )
                decision_comitente_propuesta.save()
            SolicitudServicio.objects.get(
                id_solicitud=solicitud
            ).save()
        messages.success(
            request,
            "Se ha propuesto los compromisos correctamente"
        )
        return HttpResponseRedirect(
            reverse_lazy("solicitudes:lista_solicitudes_responsable")
        )
