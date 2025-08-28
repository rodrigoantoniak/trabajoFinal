from django.db import models

from django.conf import settings


class FirmaOrden(models.Model):
    id_firma_orden: models.IntegerField = \
        models.AutoField(
            verbose_name='Identificador de Firma en Orden',
            primary_key=True
        )
    orden_firmada: models.ForeignKey = \
        models.ForeignKey(
            verbose_name='Orden Firmada',
            to='OrdenServicio',
            on_delete=models.PROTECT
        )
    usuario_firmante: models.ForeignKey = \
        models.ForeignKey(
            verbose_name='Usuario Firmante',
            to=settings.AUTH_USER_MODEL,
            on_delete=models.PROTECT
        )
    pagina_firma: models.PositiveSmallIntegerField = \
        models.PositiveSmallIntegerField(
            verbose_name='Página de Firma'
        )
    coord_x_firma: models.FloatField = \
        models.FloatField(
            verbose_name='Coordenada X de Firma'
        )
    coord_y_firma: models.FloatField = \
        models.FloatField(
            verbose_name='Coordenada Y de Firma'
        )
    tiempo_firma: models.DateTimeField = \
        models.DateTimeField(
            verbose_name='Tiempo de Firma',
            null=True
        )
    documento_firmado: models.FileField = \
        models.FileField(
            verbose_name='Documento firmado',
            upload_to='ordenes_parciales/',
            null=True
        )

    class Meta:
        db_table: str = 'firmas_ordenes'
        verbose_name: str = 'firma en orden'
        verbose_name_plural: str = 'firmas de órdenes'
        constraints: list[models.CheckConstraint | models.UniqueConstraint] = [
            models.UniqueConstraint(
                fields=[
                    'orden_firmada',
                    'usuario_firmante'
                ],
                name='usuario_unico_por_orden'
            ),
            models.UniqueConstraint(
                fields=[
                    'orden_firmada',
                    'pagina_firma',
                    'coord_x_firma',
                    'coord_y_firma'
                ],
                name='lugar_firma_unico_por_orden'
            )
        ]
