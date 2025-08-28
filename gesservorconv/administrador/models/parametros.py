from django.db import models


class Parametros(models.Model):
    class Meta:
        db_table = "opciones_parametros"
        verbose_name = "Parámetros"
        verbose_name_plural = "Opciones de Parámetros"
