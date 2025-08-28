from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import FormView
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect

from typing import Any, Dict, Self

from ..forms import FormularioPago
from ..models import Pago, Servicio

from solicitudes.models import ComitenteSolicitud, PropuestaCompromisos

from cuentas.models import (
    Comitente,
    ResponsableTecnico,
    Secretario
)


class VistaNuevoPago(FormView):
    template_name: str = "servicios/nuevo_pago.html"
    form_class: type[FormularioPago] = FormularioPago
    success_url: str = reverse_lazy("servicios:lista_servicios_ayudante")

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
        request: HttpRequest,
        servicio: int
    ) -> HttpResponse:
        contexto: Dict[str, Any] = self.get_context_data()
        contexto["servicio"] = Servicio.objects.get(
            id_servicio=servicio
        )
        contexto["comitentes"] = ComitenteSolicitud.objects.filter(
            solicitud_servicio=contexto[
                "servicio"
            ].orden_servicio.solicitud_servicio
            if contexto["servicio"].convenio is None else
            contexto[
                "servicio"
            ].convenio.solicitud_servicio
        )
        contexto["restante"] = sum(
            PropuestaCompromisos.objects.get(
                solicitud_servicio_propuesta=contexto[
                    "servicio"
                ].orden_servicio.solicitud_servicio.id_solicitud
                if contexto["servicio"].convenio is None else
                contexto[
                    "servicio"
                ].convenio.solicitud_servicio.id_solicitud,
                es_valida_propuesta=True
            ).montos_retribuciones_economicas
        ) - sum(
            Pago.objects.filter(
                servicio_pago=contexto["servicio"]
            ).values_list(
                "monto_pago", flat=True
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
        servicio: int
    ) -> HttpResponse:
        formulario: FormularioPago = FormularioPago(request.POST)
        if formulario.is_valid():
            ser: Servicio = Servicio.objects.get(
                id_servicio=servicio
            )
            pago: Pago = Pago(
                servicio_pago=ser,
                comitente_pago=formulario.cleaned_data["comitente_pago"],
                monto_pago=formulario.cleaned_data["monto_pago"]
            )
            pago.save()
            if sum(
                PropuestaCompromisos.objects.get(
                    solicitud_servicio_propuesta=ser.orden_servicio.solicitud_servicio.id_solicitud
                    if ser.convenio is None else
                    ser.convenio.solicitud_servicio.id_solicitud,
                    es_valida_propuesta=True
                ).montos_retribuciones_economicas
            ) == sum(
                Pago.objects.filter(
                    servicio_pago=ser
                ).values_list(
                    "monto_pago", flat=True
                )
            ):
                ser.pagado = True
                ser.save()
            messages.success(
                request,
                "Se ha guardado el pago correctamente"
            )
            return HttpResponseRedirect(
                reverse_lazy("servicios:lista_servicios_ayudante")
            )
