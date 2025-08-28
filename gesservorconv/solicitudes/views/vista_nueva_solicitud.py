from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.postgres.functions import TransactionNow
from django.db import transaction
from django.db.models import Q
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from typing import Any, Dict, Optional, Self

from ..models import (
    Categoria,
    Facultad,
    SolicitudServicio,
    ComitenteSolicitud
)

from cuentas.models import (
    Notificacion,
    Comitente,
    ResponsableTecnico,
    Secretario
)

from gesservorconv.mixins import MixinAccesoRequerido


class VistaNuevaSolicitud(
    MixinAccesoRequerido,
    UserPassesTestMixin,
    TemplateView
):
    template_name: str = "solicitudes/agregar_solicitud.html"

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
        if (
            "convenio" in dict(
                self.request.GET.lists()
            )
        ):
            contexto["convenio"] = True
        contexto["usuario_comitente"] = Comitente.objects.get(
            usuario_comitente=self.request.user
        )
        contexto["comitentes_solicitud"] = Comitente.objects.exclude(
            usuario_comitente=self.request.user
        )
        contexto["facultades"] = Facultad.objects.all()
        return contexto

    def get(
        self: Self,
        request: HttpRequest
    ) -> HttpResponse:
        notificaciones: QuerySet[Notificacion] = Notificacion.objects.filter(
            Q(usuario_notificacion=request.user) &
            Q(enlace_notificacion=request.build_absolute_uri()) &
            Q(lectura_notificacion__isnull=True)
        )
        notificaciones.update(
            lectura_notificacion=TransactionNow()
        )
        return super(
            VistaNuevaSolicitud,
            self
        ).get(request)

    def post(
        self: Self,
        request: HttpRequest
    ) -> HttpResponse:
        organizacion_comitente: str = request.POST.get(
            "organizacion_comitente", ""
        )
        organizacion: int = int(organizacion_comitente)
        comitentes: list[str] = request.POST.getlist(
            "comitentes",
            []
        )
        nombre_solicitud: str = request.POST.get(
            "nombre_solicitud", ""
        ).strip()
        descripcion_solicitud: str = request.POST.get(
            "descripcion_solicitud", ""
        ).strip()
        por_convenio: Optional[str] = request.POST.get(
            "por_convenio"
        )
        categorias: list[str] = request.POST.getlist(
            "categorias",
            []
        )
        with transaction.atomic():
            nueva_solicitud: SolicitudServicio = SolicitudServicio(
                nombre_solicitud=nombre_solicitud,
                descripcion_solicitud=descripcion_solicitud,
                por_convenio=True if por_convenio else False,
                responsables_autoadjudicados=False,
                cancelacion_solicitud=None,
                solicitud_suspendida=None if comitentes else False
            )
            nueva_solicitud.save()
            for categoria in categorias:
                nueva_solicitud.categorias_solicitud.add(
                    Categoria.objects.get(pk=int(categoria))
                )
            comitente: Comitente = Comitente.objects.get(
                usuario_comitente=request.user
            )
            comitente_solicitud: ComitenteSolicitud = ComitenteSolicitud(
                comitente=comitente,
                solicitud_servicio=nueva_solicitud,
                razon_social_comitente=(
                    comitente.razones_sociales_comitente[
                        organizacion-1
                    ] if organizacion > 0 else None
                ),
                cuit_organizacion_comitente=(
                    comitente.cuit_organizaciones_comitente[
                        organizacion-1
                    ] if organizacion > 0 else None
                ),
                puesto_organizacion_comitente=(
                    comitente.puestos_organizaciones_comitente[
                        organizacion-1
                    ] if organizacion > 0 else None
                ),
                tiempo_decision=TransactionNow(),
                aceptacion=True
            )
            comitente_solicitud.save()
            partes: tuple[str, str, str]
            indice: int
            for comitente_asociado in comitentes:
                partes = comitente_asociado.partition(":")
                comitente = Comitente.objects.get(
                    cuil_comitente=partes[0]
                )
                indice = int(partes[2])
                comitente_solicitud = ComitenteSolicitud(
                    comitente=comitente,
                    solicitud_servicio=nueva_solicitud,
                    razon_social_comitente=(
                        comitente.razones_sociales_comitente[
                            indice-1
                        ] if indice > 0 else None
                    ),
                    cuit_organizacion_comitente=(
                        comitente.cuit_organizaciones_comitente[
                            indice-1
                        ] if indice > 0 else None
                    ),
                    puesto_organizacion_comitente=(
                        comitente.puestos_organizaciones_comitente[
                            indice-1
                        ] if indice > 0 else None
                    ),
                    tiempo_decision=None,
                    aceptacion=False
                )
                comitente_solicitud.save()
        messages.success(
            request,
            "Ha agregado una nueva solicitud de servicio correctamente"
        )
        return HttpResponseRedirect(
            reverse_lazy("solicitudes:lista_solicitudes_comitente")
        )
