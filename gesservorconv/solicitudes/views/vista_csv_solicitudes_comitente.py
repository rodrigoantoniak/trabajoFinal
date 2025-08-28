from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Permission
from django.db.models import Case, CharField, Min, Q, QuerySet, Value, When
from django.http import (
    FileResponse,
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect
)
from django.urls import reverse_lazy
from django.views.generic import View

import csv
from io import StringIO
from typing import Self

from ..models import (
    SolicitudServicio,
    ComitenteSolicitud
)

from firmas.models import Convenio, OrdenServicio

from cuentas.models import Comitente

from gesservorconv.mixins import (
    MixinAccesoRequerido,
    MixinPermisoRequerido
)


class VistaCsvSolicitudesComitente(
    MixinAccesoRequerido,
    MixinPermisoRequerido,
    UserPassesTestMixin,
    View
):
    permission_required: QuerySet[Permission] = Permission.objects.filter(
        codename=f"view_{SolicitudServicio.__name__.lower()}"
    )

    def test_func(self: Self) -> bool:
        return Comitente.objects.filter(
            Q(usuario_comitente=self.request.user)
        ).exists()

    def handle_no_permission(self: Self) -> HttpResponse:
        if self.request.user.is_anonymous:
            messages.warning(
                self.request,
                ("La sesión ha caducado")
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
            reverse_lazy("cuentas:perfil")
        )

    def get(
        self,
        request: HttpRequest
    ) -> FileResponse:
        solicitudes_servicio: QuerySet[SolicitudServicio] = \
            SolicitudServicio.objects.filter(
                pk__in=ComitenteSolicitud.objects.filter(
                    comitente__usuario_comitente=self.request.user,
                    aceptacion=True
                ).values_list(
                    "solicitud_servicio", flat=True
                )
            ).annotate(
                tiempo_creacion=Min(
                    "comitentesolicitud__tiempo_decision",
                    filter=Q(
                        comitentesolicitud__tiempo_decision__isnull=False
                    )
                )
            ).annotate(
                estado=Case(
                    When(
                        Q(
                            pk__in=OrdenServicio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ) |
                        Q(
                            pk__in=Convenio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ),
                        then=Value("Completo")
                    ),
                    When(
                        ~Q(
                            pk__in=OrdenServicio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ) &
                        ~Q(
                            pk__in=Convenio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ) &
                        Q(
                            cancelacion_solicitud__isnull=True
                        ) & (
                            Q(
                                solicitud_suspendida__isnull=True
                            ) |
                            Q(
                                solicitud_suspendida=False
                            )
                        ),
                        then=Value("En curso")
                    ),
                    When(
                        ~Q(
                            pk__in=OrdenServicio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ) &
                        ~Q(
                            pk__in=Convenio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ) &
                        Q(
                            cancelacion_solicitud__isnull=True
                        ) &
                        Q(
                            solicitud_suspendida__isnull=False
                        ) &
                        Q(
                            solicitud_suspendida=True
                        ),
                        then=Value("Suspendido")
                    ),
                    When(
                        ~Q(
                            pk__in=OrdenServicio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ) &
                        ~Q(
                            pk__in=Convenio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ) &
                        Q(
                            cancelacion_solicitud__isnull=False
                        ),
                        then=Value("Cancelado")
                    ),
                    output_field=CharField()
                )
            )
        buffer: StringIO = StringIO()
        archivo: csv.DictWriter = csv.DictWriter(
            buffer,
            fieldnames=[
                "id_solicitud",
                "nombre_solicitud",
                "descripcion_solicitud",
                "tiempo_creacion",
                "estado"
            ],
            dialect="unix"  # El servidor será Linux, es adecuado
        )
        archivo.writeheader()
        archivo.writerows(
            {
                "id_solicitud": solicitud.id_solicitud,
                "nombre_solicitud": solicitud.nombre_solicitud,
                "descripcion_solicitud": solicitud.descripcion_solicitud,
                "tiempo_creacion": solicitud.tiempo_creacion,
                "estado": solicitud.estado
            }
            for solicitud in solicitudes_servicio
        )
        return FileResponse(
            buffer.getvalue(),
            as_attachment=True,
            filename="solicitudesServicio.csv",
            content_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="solicitudesServicio.csv"'
            }
        )
