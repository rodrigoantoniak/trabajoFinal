from django.apps import AppConfig


class SolicitudesConfig(AppConfig):
    default_auto_field: str = 'django.db.models.BigAutoField'
    name: str = 'solicitudes'

    def ready(self):
        from . import signals
