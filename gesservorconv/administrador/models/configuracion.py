from django.db import models

from django.contrib.postgres.fields import HStoreField


class Configuracion(models.Model):
    opciones: HStoreField = HStoreField(
        verbose_name="Opciones de Configuración"
    )
    actual: models.BooleanField = models.BooleanField(
        verbose_name="Si es Configuración actual"
    )

    class Meta:
        db_table: str = "configuraciones"
        verbose_name: str = "Configuración"
        verbose_name_plural: str = "Configuraciones"
        constraints: list[models.UniqueConstraint | models.CheckConstraint] = \
            [
                models.UniqueConstraint(
                    fields=[
                        'actual'
                    ],
                    name='configuracion_actual_unica',
                    condition=models.Q(actual=True)
                )
            ]
