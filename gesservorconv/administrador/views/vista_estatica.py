from inspect import getfile
from io import BufferedReader
import os

from django.contrib import admin
from django.core.exceptions import BadRequest
from django.http import (
    FileResponse,
    Http404,
    HttpRequest
)
from django.views.generic import View


class VistaEstatica(View):
    def get(
        self,
        request: HttpRequest,
        dir: str
    ) -> FileResponse:
        ruta: str = os.path.join(
            os.path.dirname(getfile(admin)),
            f'static/admin/{dir}'
        )
        if os.path.isfile(ruta):
            try:
                archivo: BufferedReader = open(ruta, 'rb')
                return FileResponse(archivo)
            except OSError:
                raise Http404(
                    'El elemento estático no pudo ser cargado'
                )
        raise BadRequest('El elemento estático no existe')
