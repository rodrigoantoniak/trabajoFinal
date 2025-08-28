from django.db import models
from django.contrib.postgres.fields import HStoreField
from django.db.backends.postgresql.base import DatabaseWrapper

from typing import Self


class OIDField(models.IntegerField):
    def db_type(self: Self, connection: DatabaseWrapper) -> str:
        return "oid"


class Auditoria(models.Model):
    id_auditoria: models.BigIntegerField = \
        models.BigAutoField(
            verbose_name="Identificador de Auditoría",
            primary_key=True
        )
    tabla_auditoria: OIDField = OIDField(
        verbose_name="Tabla en Auditoría"
    )
    tiempo_auditoria: models.DateTimeField = \
        models.DateTimeField(
            verbose_name="Tiempo de Auditoría"
        )
    viejo_auditoria: HStoreField = HStoreField(
        null=True,
        verbose_name="Valores viejos de auditoría"
    )
    nuevo_auditoria: HStoreField = HStoreField(
        null=True,
        verbose_name="Valores nuevos de auditoría"
    )

    class Meta:
        abstract: bool = True
