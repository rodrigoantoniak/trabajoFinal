from inspect import getfile
from io import BufferedReader
import os

from django.contrib import admin
from django.http import (
    FileResponse,
    HttpRequest
)
from django.views.generic import View


class VistaSelect2CSS(View):
    def get(
        self,
        request: HttpRequest
    ) -> FileResponse:
        ruta: str = os.path.join(
            os.path.dirname(getfile(admin)),
            'static/admin/css/vendor/select2/select2.min.css'
        )
        archivo: BufferedReader = open(ruta, 'rb')
        return FileResponse(archivo)
