from django.db import models

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError

from typing import Self

from .validaciones import es_valido_cuil, es_valido_cuit


class ResponsableTecnico(models.Model):
    usuario_responsable: models.OneToOneField = \
        models.OneToOneField(
            verbose_name='Usuario de Responsable Técnico',
            to=settings.AUTH_USER_MODEL,
            on_delete=models.PROTECT,
            primary_key=True
        )
    cuil_responsable: models.PositiveBigIntegerField = \
        models.PositiveBigIntegerField(
            verbose_name='CUIL de Responsable Técnico',
            unique=True
        )
    firma_digital_responsable: models.BooleanField = \
        models.BooleanField(
            verbose_name='Si Responsable Técnico tiene firma digital',
            default=False
        )
    habilitado_responsable: models.BooleanField = \
        models.BooleanField(
            verbose_name='Si Responsable Técnico está habilitado',
            null=True,
            default=None
        )
    razones_sociales_responsable: ArrayField = \
        ArrayField(
            models.CharField(
                max_length=64,
                blank=False
            ),
            verbose_name='Razones Sociales en Organizaciones de'
                         ' Responsable Técnico'
        )
    cuit_organizaciones_responsable: ArrayField = \
        ArrayField(
            models.BigIntegerField(
                unique=True
            ),
            verbose_name='CUIT en Organizaciones de Responsable Técnico'
        )
    puestos_organizaciones_responsable: ArrayField = \
        ArrayField(
            models.CharField(
                max_length=64,
                blank=False
            ),
            verbose_name='Puestos en Organizaciones de Responsable Técnico'
        )
    habilitado_organizaciones_responsable: ArrayField = \
        ArrayField(
            models.BooleanField(
                null=True,
                default=None
            ),
            verbose_name='Si Responsable Técnico está habilitado por'
                         ' Organización'
        )

    def clean(self: Self) -> None:
        if (
            self.usuario_responsable.is_staff or
            self.usuario_responsable.is_superuser
        ):
            raise ValidationError(
                'No se puede asignar como resonsable técnico a'
                ' administradores ni staff'
            )
        if not es_valido_cuil(self.cuil_responsable):
            raise ValidationError(
                'El CUIL del responsable técnico no es válido'
            )
        for cuit in self.cuit_organizaciones_responsable:
            if not es_valido_cuit(cuit):
                raise ValidationError(
                    'Al menos un CUIT de las organizaciones'
                    ' del responsable técnico no es válido'
                )
        if [
            cuit for cuit in self.cuit_organizaciones_responsable if
            sum(
                habilitado for i, habilitado in
                enumerate(self.habilitado_organizaciones_responsable) if
                habilitado is True and
                self.cuit_organizaciones_responsable[i] == cuit
            ) > 1
        ]:
            raise ValidationError(
                'Al menos un CUIT de las organizaciones'
                ' del responsable técnico es repetido'
            )
        if (
            len(self.cuit_organizaciones_responsable) !=
            len(self.razones_sociales_responsable) or
            len(self.cuit_organizaciones_responsable) !=
            len(self.puestos_organizaciones_responsable) or
            len(self.cuit_organizaciones_responsable) !=
            len(self.habilitado_organizaciones_responsable)
        ):
            raise ValidationError(
                'La cantidad de elementos para organizaciones'
                ' no es igual'
            )

    class Meta:
        db_table: str = 'responsables_tecnicos'
        verbose_name: str = 'responsable técnico'
        verbose_name_plural: str = 'responsables técnicos'
        constraints: list[models.CheckConstraint] = \
            [
                models.CheckConstraint(
                    check=models.Q(
                        razones_sociales_responsable__len=models.F(
                            'cuit_organizaciones_responsable__len'
                        )
                    ) & models.Q(
                        razones_sociales_responsable__len=models.F(
                            'puestos_organizaciones_responsable__len'
                        )
                    ) & models.Q(
                        razones_sociales_responsable__len=models.F(
                            'habilitado_organizaciones_responsable__len'
                        )
                    ),
                    name='arrays_responsable_mismo_tamanio'
                )
            ]
