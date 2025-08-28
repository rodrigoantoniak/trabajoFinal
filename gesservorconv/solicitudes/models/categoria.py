from django.db import models


class Categoria(models.Model):
    facultad_categoria: models.ForeignKey = models.ForeignKey(
        verbose_name='Facultad de Categoría',
        to='Facultad',
        on_delete=models.PROTECT
    )
    nombre_categoria: models.CharField = models.CharField(
        verbose_name='Nombre de Categoría',
        max_length=32,
        blank=False
    )

    class Meta:
        db_table: str = 'categorias'
        verbose_name: str = 'categoría'
        verbose_name_plural: str = 'categorías'
