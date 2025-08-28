from django.db import models

from decimal import Decimal


class Pago(models.Model):
    id_pago: models.IntegerField = models.AutoField(
        verbose_name='Identificador de Pago',
        primary_key=True
    )
    servicio_pago: models.ForeignKey = models.ForeignKey(
        verbose_name='Servicio de Pago',
        to='Servicio',
        on_delete=models.PROTECT
    )
    comitente_pago: models.ForeignKey = models.ForeignKey(
        verbose_name='Comitente de Pago',
        to='cuentas.Comitente',
        on_delete=models.PROTECT
    )
    monto_pago: models.DecimalField = models.DecimalField(
        verbose_name='Monto de Pago',
        max_digits=16,
        decimal_places=2
    )

    class Meta:
        db_table: str = 'pagos'
        verbose_name: str = 'pago de servicio'
        verbose_name_plural: str = 'pagos de servicios'
        constraints: list[models.CheckConstraint] = \
            [
                models.CheckConstraint(
                    check=models.Q(
                        monto_pago__gt=Decimal(0.0)
                    ),
                    name='monto_pago_valido'
                )
            ]
