from django.urls import (
    include,
    path,
    re_path,
    URLPattern,
    URLResolver
)

from .views import (
    Vista400,
    Vista403,
    Vista404,
    Vista500,
    VistaEstatica
)

from .admin import sitio_gesservorconv

app_name: str = 'administrador'
urlpatterns: list[URLPattern | URLResolver] = [
    re_path(
        r'static/admin/(?P<dir>.*[^\/])$',
        VistaEstatica.as_view()
    ),
    path('', include('favicon.urls')),
    path(
        '',
        include(
            (
                sitio_gesservorconv.get_urls(),
                'admin'
            ),
            'admin'
        )
    ),
]

handler400 = Vista400.as_view()
handler403 = Vista403.as_view()
handler404 = Vista404.as_view()
handler500 = Vista500.as_view()
