from django.db import models

from .auditoria import Auditoria


class Cuentas(Auditoria):
    class Meta:
        verbose_name: str = "Acción en Tabla de Cuentas"
        verbose_name_plural: str = "Acciones en Tablas de Cuentas"
        constraints: list[models.CheckConstraint] = \
            [
                models.CheckConstraint(
                    check=models.Q(
                        viejo_auditoria__isnull=False
                    ) | models.Q(
                        nuevo_auditoria__isnull=False
                    ),
                    name="auditoria_cuentas_no_nula"
                )
            ]
