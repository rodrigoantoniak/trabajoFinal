from django.urls import URLPattern, path

from . import views

app_name: str = "servicios"
urlpatterns: list[URLPattern] = [
    path(
        "comitente/servicios/",
        views.VistaJsonSolicitudesSugeribles.as_view(),
        name="json_comitente"
    ),
    path(
        "responsable/servicios/",
        views.VistaListaServiciosResponsable.as_view(),
        name="lista_servicios_responsable"
    ),
    path(
        "responsable/servicios/<int:servicio>/nuevo_progreso/",
        views.VistaNuevoProgreso.as_view(),
        name="agregar_progreso"
    ),
    path(
        "secretario/servicios/",
        views.VistaListaServiciosSecretario.as_view(),
        name="lista_servicios_secretario"
    ),
    path(
        "secretario/servicios/<int:servicio>/cancelar/",
        views.VistaCancelarServicio.as_view(),
        name="cancelar_servicio"
    ),
    path(
        "ayudante/servicios/",
        views.VistaListaServiciosAyudante.as_view(),
        name="lista_servicios_ayudante"
    ),
    path(
        "ayudante/servicios/<int:servicio>/nuevo_pago/",
        views.VistaNuevoPago.as_view(),
        name="agregar_pago"
    ),
]
