from django.urls import URLPattern, path

from . import views

app_name: str = 'auditoria'
urlpatterns: list[URLPattern] = [
    path(
        'auditoria/',
        views.VistaAuditoria.as_view(),
        name='index'
    ),
]
