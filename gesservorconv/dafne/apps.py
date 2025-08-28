from django.apps import AppConfig
from django.core import checks

from . import server

from .checks import check_dafne_installed


class DafneConfig(AppConfig):
    name = 'dafne'
    verbose_name = "Dafne"

    def ready(self):
        checks.register(check_dafne_installed, checks.Tags.staticfiles)
