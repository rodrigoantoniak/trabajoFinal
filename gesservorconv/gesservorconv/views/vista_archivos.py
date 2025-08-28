from inspect import getfile
from io import BufferedReader
import os
from pathlib import Path

from django.contrib import admin
from django.core.exceptions import BadRequest
from django.http import (
    FileResponse,
    Http404,
    HttpRequest
)
from django.views.generic import View


class VistaArchivos(View):
    def get(
        self,
        request: HttpRequest,
        dir: str
    ) -> FileResponse:
        ruta: str = os.path.join(
            Path(__file__).resolve().parent.parent,
            f'media/{dir}'
        )
        if os.path.isfile(ruta):
            try:
                archivo: BufferedReader = open(ruta, 'rb')
                return FileResponse(archivo)
            except OSError:
                raise Http404(
                    'El archivo no pudo ser cargado'
                )
        raise BadRequest('El archivo no existe')
