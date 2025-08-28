from io import BufferedReader
import os

from django.conf import settings
from django.http import (
    FileResponse,
    Http404,
    HttpRequest
)
from django.views.generic import View


class VistaIco(View):
    def get(self, request: HttpRequest) -> FileResponse:
        try:
            ico: BufferedReader = open(
                os.path.join(
                    settings.BASE_DIR,
                    'gesservorconv/templates/img/favicon.ico'
                ),
                'rb'
            )
            return FileResponse(
                ico,
                headers={
                    'Content-Language': 'es-AR'
                }
            )
        except OSError:
            raise Http404('No existe favicon.ico')
