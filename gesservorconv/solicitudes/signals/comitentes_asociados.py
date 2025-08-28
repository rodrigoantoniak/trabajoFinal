from typing import Any
from asgiref.sync import async_to_sync
from channels import DEFAULT_CHANNEL_LAYER
from channels.layers import (
    InMemoryChannelLayer,
    ChannelLayerManager
)
from django.conf import settings
from django.db.models import Q
from django_hosts.resolvers import reverse

from ..models import ComitenteSolicitud

from cuentas.models import Notificacion


def comitentes_asociados(
    sender: type[ComitenteSolicitud],
    instance: ComitenteSolicitud,
    created: bool,
    **kwargs
) -> None:
    if created and instance.tiempo_decision is None:
        mensaje: str = 'Ha sido asociado como Comitente' \
                        ' a la solicitud ' + str(
                            instance.solicitud_servicio.id_solicitud
                        )
        enlace: str = 'https:' if settings.SECURE_SSL_REDIRECT else 'http:'
        enlace += reverse(
            viewname='solicitudes:aceptar_solicitud_comitente',
            host=settings.DEFAULT_HOST,
            args=[instance.solicitud_servicio.id_solicitud]
        )
        notificacion: Notificacion = Notificacion(
            usuario_notificacion=instance.comitente.usuario_comitente,
            titulo_notificacion='Comitente asociado',
            contenido_notificacion=mensaje,
            enlace_notificacion=enlace
        )
        notificacion.save()
        channel_layer: InMemoryChannelLayer = \
            ChannelLayerManager()[DEFAULT_CHANNEL_LAYER]
        evento: dict[str, Any] = {
            'id': notificacion.id_notificacion,
            'type': 'comitente_asociado',
            'text': enlace
        }
        async_to_sync(channel_layer.group_send)(
            instance.comitente.usuario_comitente.username,
            evento
        )
    if not (
        created or sender.objects.filter(
            Q(solicitud_servicio=instance.solicitud_servicio) &
            Q(aceptacion=False)
        ).exists()
    ):
        mensaje: str = 'Ahora puede decidir sobre los' \
                        ' Responsables Técnicos de' \
                        ' la solicitud ' + str(
                            instance.solicitud_servicio.id_solicitud
                        )
        enlace: str = 'https:' if settings.SECURE_SSL_REDIRECT else 'http:'
        enlace += reverse(
            viewname='solicitudes:decidir_responsables',
            host=settings.DEFAULT_HOST,
            args=[instance.solicitud_servicio.id_solicitud]
        )
        notificacion: Notificacion
        channel_layer: InMemoryChannelLayer
        evento: dict[str, Any]
        for comitente_asociado in sender.objects.filter(
            Q(solicitud_servicio=instance.solicitud_servicio) &
            ~Q(comitente=instance.comitente)
        ):
            notificacion = Notificacion(
                usuario_notificacion=comitente_asociado.comitente.usuario_comitente,
                titulo_notificacion='Comitentes asociados',
                contenido_notificacion=mensaje,
                enlace_notificacion=enlace
            )
            notificacion.save()
            channel_layer = ChannelLayerManager()[DEFAULT_CHANNEL_LAYER]
            evento = {
                'id': notificacion.id_notificacion,
                'type': 'comitentes_asociados',
                'text': enlace
            }
            async_to_sync(channel_layer.group_send)(
                comitente_asociado.comitente.usuario_comitente.username,
                evento
            )
