from django.conf import settings
from django.utils.translation import to_locale

from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfdoc import PDFPage
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from babel.dates import format_datetime
from datetime import datetime
from os.path import join
from pathlib import Path
from pytz import timezone
from typing import Self


class CanvasNumerado(Canvas):
    def __init__(self, *args, **kwargs) -> None:
        ruta: str = join(
            Path(__file__).resolve().parent,
            'static/ttf'
        )
        pdfmetrics.registerFont(
            TTFont(
                'Open Sans Light',
                f'{ruta}/OpenSans_SemiCondensed-Light.ttf'
            )
        )
        super().__init__(*args, **kwargs)
        self.paginas: dict[PDFPage] = []

    def showPage(self: Self) -> None:
        self.paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self: Self) -> None:
        cantidad_paginas: int = len(self.paginas)
        ahora: datetime = datetime.now(
            timezone(settings.TIME_ZONE)
        )
        tiempo: str = format_datetime(
            ahora, 'full',
            timezone(settings.TIME_ZONE),
            locale=to_locale(settings.LANGUAGE_CODE)
        )
        for pagina in self.paginas:
            self.__dict__.update(pagina)
            self.dibujar_numero_pagina(
                cantidad_paginas,
                tiempo
            )
            super().showPage()
        super().save()

    def dibujar_numero_pagina(
        self: Self,
        cantidad_pagina: int,
        tiempo: str
    ) -> None:
        pagina: str = 'Página %s de %s' % (self._pageNumber, cantidad_pagina)
        self.setFont('Open Sans Light', 10)
        self.drawString(
            30 * mm, 5 * mm,
            f'Impreso el día {tiempo}'
        )
        self.drawRightString(190 * mm, 5 * mm, pagina)


class Documento(CanvasNumerado):
    def __init__(self, *args, **kwargs) -> None:
        ruta: str = join(
            Path(__file__).resolve().parent,
            'static/ttf'
        )
        pdfmetrics.registerFont(
            TTFont(
                'Nimbus Sans L Regular',
                f'{ruta}/NimbusSanL-Regu.ttf'
            )
        )
        super().__init__(*args, **kwargs)
        self.paginas: dict[PDFPage] = []

    def dibujar_numero_pagina(
        self: Self,
        cantidad_pagina: int,
        tiempo: str
    ) -> None:
        pagina: str = 'Página %s de %s' % (self._pageNumber, cantidad_pagina)
        self.setFont('Nimbus Sans L Regular', 8)
        self.drawString(
            30 * mm, 5 * mm,
            f'Impreso el día {tiempo}'
        )
        self.drawRightString(190 * mm, 5 * mm, pagina)
