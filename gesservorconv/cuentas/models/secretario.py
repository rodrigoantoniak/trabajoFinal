from django.db import models

from django.conf import settings


class Secretario(models.Model):
    usuario_secretario: models.OneToOneField = \
        models.OneToOneField(
            verbose_name='Usuario de Secretario',
            to=settings.AUTH_USER_MODEL,
            on_delete=models.PROTECT,
            primary_key=True
        )
    firma_digital_secretario: models.BooleanField = \
        models.BooleanField(
            verbose_name='Si Secretario tiene firma digital',
            default=False
        )
    habilitado_secretario: models.BooleanField = \
        models.BooleanField(
            verbose_name='Si Secretario está habilitado',
            default=False
        )

    class Meta:
        db_table: str = 'secretarios'
        constraints: list[models.UniqueConstraint] = [
            models.UniqueConstraint(
                fields=[
                    'habilitado_secretario'
                ],
                name='secretario_habilitado_unico',
                condition=models.Q(habilitado_secretario=True)
            )
        ]
