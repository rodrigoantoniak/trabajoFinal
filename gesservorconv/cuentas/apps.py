from django.apps import AppConfig


class CuentasConfig(AppConfig):
    name: str = 'cuentas'

    def ready(self):
        from . import signals
