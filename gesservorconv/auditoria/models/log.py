from django.db import models

from uuid import uuid4


class Log(models.Model):
    uuid_log: models.UUIDField = models.UUIDField(
        verbose_name="Identificador único universal de Log",
        primary_key=True,
        default=uuid4,
        editable=False
    )
    cliente_log: models.CharField = models.CharField(
        verbose_name="Cliente de Log"
    )
    tiempo_log: models.DateTimeField = models.DateTimeField(
        verbose_name="Tiempo de Log"
    )
    navegador_log: models.CharField = models.CharField(
        verbose_name="Navegador de Log"
    )
    usuario_log: models.IntegerField = models.IntegerField(
        verbose_name='Usuario de Log',
        null=True
    )
    mensaje_log: models.CharField = models.CharField(
        verbose_name="Mensaje de Log"
    )

    class Meta:
        db_table: str = "logs"
