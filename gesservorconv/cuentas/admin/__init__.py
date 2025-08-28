from django.contrib import admin

from .admin_comitente import AdminComitente
from .admin_responsable import AdminResponsableTecnico

from ..models import (
    Comitente,
    ResponsableTecnico,
    Secretario,
    Notificacion
)

admin.site.register(Comitente, AdminComitente)
admin.site.register(ResponsableTecnico, AdminResponsableTecnico)
admin.site.register(Secretario)
admin.site.register(Notificacion)
