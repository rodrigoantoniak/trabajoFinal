from django.db import models


class SolicitudServicio(models.Model):
    id_solicitud: models.IntegerField = \
        models.AutoField(
            verbose_name='Identificador de Solicitud de Servicio',
            primary_key=True
        )
    comitentes_solicitud: models.ManyToManyField = \
        models.ManyToManyField(
            verbose_name='Comitentes de Solicitud de Servicio',
            to='cuentas.Comitente',
            through='ComitenteSolicitud'
        )
    responsables_solicitud: models.ManyToManyField = \
        models.ManyToManyField(
            verbose_name='Responsables de Solicitud de Servicio',
            to='cuentas.ResponsableTecnico',
            through='ResponsableSolicitud'
        )
    nombre_solicitud: models.CharField = \
        models.CharField(
            verbose_name='Nombre de Solicitud de Servicio',
            max_length=128,
            blank=False
        )
    descripcion_solicitud: models.TextField = \
        models.TextField(
            verbose_name='Descripción de Solicitud de Servicio',
            blank=False
        )
    categorias_solicitud: models.ManyToManyField = \
        models.ManyToManyField(
            verbose_name='Categorías de Solicitud',
            to='Categoria'
        )
    por_convenio: models.BooleanField = \
        models.BooleanField(
            verbose_name='Si Servicio se realizará a través de Convenio',
            null=True,
            default=False
        )
    ultima_accion_solicitud: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Última Acción en Solicitud',
            auto_now=True
        )
    responsables_autoadjudicados: models.BooleanField = \
        models.BooleanField(
            verbose_name='Si los Responsables Técnicos pueden autoadjudicarse'
        )
    autoadjudicacion_abierta: models.BooleanField = \
        models.BooleanField(
            verbose_name='Si hay autoadjudicación abierta',
            null=True,
            default=False
        )
    cancelacion_solicitud: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Cancelación de Solicitud',
            null=True,
            default=None
        )
    solicitud_suspendida: models.BooleanField = \
        models.BooleanField(
            verbose_name='Si Solicitud está Suspendida',
            null=True
        )

    class Meta:
        db_table: str = 'solicitudes_servicio'
        verbose_name: str = 'solicitud de servicio'
        verbose_name_plural: str = 'solicitudes de servicio'
        constraints: list[models.CheckConstraint] = \
            [
                models.CheckConstraint(
                    check=(
                        models.Q(
                            responsables_autoadjudicados=False
                        ) & (
                            models.Q(
                                autoadjudicacion_abierta=False
                            ) |
                            models.Q(
                                autoadjudicacion_abierta__isnull=True
                            )
                        )
                    ) | (
                        models.Q(
                            responsables_autoadjudicados=True
                        ) &
                        models.Q(
                            autoadjudicacion_abierta__isnull=False
                        )
                    ),
                    name='restriccion_autoadjudicacion_solicitud'
                ),
            ]
