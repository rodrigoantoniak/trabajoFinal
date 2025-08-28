from django.db import models


class Facultad(models.Model):
    nombre_facultad: models.CharField = models.CharField(
        verbose_name='Nombre de Facultad',
        max_length=128,
        blank=False
    )
    acronimo_facultad: models.CharField = models.CharField(
        verbose_name='Acrónimo de Facultad',
        max_length=16,
        blank=False
    )

    class Meta:
        db_table: str = 'facultades'
        verbose_name_plural: str = 'facultades'
