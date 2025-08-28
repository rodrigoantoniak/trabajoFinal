from inspect import getfile
from io import BufferedReader
import os

from django.contrib import admin
from django.http import (
    FileResponse,
    HttpRequest
)
from django.views.generic import View


class VistaSelect2JS(View):
    def get(
        self,
        request: HttpRequest
    ) -> FileResponse:
        ruta: str = os.path.join(
            os.path.dirname(getfile(admin)),
            'static/admin/js/vendor/select2/select2.full.min.js'
        )
        archivo: BufferedReader = open(ruta, 'rb')
        return FileResponse(archivo)
