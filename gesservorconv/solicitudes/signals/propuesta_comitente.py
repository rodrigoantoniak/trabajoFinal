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

from ..models import DecisionComitentePropuesta

from cuentas.models import Notificacion


def propuesta_comitente(
    sender: type[DecisionComitentePropuesta],
    instance: DecisionComitentePropuesta,
    created: bool,
    **kwargs
) -> None:
    if created:
        mensaje: str = 'Existe una nueva propuesta para' \
                        ' la solicitud ' + str(
                            instance.propuesta_compromisos.solicitud_servicio_propuesta.id_solicitud
                        )
        enlace: str = 'https:' if settings.SECURE_SSL_REDIRECT else 'http:'
        enlace += reverse(
            viewname='solicitudes:revisar_propuesta_comitente',
            host=settings.DEFAULT_HOST,
            args=[instance.propuesta_compromisos.solicitud_servicio_propuesta.id_solicitud]
        )
        notificacion: Notificacion = Notificacion(
            usuario_notificacion=instance.comitente_solicitud.comitente.usuario_comitente,
            titulo_notificacion='Nueva propuesta de compromisos',
            contenido_notificacion=mensaje,
            enlace_notificacion=enlace
        )
        notificacion.save()
        channel_layer: InMemoryChannelLayer = \
            ChannelLayerManager()[DEFAULT_CHANNEL_LAYER]
        evento: dict[str, Any] = {
            'id': notificacion.id_notificacion,
            'type': 'propuesta_comitente',
            'text': enlace
        }
        async_to_sync(channel_layer.group_send)(
            instance.comitente_solicitud.comitente.usuario_comitente.username,
            evento
        )
