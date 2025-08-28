from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Permission
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.paginator import Page, Paginator
from django.db.models import (
    Case, CharField, DecimalField, F, Max, Min, Q, Value, When
)
from django.db.models.functions import Cast, Concat
from django.db.models.query import QuerySet
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from decimal import Decimal
from typing import Any, Dict, Optional, Self
from unidecode import unidecode

from ..models import Progreso, Servicio

from solicitudes.models import (
    ComitenteSolicitud,
    ResponsableSolicitud
)

from firmas.models import FirmaOrden, OrdenServicio

from cuentas.models import (
    Comitente,
    ResponsableTecnico,
    Secretario
)

from gesservorconv.mixins import (
    MixinAccesoRequerido,
    MixinPermisoRequerido
)
from gesservorconv.views import HtmxHttpRequest


class VistaListaServiciosSecretario(
    MixinAccesoRequerido,
    MixinPermisoRequerido,
    UserPassesTestMixin,
    TemplateView
):
    paginate_by: int = 10
    template_name: str = "servicios/listar_servicios_secretario.html"
    permission_required: QuerySet[Permission] = Permission.objects.filter(
        codename=f'view_{Servicio.__name__.lower()}'
    )

    def test_func(self: Self) -> bool:
        return Secretario.objects.filter(
            usuario_secretario=self.request.user
        ).exists()

    def handle_no_permission(self: Self) -> HttpResponse:
        if self.request.user.is_anonymous:
            messages.warning(
                self.request,
                "La sesión ha caducado"
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
        if self.has_permission():
            messages.error(
                self.request,
                "Usted no está a cargo de la Secretaría"
                " de Extensión y Vinculación Tecnológica."
            )
        else:
            messages.error(
                self.request,
                "Usted no tiene los permisos para acceder"
                " a esta página."
            )
        return HttpResponseRedirect(
            reverse_lazy('cuentas:perfil')
        )

    def get_queryset(self: Self) -> QuerySet[Servicio]:
        '''
        Se filtra las órdenes que pertenezcan al responsable técnico
        '''
        servicios: QuerySet[Servicio] = \
            Servicio.objects.annotate(
                tiempo_creacion=Case(
                    When(
                        Q(orden_servicio__isnull=False),
                        then=Min(
                            "orden_servicio__solicitud_servicio__comitentesolicitud__tiempo_decision",
                            filter=Q(
                                orden_servicio__solicitud_servicio__comitentesolicitud__tiempo_decision__isnull=False
                            )
                        )
                    ),
                    default=Min(
                        "convenio__solicitud_servicio__comitentesolicitud__tiempo_decision",
                        filter=Q(
                            convenio__solicitud_servicio__comitentesolicitud__tiempo_decision__isnull=False
                        )
                    )
                )
            ).annotate(
                porcentaje=Max(
                    "progreso__porcentaje_progreso",
                    default=Decimal("0.00"),
                    output_field=DecimalField(
                        max_digits=5,
                        decimal_places=2
                    )
                )
            ).annotate(
                comitentes_en_solicitud=ArrayAgg(
                    Case(
                        When(
                            Q(orden_servicio__isnull=False) &
                            Q(
                                orden_servicio__solicitud_servicio__comitentesolicitud__cuit_organizacion_comitente__isnull=True
                            ),
                            then=Concat(
                                F("orden_servicio__solicitud_servicio__comitentesolicitud__comitente__usuario_comitente__last_name"),
                                Value(", "),
                                F("orden_servicio__solicitud_servicio__comitentesolicitud__comitente__usuario_comitente__first_name"),
                                Value(". CUIL: "),
                                Cast(
                                    "orden_servicio__solicitud_servicio__comitentesolicitud__comitente__cuil_comitente",
                                    output_field=CharField()
                                ),
                                Value(" (persona física)")
                            )
                        ),
                        When(
                            Q(orden_servicio__isnull=False) &
                            Q(
                                orden_servicio__solicitud_servicio__comitentesolicitud__cuit_organizacion_comitente__isnull=False
                            ),
                            then=Concat(
                                F("orden_servicio__solicitud_servicio__comitentesolicitud__comitente__usuario_comitente__last_name"),
                                Value(", "),
                                F("orden_servicio__solicitud_servicio__comitentesolicitud__comitente__usuario_comitente__first_name"),
                                Value(". "),
                                F("orden_servicio__solicitud_servicio__comitentesolicitud__puesto_organizacion_comitente"),
                                Value(" - "),
                                F("orden_servicio__solicitud_servicio__comitentesolicitud__razon_social_comitente"),
                                Value(". CUIT: "),
                                Cast(
                                    "orden_servicio__solicitud_servicio__comitentesolicitud__cuit_organizacion_comitente",
                                    output_field=CharField()
                                )
                            )
                        ),
                        When(
                            Q(convenio__isnull=False) &
                            Q(
                                convenio__solicitud_servicio__comitentesolicitud__cuit_organizacion_comitente__isnull=True
                            ),
                            then=Concat(
                                F("convenio__solicitud_servicio__comitentesolicitud__comitente__usuario_comitente__last_name"),
                                Value(", "),
                                F("convenio__solicitud_servicio__comitentesolicitud__comitente__usuario_comitente__first_name"),
                                Value(". CUIL: "),
                                Cast(
                                    "convenio__solicitud_servicio__comitentesolicitud__comitente__cuil_comitente",
                                    output_field=CharField()
                                ),
                                Value(" (persona física)")
                            )
                        ),
                        When(
                            Q(convenio__isnull=False) &
                            Q(
                                convenio__solicitud_servicio__comitentesolicitud__cuit_organizacion_comitente__isnull=False
                            ),
                            then=Concat(
                                F("convenio__solicitud_servicio__comitentesolicitud__comitente__usuario_comitente__last_name"),
                                Value(", "),
                                F("convenio__solicitud_servicio__comitentesolicitud__comitente__usuario_comitente__first_name"),
                                Value(". "),
                                F("convenio__solicitud_servicio__comitentesolicitud__puesto_organizacion_comitente"),
                                Value(" - "),
                                F("convenio__solicitud_servicio__comitentesolicitud__razon_social_comitente"),
                                Value(". CUIT: "),
                                Cast(
                                    "convenio__solicitud_servicio__comitentesolicitud__cuit_organizacion_comitente",
                                    output_field=CharField()
                                )
                            )
                        ),
                        default=None
                    ),
                    distinct=True,
                    default=Value([])
                )
            ).annotate(
                responsables_en_solicitud=ArrayAgg(
                    Case(
                        When(
                            Q(orden_servicio__isnull=False) &
                            ~Q(
                                orden_servicio__in=ResponsableSolicitud.objects.filter(
                                    (
                                        Q(
                                            tiempo_decision_responsable__isnull=True
                                        ) &
                                        (
                                            Q(
                                                tiempo_decision_comitente__isnull=True
                                            ) |
                                            Q(
                                                aceptacion_comitente=True
                                            )
                                        )
                                    ) |
                                    (
                                        Q(
                                            tiempo_decision_comitente__isnull=True
                                        ) &
                                        (
                                            Q(
                                                tiempo_decision_responsable__isnull=True
                                            ) |
                                            Q(
                                                aceptacion_responsable=True
                                            )
                                        )
                                    )
                                ).values_list(
                                    "solicitud_servicio", flat=True
                                )
                            ),
                            then=Concat(
                                F("orden_servicio__solicitud_servicio__responsablesolicitud__responsable_tecnico__usuario_responsable__last_name"),
                                Value(", "),
                                F("orden_servicio__solicitud_servicio__responsablesolicitud__responsable_tecnico__usuario_responsable__first_name"),
                                Value(". CUIL: "),
                                Cast(
                                    "orden_servicio__solicitud_servicio__responsablesolicitud__responsable_tecnico__cuil_responsable",
                                    output_field=CharField()
                                ),
                                Value(" (persona física)")
                            )
                        ),
                        When(
                            Q(orden_servicio__isnull=False) &
                            ~Q(
                                orden_servicio__in=ResponsableSolicitud.objects.filter(
                                    (
                                        Q(
                                            tiempo_decision_responsable__isnull=True
                                        ) &
                                        (
                                            Q(
                                                tiempo_decision_comitente__isnull=True
                                            ) |
                                            Q(
                                                aceptacion_comitente=True
                                            )
                                        )
                                    ) |
                                    (
                                        Q(
                                            tiempo_decision_comitente__isnull=True
                                        ) &
                                        (
                                            Q(
                                                tiempo_decision_responsable__isnull=True
                                            ) |
                                            Q(
                                                aceptacion_responsable=True
                                            )
                                        )
                                    )
                                ).values_list(
                                    "solicitud_servicio", flat=True
                                )
                            ),
                            then=Concat(
                                F("orden_servicio__solicitud_servicio__responsablesolicitud__responsable_tecnico__usuario_responsable__last_name"),
                                Value(", "),
                                F("orden_servicio__solicitud_servicio__responsablesolicitud__responsable_tecnico__usuario_responsable__first_name"),
                                Value(". "),
                                F("orden_servicio__solicitud_servicio__responsablesolicitud__puesto_organizacion_responsable"),
                                Value(" - "),
                                F("orden_servicio__solicitud_servicio__responsablesolicitud__razon_social_responsable"),
                                Value(". CUIT: "),
                                Cast(
                                    "orden_servicio__solicitud_servicio__responsablesolicitud__cuit_organizacion_responsable",
                                    output_field=CharField()
                                )
                            )
                        ),
                        When(
                            Q(convenio__isnull=False) &
                            ~Q(
                                convenio__in=ResponsableSolicitud.objects.filter(
                                    (
                                        Q(
                                            tiempo_decision_responsable__isnull=True
                                        ) &
                                        (
                                            Q(
                                                tiempo_decision_comitente__isnull=True
                                            ) |
                                            Q(
                                                aceptacion_comitente=True
                                            )
                                        )
                                    ) |
                                    (
                                        Q(
                                            tiempo_decision_comitente__isnull=True
                                        ) &
                                        (
                                            Q(
                                                tiempo_decision_responsable__isnull=True
                                            ) |
                                            Q(
                                                aceptacion_responsable=True
                                            )
                                        )
                                    )
                                ).values_list(
                                    "solicitud_servicio", flat=True
                                )
                            ),
                            then=Concat(
                                F("convenio__solicitud_servicio__responsablesolicitud__responsable_tecnico__usuario_responsable__last_name"),
                                Value(", "),
                                F("convenio__solicitud_servicio__responsablesolicitud__responsable_tecnico__usuario_responsable__first_name"),
                                Value(". CUIL: "),
                                Cast(
                                    "convenio__solicitud_servicio__responsablesolicitud__responsable_tecnico__cuil_responsable",
                                    output_field=CharField()
                                ),
                                Value(" (persona física)")
                            )
                        ),
                        When(
                            Q(convenio__isnull=False) &
                            ~Q(
                                convenio__in=ResponsableSolicitud.objects.filter(
                                    (
                                        Q(
                                            tiempo_decision_responsable__isnull=True
                                        ) &
                                        (
                                            Q(
                                                tiempo_decision_comitente__isnull=True
                                            ) |
                                            Q(
                                                aceptacion_comitente=True
                                            )
                                        )
                                    ) |
                                    (
                                        Q(
                                            tiempo_decision_comitente__isnull=True
                                        ) &
                                        (
                                            Q(
                                                tiempo_decision_responsable__isnull=True
                                            ) |
                                            Q(
                                                aceptacion_responsable=True
                                            )
                                        )
                                    )
                                ).values_list(
                                    "solicitud_servicio", flat=True
                                )
                            ),
                            then=Concat(
                                F("convenio__solicitud_servicio__responsablesolicitud__responsable_tecnico__usuario_responsable__last_name"),
                                Value(", "),
                                F("convenio__solicitud_servicio__responsablesolicitud__responsable_tecnico__usuario_responsable__first_name"),
                                Value(". "),
                                F("convenio__solicitud_servicio__responsablesolicitud__puesto_organizacion_responsable"),
                                Value(" - "),
                                F("convenio__solicitud_servicio__responsablesolicitud__razon_social_responsable"),
                                Value(". CUIT: "),
                                Cast(
                                    "convenio__solicitud_servicio__responsablesolicitud__cuit_organizacion_responsable",
                                    output_field=CharField()
                                )
                            )
                        ),
                        default=None
                    ),
                    distinct=True,
                    default=Value([])
                )
            ).order_by(
                "id_servicio"
            )
        return servicios

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
        servicios: QuerySet[Servicio] = self.get_queryset()
        paginador_curso: Paginator = Paginator(
            servicios.filter(
                (Q(completado=False) | Q(pagado=False))
                & Q(cancelacion_servicio__isnull=True)
            ),
            self.paginate_by
        )
        objeto_pagina_curso: Page = paginador_curso.get_page(None)
        contexto["pagina_curso"] = objeto_pagina_curso
        paginador_finalizado: Paginator = Paginator(
            servicios.filter(
                Q(completado=True) & Q(pagado=True) &
                Q(cancelacion_servicio__isnull=True)
            ),
            self.paginate_by
        )
        objeto_pagina_finalizado: Page = paginador_finalizado.get_page(None)
        contexto["pagina_finalizado"] = objeto_pagina_finalizado
        paginador_cancelado: Paginator = Paginator(
            servicios.filter(
                Q(cancelacion_servicio__isnull=False)
            ),
            self.paginate_by
        )
        objeto_pagina_cancelado: Page = paginador_cancelado.get_page(None)
        contexto["pagina_cancelado"] = objeto_pagina_cancelado
        return contexto

    def get(self: Self, request: HtmxHttpRequest) -> HttpResponse:
        if request.htmx:
            busqueda_nombre: Optional[str] = self.request.GET.get(
                "buscar_nombre"
            )
            si_nombre: bool = (busqueda_nombre is not None)
            nombre: str = ""
            if si_nombre:
                nombre = str(busqueda_nombre)
            elementos_por_pagina: Optional[str] = self.request.GET.get(
                "por_pagina"
            )
            si_por_pagina: bool = (elementos_por_pagina is not None)
            por_pagina: int = self.paginate_by
            if (
                si_por_pagina and
                elementos_por_pagina != "" and
                elementos_por_pagina.isdigit()
            ):
                por_pagina = int(elementos_por_pagina)
            servicios: QuerySet[OrdenServicio] = (
                self.get_queryset() if (
                    si_por_pagina and
                    elementos_por_pagina != "" and
                    elementos_por_pagina.isdigit() and
                    por_pagina != 0
                ) else OrdenServicio.objects.none()
            )
            if si_nombre and nombre.strip() != "":
                cadenas: list[str] = unidecode(nombre.strip()).split()
                busqueda: Q = Q(
                    solicitud_servicio__nombre_solicitud__unaccent__icontains=cadenas[0]
                )
                for cadena in cadenas[1:]:
                    busqueda &= Q(
                        solicitud_servicio__nombre_solicitud__unaccent__icontains=cadena
                    )
                servicios = servicios.filter(busqueda)
            tipo: Optional[str] = request.GET.get("tipo")
            if not tipo or tipo == "curso":
                servicios_curso: QuerySet[Servicio] = servicios.filter(
                    (Q(completado=False) | Q(pagado=False)) &
                    Q(cancelacion_servicio__isnull=True)
                )
                paginador_curso: Paginator = Paginator(
                    servicios_curso,
                    por_pagina if por_pagina != 0 else self.paginate_by
                )
                '''
                Si no existe "pagina" como parámetro del método
                GET, objeto_pagina será 1 por defecto
                '''
                objeto_pagina_curso: Page = paginador_curso.get_page(
                    request.GET.get("pagina")
                )
                if tipo == "curso":
                    return render(
                        request,
                        "parciales/_lista_servicios_en_curso_responsable.html",
                        {"pagina_curso": objeto_pagina_curso}
                    )
            if not tipo or tipo == "finalizado":
                servicios_finalizado: QuerySet[Servicio] = servicios.filter(
                    Q(completado=True) & Q(pagado=True) &
                    Q(cancelacion_servicio__isnull=True)
                )
                paginador_finalizado: Paginator = Paginator(
                    servicios_finalizado,
                    por_pagina if por_pagina != 0 else self.paginate_by
                )
                '''
                Si no existe "pagina" como parámetro del método
                GET, objeto_pagina será 1 por defecto
                '''
                objeto_pagina_finalizado: Page = paginador_finalizado.get_page(
                    request.GET.get("pagina")
                )
                if tipo == "finalizado":
                    return render(
                        request,
                        "parciales/_lista_servicios_finalizados_responsable.html",
                        {"pagina_finalizado": objeto_pagina_finalizado}
                    )
            if not tipo or tipo == "cancelado":
                servicios_cancelado: QuerySet[Servicio] = servicios.filter(
                    Q(cancelacion_servicio__isnull=False)
                )
                paginador_cancelado: Paginator = Paginator(
                    servicios_cancelado,
                    por_pagina if por_pagina != 0 else self.paginate_by
                )
                '''
                Si no existe "pagina" como parámetro del método
                GET, objeto_pagina será 1 por defecto
                '''
                objeto_pagina_cancelado: Page = paginador_cancelado.get_page(
                    request.GET.get("pagina")
                )
                if tipo == "cancelado":
                    return render(
                        request,
                        "parciales/_lista_servicios_cancelados_responsable.html",
                        {"pagina_cancelado": objeto_pagina_cancelado}
                    )
            return render(
                request,
                "parciales/_lista_servicios_responsable.html",
                {
                    "pagina_curso": objeto_pagina_curso,
                    "pagina_finalizado": objeto_pagina_finalizado,
                    "pagina_cancelado": objeto_pagina_cancelado
                }
            )
        return super(
            VistaListaServiciosSecretario,
            self
        ).get(request)
