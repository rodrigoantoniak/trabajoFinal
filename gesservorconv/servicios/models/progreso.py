from django.db import models

from decimal import Decimal


class Progreso(models.Model):
    id_progreso: models.IntegerField = \
        models.AutoField(
            verbose_name='Identificador de Progreso',
            primary_key=True
        )
    servicio_progreso: models.ForeignKey = \
        models.ForeignKey(
            verbose_name='Servicio de Progreso',
            to='Servicio',
            on_delete=models.PROTECT
        )
    descripcion_progreso: models.TextField = \
        models.TextField(
            verbose_name='Descripción de Progreso',
            blank=False
        )
    porcentaje_progreso: models.DecimalField = models.DecimalField(
        verbose_name='Porcentaje de Progreso',
        max_digits=5, decimal_places=2
    )

    class Meta:
        db_table: str = 'progresos'
        constraints: list[models.CheckConstraint] = \
            [
                models.CheckConstraint(
                    check=models.Q(
                        porcentaje_progreso__gte=models.Value(
                            Decimal(0.0),
                            models.DecimalField()
                        )
                    ) & models.Q(
                        porcentaje_progreso__lte=models.Value(
                            Decimal(100.0),
                            models.DecimalField()
                        )
                    ),
                    name='porcentaje_progreso_valido'
                )
            ]
