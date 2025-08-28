from django.db import models


class ResponsableSolicitud(models.Model):
    id_responsable_solicitud: models.BigIntegerField = \
        models.BigAutoField(
            verbose_name='Identificador de Responsable por Solicitud',
            primary_key=True
        )
    responsable_tecnico: models.ForeignKey = \
        models.ForeignKey(
            verbose_name='Responsable Técnico en Solicitud',
            to='cuentas.ResponsableTecnico',
            on_delete=models.PROTECT
        )
    solicitud_servicio: models.ForeignKey = \
        models.ForeignKey(
            verbose_name='Solicitud a cargo del Responsable',
            to='SolicitudServicio',
            on_delete=models.PROTECT
        )
    tiempo_decision_comitente: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Decisión de Comitente',
            null=True,
            default=None
        )
    razon_social_responsable: models.CharField = \
        models.CharField(
            verbose_name='Razon Social en Organización de Responsable Técnico',
            max_length=64,
            blank=False,
            null=True
        )
    cuit_organizacion_responsable: models.PositiveBigIntegerField = \
        models.PositiveBigIntegerField(
            verbose_name='CUIT en Organización de Responsable Técnico',
            unique=True,
            null=True
        )
    puesto_organizacion_responsable: models.CharField = \
        models.CharField(
            verbose_name='Puesto en Organización de Responsable Técnico',
            max_length=64,
            blank=False,
            null=True
        )
    tiempo_decision_responsable: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Decisión de Responsable',
            null=True,
            default=None
        )
    aceptacion_comitente: models.BooleanField = \
        models.BooleanField(
            verbose_name='Aceptación de Comitente',
            default=False
        )
    aceptacion_responsable: models.BooleanField = \
        models.BooleanField(
            verbose_name='Aceptación de Responsable',
            default=False
        )

    class Meta:
        db_table: str = 'responsables_solicitud'
        verbose_name: str = 'responsable en solicitud'
        verbose_name_plural: str = 'responsables en solicitud'
        constraints: list[models.CheckConstraint | models.UniqueConstraint] = \
            [
                models.CheckConstraint(
                    check=(
                        (
                            models.Q(
                                cuit_organizacion_responsable__isnull=False
                            ) &
                            models.Q(
                                razon_social_responsable__isnull=False
                            )
                        ) |
                        (
                            models.Q(
                                cuit_organizacion_responsable__isnull=True
                            ) &
                            models.Q(
                                razon_social_responsable__isnull=True
                            )
                        )
                    ) & (
                        (
                            models.Q(
                                cuit_organizacion_responsable__isnull=False
                            ) &
                            models.Q(
                                puesto_organizacion_responsable__isnull=False
                            )
                        ) |
                        (
                            models.Q(
                                cuit_organizacion_responsable__isnull=True
                            ) &
                            models.Q(
                                puesto_organizacion_responsable__isnull=True
                            )
                        )
                    ),
                    name='responsable_tecnico_persona_fisica_o_juridica'
                ),
                models.CheckConstraint(
                    check=models.Q(
                        aceptacion_responsable=False
                    ) | models.Q(
                        tiempo_decision_responsable__isnull=False,
                    ),
                    name='tiempo_aceptacion_responsable_conocido'
                ),
                models.UniqueConstraint(
                    fields=[
                        'responsable_tecnico',
                        'solicitud_servicio'
                    ],
                    name='responsable_por_solicitud_unico'
                )
            ]
