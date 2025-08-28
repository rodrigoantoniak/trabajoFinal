from django.db.models import Q
from django.db.models.query import QuerySet

from datetime import datetime, timedelta, timezone

from .models import SolicitudServicio

from administrador.models import Configuracion

from firmas.models import Convenio, OrdenServicio

from gesservorconv.celery import app


@app.task(bind=True, ignore_result=False)
def suspender_solicitudes(self):
    solicitudes_a_suspender: QuerySet[SolicitudServicio] = \
        SolicitudServicio.objects.filter(
            ~Q(
                pk__in=OrdenServicio.objects.values_list(
                    "solicitud_servicio__id_solicitud",
                    flat=True
                )
            ) &
            ~Q(
                pk__in=Convenio.objects.values_list(
                    "solicitud_servicio__id_solicitud",
                    flat=True
                )
            ) &
            Q(
                ultima_accion_solicitud__lt=datetime.now(
                    timezone.utc
                ) - timedelta(
                    minutes=int(
                        Configuracion.objects.get(
                            actual=True
                        ).opciones['MINUTOS_SUSPENDER_SOLICITUD']
                    )
                )
            ) &
            (
                Q(solicitud_suspendida__isnull=True) |
                Q(solicitud_suspendida=False)
            ) &
            Q(cancelacion_solicitud__isnull=True)
        )
    return solicitudes_a_suspender.update(
        solicitud_suspendida=True
    )
