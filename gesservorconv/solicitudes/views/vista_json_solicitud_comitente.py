from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Min, Q
from django.http import JsonResponse, HttpRequest
from django.views import generic

from typing import Self

from ..models import SolicitudServicio, ComitenteSolicitud

from firmas.models import Convenio, OrdenServicio

from cuentas.models import Comitente

from gesservorconv.mixins import MixinAccesoRequerido


class VistaJsonSolicitudComitente(
    MixinAccesoRequerido,
    UserPassesTestMixin,
    generic.View
):
    def test_func(self: Self) -> bool:
        return Comitente.objects.filter(
            usuario_comitente=self.request.user
        ).exists()

    def handle_no_permission(self: Self) -> JsonResponse:
        return JsonResponse(
            status=403,
            data={
                "error": "Usuario no autorizado"
            }
        )

    def get(
        self: Self,
        request: HttpRequest,
        solicitud: int
    ) -> JsonResponse:
        if not SolicitudServicio.objects.filter(
            Q(id_solicitud=solicitud)
        ).exists():
            return JsonResponse(
                status=404,
                data={
                    "error": "No existe la solicitud de servicio",
                },
                headers={
                    "Content-Language": "es-AR"
                }
            )
        if not ComitenteSolicitud.objects.filter(
            Q(comitente__usuario_comitente=request.user) &
            Q(solicitud_servicio__id_solicitud=solicitud)
        ).exists():
            return JsonResponse(
                status=403,
                data={
                    "error": "Usted no es Comitente en este servicio",
                },
                headers={
                    "Content-Language": "es-AR"
                }
            )
        if ComitenteSolicitud.objects.filter(
            Q(comitente__usuario_comitente=request.user) &
            Q(solicitud_servicio__id_solicitud=solicitud) &
            Q(tiempo_decision__isnull=True)
        ).exists():
            return JsonResponse(
                status=401,
                data={
                    "error": "Usted aún no ha decidido sobre si es"
                             " Comitente o no en esta solicitud de"
                             " servicio",
                },
                headers={
                    "Content-Language": "es-AR"
                }
            )
        if (
            OrdenServicio.objects.filter(
                solicitud_servicio__id_solicitud=solicitud
            ).exists() or
            Convenio.objects.filter(
                solicitud_servicio__id_solicitud=solicitud
            ).exists()
        ):
            return JsonResponse(
                status=418,
                data={
                    "error": "El estado de este servicio ya no es"
                             " de una solicitud",
                },
                headers={
                    "Content-Language": "es-AR"
                }
            )
        solicitud_servicio: SolicitudServicio = \
            SolicitudServicio.objects.filter(
                id_solicitud=solicitud
            ).annotate(
                tiempo_creacion=Min(
                    "comitentesolicitud__tiempo_decision",
                    filter=Q(
                        comitentesolicitud__tiempo_decision__isnull=False
                    )
                )
            )
        return JsonResponse(
            data={
                "nombre": solicitud_servicio.first().nombre_solicitud,
                "descripcion": solicitud_servicio.first().descripcion_solicitud,
                "tiempo_creacion": solicitud_servicio.first().tiempo_creacion.isoformat(),
                "estado": (
                    "Cancelado"
                    if solicitud_servicio.first().cancelacion_solicitud is not None
                    else "Suspendido"
                    if solicitud_servicio.first().solicitud_suspendida
                    else "En curso"
                ),
                "comitentes_que_aceptaron": [
                    (
                        f"{comitente.comitente.usuario_comitente.last_name},"
                        f" {comitente.comitente.usuario_comitente.first_name}."
                        f" {comitente.puesto_organizacion_comitente} -"
                        f" {comitente.razon_social_comitente}. CUIT:"
                        f" {comitente.cuit_organizacion_comitente}"
                        if comitente.cuit_organizacion_comitente else
                        f"{comitente.comitente.usuario_comitente.last_name},"
                        f" {comitente.comitente.usuario_comitente.first_name}."
                        f" CUIL: {comitente.comitente.cuil_comitente}"
                        " (persona física)"
                    ) for comitente
                    in solicitud_servicio.first().comitentesolicitud_set.filter(
                        aceptacion=True
                    )
                ],
                "comitentes_que_no_decidieron": [
                    (
                        f"{comitente.comitente.usuario_comitente.last_name},"
                        f" {comitente.comitente.usuario_comitente.first_name}."
                        f" {comitente.puesto_organizacion_comitente} -"
                        f" {comitente.razon_social_comitente}. CUIT:"
                        f" {comitente.cuit_organizacion_comitente}"
                        if comitente.cuit_organizacion_comitente else
                        f"{comitente.comitente.usuario_comitente.last_name},"
                        f" {comitente.comitente.usuario_comitente.first_name}."
                        f" CUIL: {comitente.comitente.cuil_comitente}"
                        " (persona física)"
                    ) for comitente
                    in solicitud_servicio.first().comitentesolicitud_set.filter(
                        tiempo_decision__isnull=True
                    )
                ],
                "comitentes_que_rechazaron": [
                    (
                        f"{comitente.comitente.usuario_comitente.last_name},"
                        f" {comitente.comitente.usuario_comitente.first_name}."
                        f" {comitente.puesto_organizacion_comitente} -"
                        f" {comitente.razon_social_comitente}. CUIT:"
                        f" {comitente.cuit_organizacion_comitente}"
                        if comitente.cuit_organizacion_comitente else
                        f"{comitente.comitente.usuario_comitente.last_name},"
                        f" {comitente.comitente.usuario_comitente.first_name}."
                        f" CUIL: {comitente.comitente.cuil_comitente}"
                        " (persona física)"
                    ) for comitente
                    in solicitud_servicio.first().comitentesolicitud_set.filter(
                        tiempo_decision__isnull=False,
                        aceptacion=False
                    )
                ]
            },
            headers={
                "Content-Language": "es-AR"
            }
        )
