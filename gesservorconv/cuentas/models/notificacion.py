from django.contrib.auth.models import User
from django.db import models


class Notificacion(models.Model):
    id_notificacion: models.BigIntegerField = \
        models.BigAutoField(
            verbose_name='Identificador de Notificación',
            primary_key=True
        )
    usuario_notificacion: models.ForeignKey[User] = \
        models.ForeignKey(
            verbose_name='Usuario de Notificación',
            to=User,
            on_delete=models.PROTECT
        )
    tiempo_notificacion: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Notificación',
            auto_now=True
        )
    lectura_notificacion: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Notificación',
            null=True,
            default=None
        )
    titulo_notificacion: models.CharField = \
        models.CharField(
            verbose_name='Título de Notificación',
            blank=False
        )
    contenido_notificacion: models.TextField = \
        models.TextField(
            verbose_name='Título de Notificación',
            blank=False
        )
    enlace_notificacion: models.CharField = \
        models.CharField(
            verbose_name='Enlace de Notificación',
            blank=False
        )

    class Meta:
        db_table: str = 'notificaciones'
        verbose_name: str = 'notificación'
        verbose_name_plural: str = 'notificaciones'
