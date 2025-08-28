from typing import Any
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from channels_redis.core import RedisChannelLayer
from django.template.loader import get_template


class ConsumidorNotificaciones(WebsocketConsumer):
    channel_layer: RedisChannelLayer

    def connect(self) -> None:
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            self.close()
            return
        async_to_sync(self.channel_layer.group_add)(
            self.user.username, self.channel_name
        )
        return super().connect()

    def disconnect(self, code: dict[str, Any]) -> None:
        if self.user.is_authenticated:
            async_to_sync(self.channel_layer.group_discard)(
                self.user.username, self.channel_name
            )
        return super().disconnect(code)

    def comitente_habilitado(self, evento: dict[str, Any]) -> None:
        html: str = get_template('parciales/_mensaje.html').render(
            {
                'id': evento['id'],
                'titulo': 'Comitente',
                'mensaje': 'Nuevo rol habilitado como Comitente',
                'enlace': evento['text']
            }
        )
        self.send(text_data=html)

    def responsable_habilitado(self, evento: dict[str, Any]) -> None:
        html: str = get_template('parciales/_mensaje.html').render(
            {
                'id': evento['id'],
                'titulo': 'Responsable Técnico',
                'mensaje': 'Nuevo rol habilitado como Responsable Técnico',
                'enlace': evento['text']
            }
        )
        self.send(text_data=html)

    def comitente_asociado(self, evento: dict[str, Any]) -> None:
        html: str = get_template('parciales/_mensaje.html').render(
            {
                'id': evento['id'],
                'titulo': 'Comitente Asociado',
                'mensaje': 'Puede ser Comitente de una nueva solicitud',
                'enlace': evento['text']
            }
        )
        self.send(text_data=html)

    def comitentes_asociados(self, evento: dict[str, Any]) -> None:
        html: str = get_template('parciales/_mensaje.html').render(
            {
                'id': evento['id'],
                'titulo': 'Comitentes Asociados',
                'mensaje': 'Puede decidir por los Responsables Técnicos',
                'enlace': evento['text']
            }
        )
        self.send(text_data=html)

    def responsable_tecnico_asociado(self, evento: dict[str, Any]) -> None:
        html: str = get_template('parciales/_mensaje.html').render(
            {
                'id': evento['id'],
                'titulo': 'Responsable Técnico asociado',
                'mensaje': 'Puede ser Responsable Técnico de una nueva solicitud',
                'enlace': evento['text']
            }
        )
        self.send(text_data=html)

    def propuesta_comitente(self, evento: dict[str, Any]) -> None:
        html: str = get_template('parciales/_mensaje.html').render(
            {
                'id': evento['id'],
                'titulo': 'Nueva propuesta de compromisos',
                'mensaje': 'Puede decidir sobre propuesta de compromisos',
                'enlace': evento['text']
            }
        )
        self.send(text_data=html)
