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

from ..models import ResponsableSolicitud

from cuentas.models import Notificacion


def responsables_tecnicos(
    sender: type[ResponsableSolicitud],
    instance: ResponsableSolicitud,
    created: bool,
    **kwargs
) -> None:
    if created and instance.tiempo_decision_responsable is None:
        mensaje: str = 'Ha sido asociado como Responsable Técnico' \
                        ' a la solicitud ' + str(
                            instance.solicitud_servicio.id_solicitud
                        )
        enlace: str = 'https:' if settings.SECURE_SSL_REDIRECT else 'http:'
        enlace += reverse(
            viewname='solicitudes:aceptar_solicitud_responsable',
            host=settings.DEFAULT_HOST,
            args=[instance.solicitud_servicio.id_solicitud]
        )
        notificacion: Notificacion = Notificacion(
            usuario_notificacion=instance.responsable_tecnico.usuario_responsable,
            titulo_notificacion='Responsable Técnico asociado',
            contenido_notificacion=mensaje,
            enlace_notificacion=enlace
        )
        notificacion.save()
        channel_layer: InMemoryChannelLayer = \
            ChannelLayerManager()[DEFAULT_CHANNEL_LAYER]
        evento: dict[str, Any] = {
            'id': notificacion.id_notificacion,
            'type': 'responsable_tecnico_asociado',
            'text': enlace
        }
        async_to_sync(channel_layer.group_send)(
            instance.responsable_tecnico.usuario_responsable.username,
            evento
        )
