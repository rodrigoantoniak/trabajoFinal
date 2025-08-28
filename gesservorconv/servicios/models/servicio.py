from django.db import models


class Servicio(models.Model):
    id_servicio: models.IntegerField = models.AutoField(
        verbose_name='Identificador de servicio',
        primary_key=True
    )
    orden_servicio: models.OneToOneField = models.OneToOneField(
        verbose_name='Orden de Servicio anexa',
        to='firmas.OrdenServicio',
        on_delete=models.PROTECT,
        null=True
    )
    convenio: models.OneToOneField = models.OneToOneField(
        verbose_name='Convenio anexo',
        to='firmas.Convenio',
        on_delete=models.PROTECT,
        null=True
    )
    pagado: models.BooleanField = models.BooleanField(
        verbose_name='Si servicio está pagado',
        default=False
    )
    completado: models.BooleanField = models.BooleanField(
        verbose_name='Si servicio está completo',
        default=False
    )
    cancelacion_servicio: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Cancelación de Servicio',
            null=True,
            default=None
        )
    causa_cancelacion_servicio: models.TextField = \
        models.TextField(
            verbose_name='Causa de Cancelación de Servicio',
            null=True,
            default=None
        )

    class Meta:
        db_table: str = 'servicios'
        constraints: list[models.UniqueConstraint | models.CheckConstraint] = \
            [
                models.CheckConstraint(
                    check=(
                        models.Q(
                            orden_servicio__isnull=True
                        ) &
                        models.Q(
                            convenio__isnull=False
                        )
                    ) | (
                        models.Q(
                            orden_servicio__isnull=False
                        ) &
                        models.Q(
                            convenio__isnull=True
                        )
                    ),
                    name='u_orden_servicio_o_convenio'
                ),
                models.CheckConstraint(
                    check=(
                        models.Q(cancelacion_servicio__isnull=True) &
                        models.Q(causa_cancelacion_servicio__isnull=True)
                    ) | (
                        models.Q(cancelacion_servicio__isnull=False) &
                        models.Q(causa_cancelacion_servicio__isnull=False)
                    ),
                    name='servicio_cancelado_con_causa_o_no'
                )
            ]
