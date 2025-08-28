from django.contrib import admin
from django.urls.resolvers import URLResolver

from typing import Self

from .models import Configuracion


admin.site.register(Configuracion)


class AdminGesServOrConv(admin.AdminSite):
    site_title = "Sitio de administración de GesServOrConv"

    site_header = "Administración de GesServOrConv"

    index_title = "Sitio de administración"

    # Esta propiedad solamente sirve para reforzar lo esperado de la clase
    final_catch_all_view: bool = False

    def get_urls(self: Self) -> list[URLResolver]:
        urls: list[URLResolver] = admin.site.get_urls()
        '''
        Esto borra catch_all_view, así dispara error 404
        del proyecto. Es la forma más rápida
        '''
        urls.pop()
        return urls


admin.site.site_title = "Sitio de administración de GesServOrConv"

admin.site.site_header = "Administración de GesServOrConv"

admin.site.index_title = "Sitio de administración"


sitio_gesservorconv: AdminGesServOrConv = AdminGesServOrConv(
    name='adminGesServOrConv'
)
