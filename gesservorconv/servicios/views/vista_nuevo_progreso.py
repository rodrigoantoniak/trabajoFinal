from django.contrib import messages
from django.db.models import Max, Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import FormView
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect

from decimal import Decimal
from typing import Any, Dict, Self

from ..forms import FormularioProgreso
from ..models import Progreso, Servicio

from cuentas.models import (
    Comitente,
    ResponsableTecnico,
    Secretario
)


class VistaNuevoProgreso(FormView):
    template_name: str = "servicios/nuevo_progreso.html"
    form_class: type[FormularioProgreso] = FormularioProgreso
    success_url: str = reverse_lazy("servicio:lista_servicios_responsable")

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
        contexto["servicio"] = servicio
        contexto["restante"] = Decimal("100") - Progreso.objects.filter(
            servicio_progreso__id_servicio=servicio
        ).aggregate(
            Max(
                "porcentaje_progreso",
                default=Decimal("0.00")
            )
        )["porcentaje_progreso__max"]
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
        formulario: FormularioProgreso = FormularioProgreso(request.POST)
        if formulario.is_valid():
            ser: Servicio = Servicio.objects.get(
                id_servicio=servicio
            )
            progreso: Progreso = Progreso(
                servicio_progreso=ser,
                descripcion_progreso=formulario.cleaned_data[
                    "descripcion_progreso"
                ],
                porcentaje_progreso=formulario.cleaned_data[
                    "porcentaje_progreso"
                ] + Progreso.objects.filter(
                    servicio_progreso__id_servicio=servicio
                ).aggregate(
                    Max(
                        "porcentaje_progreso",
                        default=Decimal("0.00")
                    )
                )["porcentaje_progreso__max"]
            )
            progreso.save()
            if Progreso.objects.filter(
                servicio_progreso__id_servicio=servicio
            ).aggregate(
                Max(
                    "porcentaje_progreso",
                    default=Decimal("0.00")
                )
            )["porcentaje_progreso__max"] == Decimal("100"):
                ser.completado = True
                ser.save()
            messages.success(
                request,
                "Se ha guardado el progreso correctamente"
            )
            return HttpResponseRedirect(
                reverse_lazy("servicios:lista_servicios_responsable")
            )
