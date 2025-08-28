from django.core.checks import Error, register


@register()
def check_dafne_installed(app_configs, **kwargs):
    from django.apps import apps
    from django.contrib.staticfiles.apps import StaticFilesConfig

    from .apps import DafneConfig

    for app in apps.get_app_configs():
        if isinstance(app, DafneConfig):
            return []
        if isinstance(app, StaticFilesConfig):
            return [
                Error(
                    "Dafne must be listed before django.contrib.staticfiles"
                    " in INSTALLED_APPS.",
                    id="dafne.E001",
                )
            ]
