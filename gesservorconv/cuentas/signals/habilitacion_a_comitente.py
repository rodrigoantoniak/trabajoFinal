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

from ..models import Comitente, Notificacion


def habilitacion_a_comitente(
    sender: type[Comitente],
    instance: Comitente,
    update_fields: ImmutableList[Any],
    **kwargs
) -> None:
    if sender.objects.filter(
        pk=instance.pk
    ).exists():
        if (
            instance.habilitado_comitente is True and
            sender.objects.get(
                pk=instance.pk
            ).habilitado_comitente is not True
        ):
            mensaje: str = 'Usted ha sido aceptado' \
                           ' como persona física Comitente'
            enlace: str = 'https:' if settings.SECURE_SSL_REDIRECT else 'http:'
            enlace += reverse(
                viewname='solicitudes:agregar_solicitud',
                host=settings.DEFAULT_HOST,
            )
            notificacion: Notificacion = Notificacion(
                usuario_notificacion=instance.usuario_comitente,
                titulo_notificacion='Comitente habilitado',
                contenido_notificacion=mensaje,
                enlace_notificacion=enlace
            )
            notificacion.save()
            channel_layer: InMemoryChannelLayer = \
                ChannelLayerManager()[DEFAULT_CHANNEL_LAYER]
            evento: dict[str, Any] = {
                'id': notificacion.id_notificacion,
                'type': 'comitente_habilitado',
                'text': enlace
            }
            async_to_sync(channel_layer.group_send)(
                instance.usuario_comitente.username,
                evento
            )
