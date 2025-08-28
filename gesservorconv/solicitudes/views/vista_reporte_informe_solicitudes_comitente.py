from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Permission
from django.db.models import Case, CharField, Min, Q, QuerySet, Value, When
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseRedirect
)
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import to_locale
from django.views.decorators.cache import cache_control
from django.views.generic import View

from reportlab import rl_config
from reportlab.lib.colors import black
from reportlab.lib.enums import (
    TA_LEFT,
    TA_CENTER,
    TA_RIGHT
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.tables import LongTable

from babel.dates import format_datetime
from datetime import datetime, timezone
from io import BytesIO
from os.path import join
from pathlib import Path
import pytz
from typing import Optional, Self

from ..models import (
    SolicitudServicio,
    ComitenteSolicitud
)

from firmas.models import Convenio, OrdenServicio
from cuentas.models import Comitente

from gesservorconv.mixins import (
    MixinAccesoRequerido,
    MixinPermisoRequerido
)
from gesservorconv.report_lab import CanvasNumerado
from gesservorconv.views import HtmxHttpRequest


@method_decorator(cache_control(private=True, max_age=60), 'dispatch')
class VistaReporteInformeSolicitudesComitente(
    MixinAccesoRequerido,
    MixinPermisoRequerido,
    UserPassesTestMixin,
    View
):
    permission_required: QuerySet[Permission] = Permission.objects.filter(
        codename=f'view_{SolicitudServicio.__name__.lower()}'
    )

    def test_func(self: Self) -> bool:
        return Comitente.objects.filter(
            Q(usuario_comitente=self.request.user)
        ).exists()

    def handle_no_permission(self: Self) -> HttpResponse:
        if self.request.user.is_anonymous:
            messages.warning(
                self.request,
                ("La sesión ha caducado")
            )
            direccion: str = (
                reverse_lazy("cuentas:iniciar_sesion") +
                "?siguiente=" + self.request.path
            )
            if self.request.htmx:
                return HttpResponse(
                    self.request.get_full_path(),
                    headers={
                        "HX-Redirect": direccion
                    }
                )
            return HttpResponseRedirect(direccion)
        if self.request.user.is_staff or self.request.user.is_superuser:
            logout(self.request)
            messages.error(
                self.request,
                (
                    "El usuario %(nombre)s no tiene permiso a"
                    " esta página. Por ello, se ha cerrado"
                    " la sesión."
                ) % {
                    "nombre": self.request.user.username
                }
            )
            return HttpResponseRedirect(
                reverse_lazy("cuentas:iniciar_sesion")
            )
        if self.has_permission():
            messages.error(
                self.request,
                "Usted no es un Comitente."
            )
        else:
            messages.error(
                self.request,
                "Usted no tiene los permisos para acceder"
                " a esta página."
            )
        return HttpResponseRedirect(
            reverse_lazy('cuentas:perfil')
        )

    def get(
        self: Self,
        request: HtmxHttpRequest
    ) -> FileResponse:
        estados = {
            'completo': 'Completo',
            'curso': 'En curso',
            'suspendido': 'Suspendido',
            'cancelado': 'Cancelado'
        }
        estado: str = request.GET.get(
            "estado", "completo"
        )
        buscar_fecha_inicio: Optional[str] = request.GET.get(
            "buscar_fecha_inicio"
        )
        buscar_hora_inicio: Optional[str] = request.GET.get(
            "buscar_hora_inicio"
        )
        buscar_fecha_fin: Optional[str] = request.GET.get(
            "buscar_fecha_fin"
        )
        buscar_hora_fin: Optional[str] = request.GET.get(
            "buscar_hora_fin"
        )
        tiempo_inicio: datetime = (
            datetime.strptime(
                f"{buscar_fecha_inicio} {buscar_hora_inicio}",
                "%Y-%m-%d %H:%M"
            )
            if buscar_fecha_inicio and buscar_hora_inicio
            else datetime.fromtimestamp(0, timezone.utc)
        )
        tiempo_fin: datetime = (
            datetime.strptime(
                f"{buscar_fecha_fin} {buscar_hora_fin}",
                "%Y-%m-%d %H:%M"
            )
            if buscar_fecha_fin and buscar_hora_fin
            else datetime.now(timezone.utc)
        )
        solicitudes_servicio: QuerySet[SolicitudServicio] = \
            SolicitudServicio.objects.filter(
                pk__in=ComitenteSolicitud.objects.filter(
                    comitente__usuario_comitente=self.request.user
                ).values_list(
                    "solicitud_servicio", flat=True
                )
            ).annotate(
                tiempo_creacion=Min(
                    "comitentesolicitud__tiempo_decision",
                    filter=Q(
                        comitentesolicitud__tiempo_decision__isnull=False
                    )
                )
            ).filter(
                Q(
                    tiempo_creacion__gte=tiempo_inicio.replace(
                        tzinfo=timezone.utc
                    ).isoformat()
                ) &
                Q(
                    tiempo_creacion__lte=tiempo_fin.replace(
                        tzinfo=timezone.utc
                    ).isoformat()
                )
            ).annotate(
                estado=Case(
                    When(
                        Q(
                            pk__in=OrdenServicio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ) |
                        Q(
                            pk__in=Convenio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ),
                        then=Value(list(estados.keys())[0], CharField())
                    ),
                    When(
                        ~Q(
                            pk__in=OrdenServicio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ) &
                        ~Q(
                            pk__in=Convenio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ) &
                        Q(
                            cancelacion_solicitud__isnull=True
                        ) & (
                            Q(
                                solicitud_suspendida__isnull=True
                            ) |
                            Q(
                                solicitud_suspendida=False
                            )
                        ),
                        then=Value(list(estados.keys())[1], CharField())
                    ),
                    When(
                        ~Q(
                            pk__in=OrdenServicio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ) &
                        ~Q(
                            pk__in=Convenio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ) &
                        Q(
                            cancelacion_solicitud__isnull=True
                        ) &
                        Q(
                            solicitud_suspendida__isnull=False
                        ) &
                        Q(
                            solicitud_suspendida=True
                        ),
                        then=Value(list(estados.keys())[2], CharField())
                    ),
                    When(
                        ~Q(
                            pk__in=OrdenServicio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ) &
                        ~Q(
                            pk__in=Convenio.objects.values_list(
                                "solicitud_servicio__id_solicitud", flat=True
                            )
                        ) &
                        Q(
                            cancelacion_solicitud__isnull=False
                        ),
                        then=Value(list(estados.keys())[3], CharField())
                    ),
                    output_field=CharField()
                )
            )
        if estado is not None:
            solicitudes_servicio = solicitudes_servicio.filter(
                estado=estado
            )
        ruta: str = join(
            Path(__file__).resolve().parent.parent.parent,
            'gesservorconv/static/ttf'
        )
        pdfmetrics.registerFont(
            TTFont(
                'Tangerine',
                f'{ruta}/Tangerine.ttf'
            )
        )
        pdfmetrics.registerFont(
            TTFont(
                'Basic',
                f'{ruta}/Basic.ttf'
            )
        )
        pdfmetrics.registerFont(
            TTFont(
                'Open Sans Medium',
                f'{ruta}/OpenSans-Medium.ttf'
            )
        )
        pdfmetrics.registerFont(
            TTFont(
                'Open Sans Italic',
                f'{ruta}/OpenSans_SemiCondensed-ExtraBoldItalic.ttf'
            )
        )
        pdfmetrics.registerFont(
            TTFont(
                'Open Sans Bold',
                f'{ruta}/OpenSans-Bold.ttf'
            )
        )
        rl_config.warnOnMissingFontGlyphs = 0
        buffer: BytesIO = BytesIO()
        canvas: CanvasNumerado = CanvasNumerado(
            buffer,
            pagesize=A4,
            bottomup=1,
            pageCompression=1,
            pdfVersion=(2, 0),
            initialFontName='Open Sans Medium',
            initialFontSize=12,
            lang=settings.LANGUAGE_CODE
        )
        estilo_parrafo: ParagraphStyle
        canvas.setTitle('Solicitudes de Servicio')
        canvas.setFont('Tangerine', 28)
        # Color primario de Bootstrap
        canvas.setFillColorRGB(
            0.05078125,
            0.4296875,
            0.98828125
        )
        canvas.drawCentredString(
            110*mm, 277*mm,
            'GesServOrConv'
        )
        canvas.setFont('Basic', 18)
        canvas.setFillColor(black)
        canvas.drawCentredString(
            110*mm, 267*mm,
            'Solicitudes de Servicio'
        )
        canvas.setFont('Open Sans Bold', 12)
        canvas.drawString(
            30*mm, 262*mm,
            'Estado:'
        )
        canvas.setFont('Open Sans Medium', 12)
        canvas.drawString(
            47*mm, 262*mm,
            estados[estado] if estado else 'Todos incluidos'
        )
        canvas.setFont('Open Sans Bold', 12)
        canvas.drawString(
            30*mm, 257*mm,
            'Desde:'
        )
        canvas.setFont('Open Sans Medium', 12)
        canvas.drawString(
            46*mm, 257*mm,
            format_datetime(
                tiempo_inicio, 'long',
                pytz.timezone(settings.TIME_ZONE),
                locale=to_locale(settings.LANGUAGE_CODE)
            )
        )
        canvas.setFont('Open Sans Bold', 12)
        canvas.drawString(
            30*mm, 252*mm,
            'Hasta:'
        )
        canvas.setFont('Open Sans Medium', 12)
        canvas.drawString(
            45*mm, 252*mm,
            format_datetime(
                tiempo_fin, 'long',
                pytz.timezone(settings.TIME_ZONE),
                locale=to_locale(settings.LANGUAGE_CODE)
            )
        )
        estilo_identificador = ParagraphStyle(
            name='identificador',
            fontName='Open Sans Italic',
            bulletFontName='Open Sans Italic',
            alignment=TA_CENTER,
            fontSize=12,
            leading=14.25
        )
        estilo_encabezado = ParagraphStyle(
            name='encabezado',
            fontName='Open Sans Bold',
            bulletFontName='Open Sans Bold',
            alignment=TA_CENTER,
            fontSize=12,
            leading=14.25
        )
        estilo_numero = ParagraphStyle(
            name='numero',
            fontName='Open Sans Medium',
            bulletFontName='Open Sans Medium',
            alignment=TA_RIGHT,
            fontSize=12,
            leading=14.25
        )
        estilo_parrafo = ParagraphStyle(
            name='estilo',
            fontName='Open Sans Medium',
            bulletFontName='Open Sans Medium',
            alignment=TA_LEFT,
            fontSize=12,
            leading=14.25
        )
        tabla: LongTable = LongTable(
            [
                [
                    Paragraph(
                        'Id.',
                        style=estilo_identificador
                    ),
                    Paragraph(
                        'Nombre',
                        style=estilo_encabezado
                    ),
                    Paragraph(
                        'Creación',
                        style=estilo_encabezado
                    )
                ]
            ] + [
                [
                    Paragraph(
                        str(solicitud.id_solicitud),
                        style=estilo_numero
                    ),
                    Paragraph(
                        solicitud.nombre_solicitud,
                        style=estilo_parrafo
                    ),
                    Paragraph(
                        format_datetime(
                            solicitud.tiempo_creacion, 'short',
                            pytz.timezone(settings.TIME_ZONE),
                            locale=to_locale(settings.LANGUAGE_CODE)
                        ),
                        style=estilo_parrafo
                    )
                ]
                for solicitud in solicitudes_servicio
            ],
            colWidths=(
                [30*mm, 80*mm, 50*mm]
            ),
            repeatRows=1
        )
        partes: list[LongTable] = tabla.splitOn(canvas, 160*mm, 185*mm)
        if len(partes) == 0:
            canvas.setFont('Open Sans Medium', 12)
            canvas.drawCentredString(
                110*mm, 247*mm,
                'No hay solicitudes de servicio'
            )
            canvas.showPage()
        else:
            y: int
            partes[0].setStyle(
                [
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, black),
                    ('BOX', (0, 0), (-1, -1), 2, black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LINEBELOW', (0, 0), (-1, 0), 1.5, black),
                    ('LINEAFTER', (0, 0), (0, -1), 1, black),
                ]
            )
            (_, y) = partes[0].wrapOn(canvas, 160*mm, 185*mm)
            partes[0].drawOn(canvas, 30*mm, (247*mm)-y)
            canvas.showPage()
            while len(partes) == 2:
                partes = partes[1].splitOn(canvas, 160*mm, 257*mm)
                partes[0].setStyle(
                    [
                        ('INNERGRID', (0, 0), (-1, -1), 0.5, black),
                        ('BOX', (0, 0), (-1, -1), 2, black),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('LINEBELOW', (0, 0), (-1, 0), 1.5, black),
                        ('LINEAFTER', (0, 0), (0, -1), 1, black),
                    ]
                )
                (_, y) = partes[0].wrapOn(canvas, 160*mm, 257*mm)
                partes[0].drawOn(canvas, 30*mm, (277*mm)-y)
                canvas.showPage()
        canvas.save()
        buffer.seek(0)
        return FileResponse(
            buffer,
            filename='solicitudesServicio.pdf'
        )
