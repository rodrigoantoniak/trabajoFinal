from django.contrib import messages
from django.contrib.auth.models import Permission
from django.contrib.postgres.functions import TransactionNow
from django.db import transaction
from django.db.models import Q
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from typing import Any, Dict, Self

from ..models import Servicio

from solicitudes.models import ComitenteSolicitud, SolicitudServicio

from cuentas.models import Comitente, ResponsableTecnico, Secretario

from gesservorconv.mixins import MixinAccesoRequerido, MixinPermisoRequerido


class VistaCancelarServicio(
    MixinAccesoRequerido,
    MixinPermisoRequerido,
    TemplateView
):
    template_name: str = "servicios/cancelar_servicio.html"
    permission_required: QuerySet[Permission] = Permission.objects.filter(
        codename=f'change_{Servicio.__name__.lower()}'
    )

    def test_func(self: Self) -> bool:
        return Secretario.objects.filter(
            usuario_secretario=self.request.user,
            habilitado_secretario=True
        ).exists()

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

    def get(self: Self, request: HttpRequest, servicio: int) -> HttpResponse:
        if not Servicio.objects.filter(
            Q(id_servicio=servicio)
        ).exists():
            messages.error(
                "No existe el servicio"
            )
            return HttpResponseRedirect(
                reverse_lazy("servicios:lista_servicios_secretario")
            )
        if Servicio.objects.filter(
            Q(id_servicio=servicio) &
            Q(cancelacion_servicio__isnull=False)
        ).exists():
            messages.error(
                "Este servicio se encuentra cancelado"
            )
            return HttpResponseRedirect(
                reverse_lazy("servicios:lista_servicios_secretario")
            )
        if Servicio.objects.filter(
            Q(id_servicio=servicio) &
            (
                Q(pagado=True) |
                Q(completado=True)
            )
        ).exists():
            messages.error(
                "Este servicio ya está completado y/o pagado totalmente"
            )
            return HttpResponseRedirect(
                reverse_lazy("servicios:lista_servicios_secretario")
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
        contexto["servicio"] = Servicio.objects.get(
            Q(id_servicio=servicio)
        )
        return render(
            request,
            self.template_name,
            contexto
        )

    def post(self: Self, request: HttpRequest, servicio: int) -> HttpResponse:
        if not Servicio.objects.filter(
            Q(id_servicio=servicio)
        ).exists():
            messages.error(
                "No existe el servicio"
            )
            return HttpResponseRedirect(
                reverse_lazy("servicios:lista_servicios_secretario")
            )
        if Servicio.objects.filter(
            Q(id_servicio=servicio) &
            Q(cancelacion_servicio__isnull=False)
        ).exists():
            messages.error(
                "Este servicio se encuentra cancelado"
            )
            return HttpResponseRedirect(
                reverse_lazy("servicios:lista_servicios_secretario")
            )
        if Servicio.objects.filter(
            Q(id_servicio=servicio) &
            (
                Q(pagado=True) |
                Q(completado=True)
            )
        ).exists():
            messages.error(
                "Este servicio ya está completado y/o pagado totalmente"
            )
            return HttpResponseRedirect(
                reverse_lazy("servicios:lista_servicios_secretario")
            )
        servicio_a_cancelar: Servicio = \
            Servicio.objects.get(id_servicio=servicio)
        servicio_a_cancelar.cancelacion_servicio = TransactionNow()
        servicio_a_cancelar.causa_cancelacion_servicio = request.POST.get(
            "causa"
        )
        with transaction.atomic():
            servicio_a_cancelar.save()
        messages.error(
            request,
            "Ha cancelado el servicio definitivamente"
        )
        return HttpResponseRedirect(
            reverse_lazy("servicios:lista_servicios_secretario")
        )
