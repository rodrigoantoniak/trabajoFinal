from django.db import models

from .auditoria import Auditoria


class Solicitudes(Auditoria):
    class Meta:
        verbose_name: str = "Acción en Tabla de Solicitudes"
        verbose_name_plural: str = "Acciones en Tablas de Solicitudes"
        constraints: list[models.CheckConstraint] = \
            [
                models.CheckConstraint(
                    check=models.Q(
                        viejo_auditoria__isnull=False
                    ) | models.Q(
                        nuevo_auditoria__isnull=False
                    ),
                    name="auditoria_solicitudes_no_nula"
                )
            ]
