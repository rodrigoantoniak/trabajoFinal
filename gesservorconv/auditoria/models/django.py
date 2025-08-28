from django.db import models

from .auditoria import Auditoria


class Django(Auditoria):
    class Meta:
        verbose_name: str = "Acción en Tabla de Django"
        verbose_name_plural: str = "Acciones en Tablas de Django"
        constraints: list[models.CheckConstraint] = \
            [
                models.CheckConstraint(
                    check=models.Q(
                        viejo_auditoria__isnull=False
                    ) | models.Q(
                        nuevo_auditoria__isnull=False
                    ),
                    name="auditoria_django_no_nula"
                )
            ]
