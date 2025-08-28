from django.contrib import admin

from .admin_solicitud_servicio import AdminSolicitudServicio
from .admin_responsable_solicitud import AdminResponsableSolicitud
from .admin_propuesta_compromisos import AdminPropuestaCompromisos

from ..models import (
    SolicitudServicio,
    ComitenteSolicitud,
    ResponsableSolicitud,
    PropuestaCompromisos,
    DecisionResponsableTecnicoPropuesta,
    DecisionComitentePropuesta
)

admin.site.register(SolicitudServicio, AdminSolicitudServicio)
admin.site.register(ComitenteSolicitud)
admin.site.register(ResponsableSolicitud)
admin.site.register(PropuestaCompromisos, AdminPropuestaCompromisos)
admin.site.register(DecisionResponsableTecnicoPropuesta)
admin.site.register(DecisionComitentePropuesta)
