from inspect import getfile
from io import BufferedReader
import os

from django.contrib import admin
from django.http import (
    FileResponse,
    HttpRequest
)
from django.views.generic import View


class VistaJQuery(View):
    def get(
        self,
        request: HttpRequest
    ) -> FileResponse:
        ruta: str = os.path.join(
            os.path.dirname(getfile(admin)),
            'static/admin/js/vendor/jquery/jquery.min.js'
        )
        archivo: BufferedReader = open(ruta, 'rb')
        return FileResponse(archivo)
