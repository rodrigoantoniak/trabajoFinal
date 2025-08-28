from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Permission
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.functions import TransactionNow
from django.core.paginator import Page, Paginator
from django.db.models import (
    BooleanField, Case, CharField, F, Min, Q, Value, When
)
from django.db.models.functions import Cast, Concat
from django.db.models.query import QuerySet
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from typing import Any, Dict, Optional, Self
from unidecode import unidecode

from ..models import (
    SolicitudServicio,
    ComitenteSolicitud,
    ResponsableSolicitud,
    PropuestaCompromisos,
    DecisionComitentePropuesta
)

from firmas.models import Convenio, OrdenServicio

from cuentas.models import (
    Notificacion,
    Comitente,
    ResponsableTecnico,
    Secretario
)

from gesservorconv.mixins import (
    MixinAccesoRequerido,
    MixinPermisoRequerido
)
from gesservorconv.views import HtmxHttpRequest


class VistaListaSolicitudesComitente(
    MixinAccesoRequerido,
    MixinPermisoRequerido,
    UserPassesTestMixin,
    TemplateView
):
    paginate_by: int = 10
    template_name: str = "solicitudes/listar_solicitudes_comitente.html"
    permission_required: QuerySet[Permission] = Permission.objects.filter(
        codename=f'view_{SolicitudServicio.__name__.lower()}'
    )

    def test_func(self: Self) -> bool:
        return Comitente.objects.filter(
            Q(usuario_comitente=self.request.user)
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
                "Usted no es un Comitente."
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

    def get_queryset(self: Self) -> QuerySet[SolicitudServicio]:
        '''
        Se excluye todas las solicitudes que cuenten con una orden
        y se filtra los que pertenezcan al comitente
        '''
        solicitudes_servicio: QuerySet[SolicitudServicio] = \
            SolicitudServicio.objects.exclude(
                Q(
                    pk__in=OrdenServicio.objects.values_list(
                        "solicitud_servicio__id_solicitud", flat=True
                    )
                ) |
                Q(
                    pk__in=Convenio.objects.values_list(
                        "solicitud_servicio__id_solicitud", flat=True
                    )
                )
            ).filter(
                pk__in=ComitenteSolicitud.objects.filter(
                    comitente__usuario_comitente=self.request.user
                ).values_list(
                    "solicitud_servicio__id_solicitud", flat=True
                )
            ).annotate(
                tiempo_creacion=Min(
                    "comitentesolicitud__tiempo_decision",
                    filter=Q(
                        comitentesolicitud__tiempo_decision__isnull=False
                    )
                )
            ).annotate(
                debe_decidir_comitente=Case(
                    When(
                        Q(
                            pk__in=ComitenteSolicitud.objects.filter(
                                Q(
                                    comitente__usuario_comitente=self.request.user
                                ) &
                                Q(
                                    tiempo_decision__isnull=True
                                )
                            ).values_list(
                                "solicitud_servicio", flat=True
                            )
                        ),
                        then=Value(True)
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            ).annotate(
                debe_responsables=Case(
                    When(
                        ~Q(
                            pk__in=ComitenteSolicitud.objects.filter(
                                aceptacion=False
                            ).values_list(
                                "solicitud_servicio", flat=True
                            )
                        ) &
                        ~Q(
                            pk__in=ResponsableSolicitud.objects.values_list(
                                "solicitud_servicio", flat=True
                            )
                        ) &
                        Q(responsables_autoadjudicados=False) &
                        Q(autoadjudicacion_abierta__isnull=False) &
                        Q(autoadjudicacion_abierta=False) &
                        Q(solicitud_suspendida__isnull=False) &
                        Q(solicitud_suspendida=False),
                        then=Value(True)
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            ).annotate(
                debe_decidir_responsable=Case(
                    When(
                        pk__in=ResponsableSolicitud.objects.filter(
                            Q(
                                aceptacion_responsable=True
                            ) &
                            Q(
                                tiempo_decision_comitente__isnull=True
                            )
                        ).values_list(
                            "solicitud_servicio", flat=True
                        ),
                        then=Value(True)
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            ).annotate(
                debe_revisar_propuesta=Case(
                    When(
                        Q(
                            pk__in=DecisionComitentePropuesta.objects.filter(
                                propuesta_compromisos__es_valida_propuesta=True,
                                comitente_solicitud__comitente__usuario_comitente=self.request.user,
                                tiempo_decision_propuesta__isnull=True
                            ).values_list(
                                "propuesta_compromisos__solicitud_servicio_propuesta", flat=True
                            )
                        ),
                        then=Value(True)
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            ).annotate(
                comitentes_en_solicitud=ArrayAgg(
                    Case(
                        When(
                            Q(
                                comitentesolicitud__cuit_organizacion_comitente__isnull=True
                            ) & (
                                Q(
                                    responsables_autoadjudicados=True
                                ) |
                                Q(
                                    pk__in=ResponsableSolicitud.objects.values_list(
                                        "solicitud_servicio", flat=True
                                    )
                                )
                            ),
                            then=Concat(
                                F("comitentesolicitud__comitente__usuario_comitente__last_name"),
                                Value(", "),
                                F("comitentesolicitud__comitente__usuario_comitente__first_name"),
                                Value(". CUIL: "),
                                Cast(
                                    "comitentesolicitud__comitente__cuil_comitente",
                                    output_field=CharField()
                                ),
                                Value(" (persona física)")
                            )
                        ),
                        When(
                            Q(
                                comitentesolicitud__cuit_organizacion_comitente__isnull=False
                            ) & (
                                Q(
                                    responsables_autoadjudicados=True
                                ) |
                                Q(
                                    pk__in=ResponsableSolicitud.objects.values_list(
                                        "solicitud_servicio", flat=True
                                    )
                                )
                            ),
                            then=Concat(
                                F("comitentesolicitud__comitente__usuario_comitente__last_name"),
                                Value(", "),
                                F("comitentesolicitud__comitente__usuario_comitente__first_name"),
                                Value(". "),
                                F("comitentesolicitud__puesto_organizacion_comitente"),
                                Value(" - "),
                                F("comitentesolicitud__razon_social_comitente"),
                                Value(". CUIT: "),
                                Cast(
                                    "comitentesolicitud__cuit_organizacion_comitente",
                                    output_field=CharField()
                                )
                            )
                        ),
                        When(
                            Q(
                                comitentesolicitud__cuit_organizacion_comitente__isnull=True
                            ) & Q(
                                comitentesolicitud__aceptacion=True
                            ),
                            then=Concat(
                                Value("Aceptó: "),
                                F("comitentesolicitud__comitente__usuario_comitente__last_name"),
                                Value(", "),
                                F("comitentesolicitud__comitente__usuario_comitente__first_name"),
                                Value(". CUIL: "),
                                Cast(
                                    "comitentesolicitud__comitente__cuil_comitente",
                                    output_field=CharField()
                                ),
                                Value(" (persona física)")
                            )
                        ),
                        When(
                            Q(
                                comitentesolicitud__cuit_organizacion_comitente__isnull=False
                            ) & Q(
                                comitentesolicitud__aceptacion=True
                            ),
                            then=Concat(
                                Value("Aceptó: "),
                                F("comitentesolicitud__comitente__usuario_comitente__last_name"),
                                Value(", "),
                                F("comitentesolicitud__comitente__usuario_comitente__first_name"),
                                Value(". "),
                                F("comitentesolicitud__puesto_organizacion_comitente"),
                                Value(" - "),
                                F("comitentesolicitud__razon_social_comitente"),
                                Value(". CUIT: "),
                                Cast(
                                    "comitentesolicitud__cuit_organizacion_comitente",
                                    output_field=CharField()
                                )
                            )
                        ),
                        When(
                            Q(
                                comitentesolicitud__cuit_organizacion_comitente__isnull=True
                            ) & Q(
                                comitentesolicitud__tiempo_decision__isnull=True
                            ),
                            then=Concat(
                                Value("No decidió: "),
                                F("comitentesolicitud__comitente__usuario_comitente__last_name"),
                                Value(", "),
                                F("comitentesolicitud__comitente__usuario_comitente__first_name"),
                                Value(". CUIL: "),
                                Cast(
                                    "comitentesolicitud__comitente__cuil_comitente",
                                    output_field=CharField()
                                ),
                                Value(" (persona física)")
                            )
                        ),
                        When(
                            Q(
                                comitentesolicitud__cuit_organizacion_comitente__isnull=False
                            ) & Q(
                                comitentesolicitud__tiempo_decision__isnull=True
                            ),
                            then=Concat(
                                Value("No decidió: "),
                                F("comitentesolicitud__comitente__usuario_comitente__last_name"),
                                Value(", "),
                                F("comitentesolicitud__comitente__usuario_comitente__first_name"),
                                Value(". "),
                                F("comitentesolicitud__puesto_organizacion_comitente"),
                                Value(" - "),
                                F("comitentesolicitud__razon_social_comitente"),
                                Value(". CUIT: "),
                                Cast(
                                    "comitentesolicitud__cuit_organizacion_comitente",
                                    output_field=CharField()
                                )
                            )
                        ),
                        When(
                            Q(
                                comitentesolicitud__cuit_organizacion_comitente__isnull=True
                            ) & Q(
                                comitentesolicitud__tiempo_decision__isnull=False
                            ) & Q(
                                comitentesolicitud__aceptacion=False
                            ),
                            then=Concat(
                                Value("Rechazó: "),
                                F("comitentesolicitud__comitente__usuario_comitente__last_name"),
                                Value(", "),
                                F("comitentesolicitud__comitente__usuario_comitente__first_name"),
                                Value(". CUIL: "),
                                Cast(
                                    "comitentesolicitud__comitente__cuil_comitente",
                                    output_field=CharField()
                                ),
                                Value(" (persona física)")
                            )
                        ),
                        When(
                            Q(
                                comitentesolicitud__cuit_organizacion_comitente__isnull=False
                            ) & Q(
                                comitentesolicitud__tiempo_decision__isnull=False
                            ) & Q(
                                comitentesolicitud__aceptacion=False
                            ),
                            then=Concat(
                                Value("Rechazó: "),
                                F("comitentesolicitud__comitente__usuario_comitente__last_name"),
                                Value(", "),
                                F("comitentesolicitud__comitente__usuario_comitente__first_name"),
                                Value(". "),
                                F("comitentesolicitud__puesto_organizacion_comitente"),
                                Value(" - "),
                                F("comitentesolicitud__razon_social_comitente"),
                                Value(". CUIT: "),
                                Cast(
                                    "comitentesolicitud__cuit_organizacion_comitente",
                                    output_field=CharField()
                                )
                            )
                        )
                    ),
                    distinct=True,
                    default=Value([])
                )
            ).annotate(
                responsables_en_solicitud=Case(
                    When(
                        Q(
                            pk__in=ResponsableSolicitud.objects.filter(
                                (
                                    Q(
                                        aceptacion_responsable=True
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
                                        aceptacion_comitente=True
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
                        then=ArrayAgg(
                            Case(
                                When(
                                    Q(autoadjudicacion_abierta__isnull=False) &
                                    Q(autoadjudicacion_abierta=False) &
                                    ~Q(
                                        pk__in=ResponsableSolicitud.objects.filter(
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
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__last_name"),
                                        Value(", "),
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__first_name"),
                                        Value(". CUIL: "),
                                        Cast(
                                            "responsablesolicitud__responsable_tecnico__cuil_responsable",
                                            output_field=CharField()
                                        ),
                                        Value(" (persona física)")
                                    )
                                ),
                                When(
                                    Q(autoadjudicacion_abierta__isnull=False) &
                                    Q(autoadjudicacion_abierta=False) &
                                    ~Q(
                                        pk__in=ResponsableSolicitud.objects.filter(
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
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__last_name"),
                                        Value(", "),
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__first_name"),
                                        Value(". "),
                                        F("responsablesolicitud__puesto_organizacion_responsable"),
                                        Value(" - "),
                                        F("responsablesolicitud__razon_social_responsable"),
                                        Value(". CUIT: "),
                                        Cast(
                                            "responsablesolicitud__cuit_organizacion_responsable",
                                            output_field=CharField()
                                        )
                                    )
                                ),
                                When(
                                    Q(
                                        responsablesolicitud__cuit_organizacion_responsable__isnull=True
                                    ) & Q(
                                        responsablesolicitud__aceptacion_comitente=True
                                    ) & Q(
                                        responsablesolicitud__aceptacion_responsable=True
                                    ),
                                    then=Concat(
                                        Value("Aceptado: "),
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__last_name"),
                                        Value(", "),
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__first_name"),
                                        Value(". CUIL: "),
                                        Cast(
                                            "responsablesolicitud__responsable_tecnico__cuil_responsable",
                                            output_field=CharField()
                                        ),
                                        Value(" (persona física)")
                                    )
                                ),
                                When(
                                    Q(
                                        responsablesolicitud__cuit_organizacion_responsable__isnull=False
                                    ) & Q(
                                        responsablesolicitud__aceptacion_comitente=True
                                    ) & Q(
                                        responsablesolicitud__aceptacion_responsable=True
                                    ),
                                    then=Concat(
                                        Value("Aceptado: "),
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__last_name"),
                                        Value(", "),
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__first_name"),
                                        Value(". "),
                                        F("responsablesolicitud__puesto_organizacion_responsable"),
                                        Value(" - "),
                                        F("responsablesolicitud__razon_social_responsable"),
                                        Value(". CUIT: "),
                                        Cast(
                                            "responsablesolicitud__cuit_organizacion_responsable",
                                            output_field=CharField()
                                        )
                                    )
                                ),
                                When(
                                    Q(
                                        responsablesolicitud__cuit_organizacion_responsable__isnull=True
                                    ) & Q(
                                        responsablesolicitud__aceptacion_comitente=True
                                    ) & Q(
                                        responsablesolicitud__tiempo_decision_responsable__isnull=True
                                    ),
                                    then=Concat(
                                        Value("Falta aceptar: "),
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__last_name"),
                                        Value(", "),
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__first_name"),
                                        Value(". CUIL: "),
                                        Cast(
                                            "responsablesolicitud__responsable_tecnico__cuil_responsable",
                                            output_field=CharField()
                                        ),
                                        Value(" (persona física)")
                                    )
                                ),
                                When(
                                    Q(
                                        responsablesolicitud__cuit_organizacion_responsable__isnull=False
                                    ) & Q(
                                        responsablesolicitud__aceptacion_comitente=True
                                    ) & Q(
                                        responsablesolicitud__tiempo_decision_responsable__isnull=True
                                    ),
                                    then=Concat(
                                        Value("Falta aceptar: "),
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__last_name"),
                                        Value(", "),
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__first_name"),
                                        Value(". "),
                                        F("responsablesolicitud__puesto_organizacion_responsable"),
                                        Value(" - "),
                                        F("responsablesolicitud__razon_social_responsable"),
                                        Value(". CUIT: "),
                                        Cast(
                                            "responsablesolicitud__cuit_organizacion_responsable",
                                            output_field=CharField()
                                        )
                                    )
                                ),
                                When(
                                    Q(
                                        responsablesolicitud__cuit_organizacion_responsable__isnull=True
                                    ) & Q(
                                        responsablesolicitud__aceptacion_responsable=True
                                    ) & Q(
                                        responsablesolicitud__tiempo_decision_comitente__isnull=True
                                    ),
                                    then=Concat(
                                        Value("Falta ser aceptado: "),
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__last_name"),
                                        Value(", "),
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__first_name"),
                                        Value(". CUIL: "),
                                        Cast(
                                            "responsablesolicitud__responsable_tecnico__cuil_responsable",
                                            output_field=CharField()
                                        ),
                                        Value(" (persona física)")
                                    )
                                ),
                                When(
                                    Q(
                                        responsablesolicitud__cuit_organizacion_responsable__isnull=False
                                    ) & Q(
                                        responsablesolicitud__aceptacion_responsable=True
                                    ) & Q(
                                        responsablesolicitud__tiempo_decision_comitente__isnull=True
                                    ),
                                    then=Concat(
                                        Value("Falta ser aceptado: "),
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__last_name"),
                                        Value(", "),
                                        F("responsablesolicitud__responsable_tecnico__usuario_responsable__first_name"),
                                        Value(". "),
                                        F("responsablesolicitud__puesto_organizacion_responsable"),
                                        Value(" - "),
                                        F("responsablesolicitud__razon_social_responsable"),
                                        Value(". CUIT: "),
                                        Cast(
                                            "responsablesolicitud__cuit_organizacion_responsable",
                                            output_field=CharField()
                                        )
                                    )
                                ),
                                default=None
                            ),
                            distinct=True,
                            default=Value([])
                        )
                    ),
                    default=None
                )
            ).order_by(
                "-ultima_accion_solicitud"
            )
        return solicitudes_servicio

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
        solicitudes: QuerySet[SolicitudServicio] = self.get_queryset()
        paginador_curso: Paginator = Paginator(
            solicitudes.filter(
                Q(
                    cancelacion_solicitud__isnull=True
                ) & (
                    Q(
                        solicitud_suspendida__isnull=True
                    ) |
                    Q(
                        solicitud_suspendida=False
                    )
                )
            ),
            self.paginate_by
        )
        objeto_pagina_curso: Page = paginador_curso.get_page(None)
        contexto["pagina_curso"] = objeto_pagina_curso
        paginador_suspendido: Paginator = Paginator(
            solicitudes.filter(
                Q(
                    cancelacion_solicitud__isnull=True
                ) &
                Q(
                    solicitud_suspendida__isnull=False
                ) &
                Q(
                    solicitud_suspendida=True
                )
            ),
            self.paginate_by
        )
        objeto_pagina_suspendido: Page = paginador_suspendido.get_page(None)
        contexto["pagina_suspendido"] = objeto_pagina_suspendido
        paginador_cancelado: Paginator = Paginator(
            solicitudes.filter(
                Q(
                    cancelacion_solicitud__isnull=False
                )
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
            solicitudes: QuerySet[SolicitudServicio] = (
                self.get_queryset() if (
                    si_por_pagina and
                    elementos_por_pagina != "" and
                    elementos_por_pagina.isdigit() and
                    por_pagina != 0
                ) else SolicitudServicio.objects.none()
            )
            if si_nombre and nombre.strip() != "":
                cadenas: list[str] = unidecode(nombre.strip()).split()
                busqueda: Q = Q(
                    nombre_solicitud__unaccent__icontains=cadenas[0]
                )
                for cadena in cadenas[1:]:
                    busqueda &= Q(
                        nombre_solicitud__unaccent__icontains=cadena
                    )
                solicitudes = solicitudes.filter(busqueda)
            tipo: Optional[str] = request.GET.get("tipo")
            if not tipo or tipo == "curso":
                solicitudes_curso: QuerySet[SolicitudServicio] = solicitudes.filter(
                    Q(
                        cancelacion_solicitud__isnull=True
                    ) & (
                        Q(
                            solicitud_suspendida__isnull=True
                        ) |
                        Q(
                            solicitud_suspendida=False
                        )
                    )
                )
                paginador_curso: Paginator = Paginator(
                    solicitudes_curso,
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
                        "parciales/_lista_solicitudes_en_curso_comitente.html",
                        {"pagina_curso": objeto_pagina_curso}
                    )
            if not tipo or tipo == "suspendido":
                solicitudes_suspendido: QuerySet[SolicitudServicio] = solicitudes.filter(
                    Q(
                        cancelacion_solicitud__isnull=True
                    ) &
                    Q(
                        solicitud_suspendida__isnull=False
                    ) &
                    Q(
                        solicitud_suspendida=True
                    )
                )
                paginador_suspendido: Paginator = Paginator(
                    solicitudes_suspendido,
                    por_pagina if por_pagina != 0 else self.paginate_by
                )
                '''
                Si no existe "pagina" como parámetro del método
                GET, objeto_pagina será 1 por defecto
                '''
                objeto_pagina_suspendido: Page = paginador_suspendido.get_page(
                    request.GET.get("pagina")
                )
                if tipo == "suspendido":
                    return render(
                        request,
                        "parciales/_lista_solicitudes_suspendidas_comitente.html",
                        {"pagina_suspendido": objeto_pagina_suspendido}
                    )
            if not tipo or tipo == "cancelado":
                solicitudes_cancelado: QuerySet[SolicitudServicio] = solicitudes.filter(
                    Q(
                        cancelacion_solicitud__isnull=False
                    )
                )
                paginador_cancelado: Paginator = Paginator(
                    solicitudes_cancelado,
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
                        "parciales/_lista_solicitudes_canceladas_comitente.html",
                        {"pagina_cancelado": objeto_pagina_cancelado}
                    )
            return render(
                request,
                "parciales/_lista_solicitudes_comitente.html",
                {
                    "pagina_curso": objeto_pagina_curso,
                    "pagina_suspendido": objeto_pagina_suspendido,
                    "pagina_cancelado": objeto_pagina_cancelado
                }
            )
        return super(
            VistaListaSolicitudesComitente,
            self
        ).get(request)
