from django.db import models


class Convenio(models.Model):
    solicitud_servicio: models.OneToOneField = \
        models.OneToOneField(
            verbose_name='Solicitud para Convenio',
            to='solicitudes.SolicitudServicio',
            on_delete=models.PROTECT,
            primary_key=True
        )
    tiempo_creacion_convenio: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Creación de Convenio',
            auto_now_add=True
        )
    archivo_convenio: models.FileField = \
        models.FileField(
            verbose_name='Archivo de Convenio',
            upload_to='convenios/',
            null=True
        )
    tiempo_subida_convenio: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Subida de Convenio',
            null=True
        )
    cancelacion_convenio: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Cancelación de Convenio',
            null=True,
            default=None
        )
    causa_cancelacion_convenio: models.TextField = \
        models.TextField(
            verbose_name='Causa de Cancelación de Convenio',
            null=True,
            default=None
        )
    convenio_suspendido: models.BooleanField = \
        models.BooleanField(
            verbose_name='Si Convenio está Suspendido'
        )

    class Meta:
        db_table: str = 'convenios'
        verbose_name_plural: str = 'convenios'
        constraints: list[models.CheckConstraint] = \
            [
                models.CheckConstraint(
                    check=(
                        models.Q(cancelacion_convenio__isnull=True) &
                        models.Q(causa_cancelacion_convenio__isnull=True)
                    ) | (
                        models.Q(cancelacion_convenio__isnull=True) &
                        models.Q(causa_cancelacion_convenio__isnull=False) &
                        models.Q(archivo_convenio__isnull=True)
                    ),
                    name='convenio_cancelado_con_causa_y_sin_archivo_o_no'
                )
            ]
