from django.db import models

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError

from typing import Self

from .validaciones import es_valido_cuil, es_valido_cuit


class Comitente(models.Model):
    usuario_comitente: models.OneToOneField = \
        models.OneToOneField(
            verbose_name='Usuario de Comitente',
            to=settings.AUTH_USER_MODEL,
            on_delete=models.PROTECT,
            primary_key=True
        )
    cuil_comitente: models.PositiveBigIntegerField = \
        models.PositiveBigIntegerField(
            verbose_name='CUIL de Comitente',
            unique=True
        )
    firma_digital_comitente: models.BooleanField = \
        models.BooleanField(
            verbose_name='Si Comitente tiene firma digital',
            default=False
        )
    habilitado_comitente: models.BooleanField = \
        models.BooleanField(
            verbose_name='Si la persona física está habilitada como Comitente',
            null=True,
            default=None
        )
    razones_sociales_comitente: ArrayField = \
        ArrayField(
            models.CharField(
                max_length=64,
                blank=False
            ),
            verbose_name='Razones Sociales en Organizaciones de Comitente'
        )
    cuit_organizaciones_comitente: ArrayField = \
        ArrayField(
            models.BigIntegerField(
                unique=True
            ),
            verbose_name='CUIT en Organizaciones de Comitente'
        )
    puestos_organizaciones_comitente: ArrayField = \
        ArrayField(
            models.CharField(
                max_length=64,
                blank=False
            ),
            verbose_name='Puestos en Organizaciones de Comitente'
        )
    habilitado_organizaciones_comitente: ArrayField = \
        ArrayField(
            models.BooleanField(
                null=True,
                default=None
            ),
            verbose_name='Si Comitente está habilitado por Organización'
        )

    def clean(self: Self) -> None:
        if (
            self.usuario_comitente.is_staff or
            self.usuario_comitente.is_superuser
        ):
            raise ValidationError(
                'No se puede asignar como comitente a'
                ' administradores ni staff'
            )
        if not es_valido_cuil(self.cuil_comitente):
            raise ValidationError(
                'El CUIL del comiente no es válido'
            )
        for cuit in self.cuit_organizaciones_comitente:
            if not es_valido_cuit(cuit):
                raise ValidationError(
                    'Al menos un CUIT de las organizaciones'
                    ' del comiente no es válido'
                )
        if [
            cuit for cuit in self.cuit_organizaciones_comitente if
            sum(
                habilitado for i, habilitado in
                enumerate(self.habilitado_organizaciones_comitente) if
                habilitado is True and
                self.cuit_organizaciones_comitente[i] == cuit
            ) > 1
        ]:
            raise ValidationError(
                'Al menos un CUIT de las organizaciones'
                ' del comiente es repetido'
            )
        if (
            len(self.cuit_organizaciones_comitente) !=
            len(self.razones_sociales_comitente) or
            len(self.cuit_organizaciones_comitente) !=
            len(self.puestos_organizaciones_comitente) or
            len(self.cuit_organizaciones_comitente) !=
            len(self.habilitado_organizaciones_comitente)
        ):
            raise ValidationError(
                'La cantidad de elementos para organizaciones'
                ' no es igual'
            )

    class Meta:
        db_table: str = 'comitentes'
        constraints: list[models.CheckConstraint] = \
            [
                models.CheckConstraint(
                    check=models.Q(
                        razones_sociales_comitente__len=models.F(
                            'cuit_organizaciones_comitente__len'
                        )
                    ) & models.Q(
                        razones_sociales_comitente__len=models.F(
                            'puestos_organizaciones_comitente__len'
                        )
                    ) & models.Q(
                        razones_sociales_comitente__len=models.F(
                            'habilitado_organizaciones_comitente__len'
                        )
                    ),
                    name='arrays_comitente_mismo_tamanio'
                )
            ]
