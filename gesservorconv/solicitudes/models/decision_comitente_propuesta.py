from django.db import models


class DecisionComitentePropuesta(models.Model):
    id_decision_responsable_tecnico_propuesta: models.BigIntegerField = \
        models.BigAutoField(
            verbose_name='Identificador de Decisión de Comitente en Propuesta',
            primary_key=True
        )
    comitente_solicitud: models.ForeignKey = \
        models.ForeignKey(
            verbose_name='Comitente en Decisión de Propuesta',
            to='ComitenteSolicitud',
            on_delete=models.PROTECT
        )
    propuesta_compromisos: models.ForeignKey = \
        models.ForeignKey(
            verbose_name='Propuesta de Compromisos a decidir por el Comitente',
            to='PropuestaCompromisos',
            on_delete=models.PROTECT
        )
    tiempo_decision_propuesta: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Decisión sobre Propuesta',
            null=True,
            default=None
        )
    aceptacion_propuesta: models.BooleanField = \
        models.BooleanField(
            verbose_name='Aceptación de Propuesta',
            default=False
        )

    class Meta:
        db_table: str = 'decisiones_comitentes_propuesta'
        verbose_name: str = 'decisión de comitente sobre propuesta'
        verbose_name_plural: str = 'decisiones de comitentes sobre propuestas'
        constraints: list[models.CheckConstraint | models.UniqueConstraint] = \
            [
                models.CheckConstraint(
                    check=models.Q(
                        aceptacion_propuesta=False
                    ) | models.Q(
                        tiempo_decision_propuesta__isnull=False,
                    ),
                    name='tiempo_aceptacion_propuesta_conocido'
                ),
                models.UniqueConstraint(
                    fields=[
                        'comitente_solicitud',
                        'propuesta_compromisos'
                    ],
                    name='comitente_por_propuesta_unico'
                )
            ]
