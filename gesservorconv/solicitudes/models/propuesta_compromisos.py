from django.db import models

from django.contrib.postgres.fields import ArrayField


class PropuestaCompromisos(models.Model):
    id_propuesta_compromiso: models.IntegerField = \
        models.AutoField(
            verbose_name='Identificador de Propuesta de Compromisos',
            primary_key=True
        )
    solicitud_servicio_propuesta: models.ForeignKey = \
        models.ForeignKey(
            verbose_name='Solicitud que corresponde a Propuesta',
            to='SolicitudServicio',
            on_delete=models.PROTECT
        )
    descripciones_compromisos_comitente: ArrayField = \
        ArrayField(
            models.CharField(
                max_length=128,
                blank=False
            ),
            verbose_name='Descripciones de Compromisos de Comitente'
        )
    descripciones_compromisos_unidad_ejecutora: ArrayField = \
        ArrayField(
            models.CharField(
                max_length=128,
                blank=False
            ),
            verbose_name='Descripciones de Compromisos de Unidad Ejecutora'
        )
    montos_retribuciones_economicas: ArrayField = \
        ArrayField(
            models.DecimalField(
                max_digits=16,
                decimal_places=2
            ),
            verbose_name='Montos de Retribuciones Económicas'
        )
    descripciones_retribuciones_economicas: ArrayField = \
        ArrayField(
            models.CharField(
                max_length=128,
                blank=False
            ),
            verbose_name='Descripciones de Retribuciones Económicas'
        )
    decisiones_responsables_tecnicos_propuesta: models.ManyToManyField = \
        models.ManyToManyField(
            verbose_name='Decisiones de Responsables Técnicos en Propuesta',
            to='ResponsableSolicitud',
            through='DecisionResponsableTecnicoPropuesta'
        )
    decisiones_comitentes_propuesta: models.ManyToManyField = \
        models.ManyToManyField(
            verbose_name='Decisiones de Comitentes en Propuesta',
            to='ComitenteSolicitud',
            through='DecisionComitentePropuesta'
        )
    es_valida_propuesta: models.BooleanField = \
        models.BooleanField(
            verbose_name='Si Propuesta de Compromisos es válida'
        )
    causa_rechazo_propuesta: models.TextField = \
        models.TextField(
            verbose_name='Causa de Rechazo de Propuesta',
            null=True,
            default=None
        )

    class Meta:
        db_table: str = 'propuestas_compromisos'
        verbose_name: str = 'propuesta de compromisos'
        verbose_name_plural: str = 'propuestas de compromisos'
        constraints: list[models.UniqueConstraint | models.CheckConstraint] = \
            [
                models.CheckConstraint(
                    check=models.Q(
                        montos_retribuciones_economicas__len=models.F(
                            'descripciones_retribuciones_economicas__len'
                        )
                    ),
                    name='arrays_retribuciones_economicas_mismo_tamanio'
                ),
                models.UniqueConstraint(
                    fields=[
                        'solicitud_servicio_propuesta',
                        'es_valida_propuesta'
                    ],
                    name='propuesta_compromisos_valida_unica_por_solicitud',
                    condition=models.Q(es_valida_propuesta=True)
                ),
                models.CheckConstraint(
                    check=(
                        models.Q(
                            es_valida_propuesta=True
                        ) &
                        models.Q(
                            causa_rechazo_propuesta__isnull=True
                        )
                    ) | (
                        models.Q(
                            es_valida_propuesta=False
                        ) &
                        models.Q(
                            causa_rechazo_propuesta__isnull=False
                        )
                    ),
                    name='propuesta_valida_o_con_causa_rechazo'
                )
            ]
