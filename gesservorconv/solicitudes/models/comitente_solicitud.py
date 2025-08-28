from django.db import models


class ComitenteSolicitud(models.Model):
    id_comitente_solicitud: models.BigIntegerField = \
        models.BigAutoField(
            verbose_name='Identificador de Comitente por Solicitud',
            primary_key=True
        )
    comitente: models.ForeignKey = \
        models.ForeignKey(
            verbose_name='Comitente en Solicitud',
            to='cuentas.Comitente',
            on_delete=models.PROTECT
        )
    solicitud_servicio: models.ForeignKey = \
        models.ForeignKey(
            verbose_name='Solicitud en que participa Comitente',
            to='SolicitudServicio',
            on_delete=models.PROTECT
        )
    razon_social_comitente: models.CharField = \
        models.CharField(
            verbose_name='Razon Social en Organización de Comitente',
            max_length=64,
            blank=False,
            null=True
        )
    cuit_organizacion_comitente: models.PositiveBigIntegerField = \
        models.PositiveBigIntegerField(
            verbose_name='CUIT en Organización de Comitente',
            null=True
        )
    puesto_organizacion_comitente: models.CharField = \
        models.CharField(
            verbose_name='Puesto en Organización de Comitente',
            max_length=64,
            blank=False,
            null=True
        )
    tiempo_decision: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Decisión de Comitente',
            null=True,
            default=None
        )
    aceptacion: models.BooleanField = \
        models.BooleanField(
            verbose_name='Aceptación de Comitente',
            default=False
        )

    class Meta:
        db_table: str = 'comitentes_solicitud'
        verbose_name: str = 'comitente en solicitud'
        verbose_name_plural: str = 'comitentes en solicitud'
        constraints: list[models.CheckConstraint | models.UniqueConstraint] = \
            [
                models.CheckConstraint(
                    check=(
                        (
                            models.Q(
                                cuit_organizacion_comitente__isnull=False
                            ) &
                            models.Q(
                                razon_social_comitente__isnull=False
                            )
                        ) |
                        (
                            models.Q(
                                cuit_organizacion_comitente__isnull=True
                            ) &
                            models.Q(
                                razon_social_comitente__isnull=True
                            )
                        )
                    ) & (
                        (
                            models.Q(
                                cuit_organizacion_comitente__isnull=False
                            ) &
                            models.Q(
                                puesto_organizacion_comitente__isnull=False
                            )
                        ) |
                        (
                            models.Q(
                                cuit_organizacion_comitente__isnull=True
                            ) &
                            models.Q(
                                puesto_organizacion_comitente__isnull=True
                            )
                        )
                    ),
                    name='comitente_persona_fisica_o_juridica'
                ),
                models.CheckConstraint(
                    check=models.Q(
                        aceptacion=False
                    ) | models.Q(
                        tiempo_decision__isnull=False,
                    ),
                    name='tiempo_aceptacion_comitente_conocido'
                ),
                models.UniqueConstraint(
                    fields=[
                        'comitente',
                        'solicitud_servicio'
                    ],
                    name='comitente_por_solicitud_unico'
                )
            ]
