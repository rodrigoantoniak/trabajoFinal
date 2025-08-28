from django.urls import URLPattern, path

from . import views

app_name: str = 'favicon'
urlpatterns: list[URLPattern] = [
    path(
        'favicon.ico',
        views.VistaIco.as_view(),
        name='ico'
    ),
]
