from typing import Any
from asgiref.sync import async_to_sync
from channels import DEFAULT_CHANNEL_LAYER
from channels.layers import (
    InMemoryChannelLayer,
    ChannelLayerManager
)
from django.conf import settings
from django.utils.datastructures import ImmutableList
from django_hosts.resolvers import reverse

from ..models import ResponsableTecnico, Notificacion


def habilitacion_a_responsable(
    sender: type[ResponsableTecnico],
    instance: ResponsableTecnico,
    update_fields: ImmutableList[Any],
    **kwargs
) -> None:
    if sender.objects.filter(
        pk=instance.pk
    ).exists():
        if (
            instance.habilitado_responsable and
            not sender.objects.get(
                pk=instance.pk
            ).habilitado_responsable
        ):
            mensaje: str = 'Usted ha sido aceptado' \
                           ' como Representante Técnico'
            enlace: str = 'https:' if settings.SECURE_SSL_REDIRECT else 'http:'
            enlace += reverse(
                viewname='solicitudes:lista_solicitudes_responsable',
                host=settings.DEFAULT_HOST,
            )
            notificacion: Notificacion = Notificacion(
                usuario_notificacion=instance.usuario_responsable,
                titulo_notificacion='Responsable Técnico habilitado',
                contenido_notificacion=mensaje,
                enlace_notificacion=enlace
            )
            notificacion.save()
            channel_layer: InMemoryChannelLayer = \
                ChannelLayerManager()[DEFAULT_CHANNEL_LAYER]
            evento: dict[str, Any] = {
                'id': notificacion.id_notificacion,
                'type': 'responsable_habilitado',
                'text': enlace
            }
            async_to_sync(channel_layer.group_send)(
                instance.usuario_responsable.username,
                evento
            )
