from django.db import models


class OrdenServicio(models.Model):
    solicitud_servicio: models.OneToOneField = \
        models.OneToOneField(
            verbose_name='Solicitud para Orden de Servicio',
            to='solicitudes.SolicitudServicio',
            on_delete=models.PROTECT,
            primary_key=True
        )
    numero_orden_servicio: models.PositiveIntegerField = \
        models.PositiveIntegerField(
            verbose_name='Número de Orden de Servicio',
            unique=True
        )
    tiempo_creacion_orden: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Creación de Orden de Servicio',
            auto_now_add=True
        )
    firma_digital: models.BooleanField = \
        models.BooleanField(
            verbose_name='Si la Firma de Orden de Servicio es digital'
        )
    archivo_orden_original: models.FileField = \
        models.FileField(
            verbose_name='Archivo Original de Orden de Servicio',
            upload_to='ordenes_originales/',
            null=True
        )
    archivo_orden_firmada: models.FileField = \
        models.FileField(
            verbose_name='Archivo de Orden de Servicio Firmada',
            upload_to='ordenes_firmadas/',
            null=True
        )
    ultima_accion_orden: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Última Acción en Orden de Servicio',
            auto_now=True
        )
    cancelacion_orden: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Cancelación de Orden de Servicio',
            null=True,
            default=None
        )
    causa_cancelacion_orden: models.TextField = \
        models.TextField(
            verbose_name='Causa de Cancelación de Orden de Servicio',
            null=True,
            default=None
        )
    orden_suspendida: models.BooleanField = \
        models.BooleanField(
            verbose_name='Si Orden de Servicio está Suspendida'
        )

    class Meta:
        db_table: str = 'ordenes_servicio'
        verbose_name: str = 'orden de servicio'
        verbose_name_plural: str = 'órdenes de servicio'
        constraints: list[models.CheckConstraint] = \
            [
                models.CheckConstraint(
                    check=models.Q(
                        archivo_orden_firmada__isnull=True
                    ) | models.Q(
                        archivo_orden_original__isnull=False
                    ),
                    name='primero_orden_original_despues_firmada'
                ),
                models.CheckConstraint(
                    check=(
                        models.Q(cancelacion_orden__isnull=True) &
                        models.Q(causa_cancelacion_orden__isnull=True)
                    ) | (
                        models.Q(cancelacion_orden__isnull=False) &
                        models.Q(causa_cancelacion_orden__isnull=False)
                    ),
                    name='orden_cancelada_con_causa_o_no'
                )
            ]
