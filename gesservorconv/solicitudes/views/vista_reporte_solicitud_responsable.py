from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Permission
from django.conf import settings
from django.db.models import Q, QuerySet
from django.http import (
    FileResponse,
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse
)
from django.urls import reverse_lazy
from django.views.generic import View

from reportlab import rl_config
from reportlab.lib.colors import black
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.paragraph import Paragraph

from io import BytesIO
from os.path import join
from pathlib import Path
from typing import Self

from ..models import (
    SolicitudServicio,
    ComitenteSolicitud,
    ResponsableSolicitud
)

from firmas.models import Convenio, OrdenServicio
from cuentas.models import ResponsableTecnico

from gesservorconv.mixins import (
    MixinAccesoRequerido,
    MixinPermisoRequerido
)
from gesservorconv.report_lab import CanvasNumerado


class VistaReporteSolicitudResponsable(
    MixinAccesoRequerido,
    MixinPermisoRequerido,
    UserPassesTestMixin,
    View
):
    permission_required: QuerySet[Permission] = Permission.objects.filter(
        codename=f'view_{SolicitudServicio.__name__.lower()}'
    )

    def test_func(self: Self) -> bool:
        return ResponsableTecnico.objects.filter(
            Q(usuario_responsable=self.request.user)
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
                "Usted no es un Responsable Técnico."
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
        self,
        request: HttpRequest,
        solicitud: int
    ) -> FileResponse:
        if not SolicitudServicio.objects.filter(
            Q(id_solicitud=solicitud)
        ).exists():
            return JsonResponse(
                status=404,
                data={
                    "error": "No existe la solicitud de servicio",
                },
                headers={
                    "Content-Language": "es-AR"
                }
            )
        if not ResponsableSolicitud.objects.filter(
            Q(responsable_tecnico__usuario_responsable=request.user) &
            Q(solicitud_servicio__id_solicitud=solicitud)
        ).exists():
            return JsonResponse(
                status=403,
                data={
                    "error": "Usted no es Responsable Técnico en este servicio",
                },
                headers={
                    "Content-Language": "es-AR"
                }
            )
        if ResponsableSolicitud.objects.filter(
            Q(responsable_tecnico__usuario_responsable=request.user) &
            Q(solicitud_servicio__id_solicitud=solicitud) &
            Q(tiempo_decision_responsable__isnull=True)
        ).exists():
            return JsonResponse(
                status=401,
                data={
                    "error": "Usted aún no ha decidido sobre si es"
                             " Responsable Técnico o no en esta solicitud de"
                             " servicio",
                },
                headers={
                    "Content-Language": "es-AR"
                }
            )
        if (
            OrdenServicio.objects.filter(
                solicitud_servicio__id_solicitud=solicitud
            ).exists() or
            Convenio.objects.filter(
                solicitud_servicio__id_solicitud=solicitud
            ).exists()
        ):
            return JsonResponse(
                status=418,
                data={
                    "error": "El estado de este servicio ya no es"
                             " de una solicitud",
                },
                headers={
                    "Content-Language": "es-AR"
                }
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
        solicitud_servicio: SolicitudServicio = SolicitudServicio.objects.get(
            id_solicitud=solicitud
        )
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
        parrafo: Paragraph
        fragmentos: list[Paragraph]
        estilo_parrafo: ParagraphStyle
        canvas.setTitle('Solicitud de Servicio')
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
            'Solicitud de Servicio'
        )
        canvas.setFont('Open Sans Bold', 12)
        canvas.drawString(
            30*mm, 257*mm,
            'Identificador:'
        )
        canvas.setFont('Open Sans Medium', 12)
        canvas.drawString(
            60*mm, 257*mm,
            str(solicitud_servicio.id_solicitud)
        )
        y: int = 250
        canvas.setFont('Open Sans Bold', 12)
        canvas.drawString(
            30*mm, y*mm,
            'Nombre:'
        )
        canvas.setFont('Open Sans Medium', 12)
        estilo_parrafo = ParagraphStyle(
            name='estilo',
            fontName='Open Sans Medium',
            bulletFontName='Open Sans Medium',
            fontSize=12,
            leading=14.25,
            firstLineIndent=20*mm,
            leftIndent=30*mm,
            rightIndent=20*mm,
            spaceBefore=20*mm,
            spaceAfter=20*mm
        )
        parrafo = Paragraph(
            solicitud_servicio.nombre_solicitud,
            style=estilo_parrafo
        )
        fragmentos = parrafo.splitOn(canvas, A4[0], A4[1]-(y*mm))
        canvas.drawString(
            50*mm, y*mm,
            ' '.join(
                [
                    palabra
                    for palabra
                    in fragmentos[0].blPara.lines[0][1]
                ]
            )
        )
        y -= 5
        for linea in fragmentos[0].blPara.lines[1:]:
            if y < 20:
                y = 277
                canvas.showPage()
            canvas.drawString(
                30*mm, y*mm,
                ' '.join(
                    [
                        palabra
                        for palabra
                        in linea[1]
                    ]
                )
            )
            y -= 5
        y -= 2
        canvas.setFont('Open Sans Bold', 12)
        canvas.drawString(
            30*mm, y*mm,
            'Descripción:'
        )
        canvas.setFont('Open Sans Medium', 12)
        estilo_parrafo = ParagraphStyle(
            name='estilo',
            fontName='Open Sans Medium',
            bulletFontName='Open Sans Medium',
            fontSize=12,
            leading=14.25,
            firstLineIndent=27*mm,
            leftIndent=30*mm,
            rightIndent=20*mm,
            spaceBefore=20*mm,
            spaceAfter=20*mm
        )
        parrafo = Paragraph(
            solicitud_servicio.descripcion_solicitud,
            style=estilo_parrafo
        )
        fragmentos = parrafo.splitOn(canvas, A4[0], A4[1]-(y*mm))
        canvas.drawString(
            57*mm, y*mm,
            ' '.join(
                [
                    palabra
                    for palabra
                    in fragmentos[0].blPara.lines[0][1]
                ]
            )
        )
        y -= 5
        for linea in fragmentos[0].blPara.lines[1:]:
            if y < 20:
                y = 277
                canvas.showPage()
            canvas.drawString(
                30*mm, y*mm,
                ' '.join(
                    [
                        palabra
                        for palabra
                        in linea[1]
                    ]
                )
            )
            y -= 5
        y -= 2
        comitentes: QuerySet[ComitenteSolicitud] = \
            solicitud_servicio.comitentesolicitud_set.filter(
                aceptacion=True
            )
        if comitentes.exists():
            canvas.setFont('Open Sans Italic', 12)
            canvas.drawCentredString(
                110*mm, y*mm,
                'Comitentes que aceptaron:'
            )
            y -= 6
            canvas.setFont('Open Sans Medium', 12)
            for comitente in comitentes:
                estilo_parrafo = ParagraphStyle(
                    name='estilo',
                    fontName='Open Sans Medium',
                    bulletFontName='Open Sans Medium',
                    fontSize=12,
                    leading=14.25,
                    leftIndent=30*mm,
                    rightIndent=20*mm,
                    spaceBefore=20*mm,
                    spaceAfter=20*mm
                )
                parrafo = Paragraph(
                    f"{comitente.comitente.usuario_comitente.last_name},"
                    f" {comitente.comitente.usuario_comitente.first_name}."
                    f" {comitente.puesto_organizacion_comitente} -"
                    f" {comitente.razon_social_comitente}. CUIT:"
                    f" {comitente.cuit_organizacion_comitente}"
                    if comitente.cuit_organizacion_comitente else
                    f"{comitente.comitente.usuario_comitente.last_name},"
                    f" {comitente.comitente.usuario_comitente.first_name}."
                    f" CUIL: {comitente.comitente.cuil_comitente}"
                    " (persona física)",
                    style=estilo_parrafo
                )
                fragmentos = parrafo.splitOn(canvas, A4[0], A4[1]-(y*mm))
                for linea in fragmentos[0].blPara.lines:
                    if y < 20:
                        y = 277
                        canvas.showPage()
                    canvas.drawString(
                        30*mm, y*mm,
                        ' '.join(
                            [
                                palabra
                                for palabra
                                in linea[1]
                            ]
                        )
                    )
                    y -= 5
                y -= 1
            y -= 1
        comitentes = solicitud_servicio.comitentesolicitud_set.filter(
            tiempo_decision__isnull=True
        )
        if comitentes.exists():
            canvas.setFont('Open Sans Italic', 12)
            canvas.drawCentredString(
                110*mm, y*mm,
                'Comitentes que no decidieron:'
            )
            y -= 6
            canvas.setFont('Open Sans Medium', 12)
            for comitente in comitentes:
                estilo_parrafo = ParagraphStyle(
                    name='estilo',
                    fontName='Open Sans Medium',
                    bulletFontName='Open Sans Medium',
                    fontSize=12,
                    leading=14.25,
                    leftIndent=30*mm,
                    rightIndent=20*mm,
                    spaceBefore=20*mm,
                    spaceAfter=20*mm
                )
                parrafo = Paragraph(
                    f"{comitente.comitente.usuario_comitente.last_name},"
                    f" {comitente.comitente.usuario_comitente.first_name}."
                    f" {comitente.puesto_organizacion_comitente} -"
                    f" {comitente.razon_social_comitente}. CUIT:"
                    f" {comitente.cuit_organizacion_comitente}"
                    if comitente.cuit_organizacion_comitente else
                    f"{comitente.comitente.usuario_comitente.last_name},"
                    f" {comitente.comitente.usuario_comitente.first_name}."
                    f" CUIL: {comitente.comitente.cuil_comitente}"
                    " (persona física)",
                    style=estilo_parrafo
                )
                fragmentos = parrafo.splitOn(canvas, A4[0], A4[1]-(y*mm))
                for linea in fragmentos[0].blPara.lines:
                    if y < 20:
                        y = 277
                        canvas.showPage()
                    canvas.drawString(
                        30*mm, y*mm,
                        ' '.join(
                            [
                                palabra
                                for palabra
                                in linea[1]
                            ]
                        )
                    )
                    y -= 5
                y -= 1
            y -= 1
        comitentes = solicitud_servicio.comitentesolicitud_set.filter(
            tiempo_decision__isnull=False, aceptacion=False
        )
        if comitentes.exists():
            canvas.setFont('Open Sans Italic', 12)
            canvas.drawCentredString(
                110*mm, y*mm,
                'Comitentes que rechazaron:'
            )
            y -= 6
            canvas.setFont('Open Sans Medium', 12)
            for comitente in comitentes:
                estilo_parrafo = ParagraphStyle(
                    name='estilo',
                    fontName='Open Sans Medium',
                    bulletFontName='Open Sans Medium',
                    fontSize=12,
                    leading=14.25,
                    leftIndent=30*mm,
                    rightIndent=20*mm,
                    spaceBefore=20*mm,
                    spaceAfter=20*mm
                )
                parrafo = Paragraph(
                    f"{comitente.comitente.usuario_comitente.last_name},"
                    f" {comitente.comitente.usuario_comitente.first_name}."
                    f" {comitente.puesto_organizacion_comitente} -"
                    f" {comitente.razon_social_comitente}. CUIT:"
                    f" {comitente.cuit_organizacion_comitente}"
                    if comitente.cuit_organizacion_comitente else
                    f"{comitente.comitente.usuario_comitente.last_name},"
                    f" {comitente.comitente.usuario_comitente.first_name}."
                    f" CUIL: {comitente.comitente.cuil_comitente}"
                    " (persona física)",
                    style=estilo_parrafo
                )
                fragmentos = parrafo.splitOn(canvas, A4[0], A4[1]-(y*mm))
                for linea in fragmentos[0].blPara.lines:
                    if y < 20:
                        y = 277
                        canvas.showPage()
                    canvas.drawString(
                        30*mm, y*mm,
                        ' '.join(
                            [
                                palabra
                                for palabra
                                in linea[1]
                            ]
                        )
                    )
                    y -= 5
                y -= 1
            y -= 1
        responsables: QuerySet[ResponsableSolicitud] = \
            solicitud_servicio.responsablesolicitud_set.filter(
                Q(aceptacion_responsable=True) &
                Q(aceptacion_comitente=True)
            )
        if responsables.exists():
            canvas.setFont('Open Sans Italic', 12)
            canvas.drawCentredString(
                110*mm, y*mm,
                'Responsables Técnicos aceptados:'
            )
            y -= 6
            canvas.setFont('Open Sans Medium', 12)
            for responsable in responsables:
                estilo_parrafo = ParagraphStyle(
                    name='estilo',
                    fontName='Open Sans Medium',
                    bulletFontName='Open Sans Medium',
                    fontSize=12,
                    leading=14.25,
                    leftIndent=30*mm,
                    rightIndent=20*mm,
                    spaceBefore=20*mm,
                    spaceAfter=20*mm
                )
                parrafo = Paragraph(
                    f"{responsable.responsable_tecnico.usuario_responsable.last_name},"
                    f" {responsable.responsable_tecnico.usuario_responsable.first_name}."
                    f" {responsable.puesto_organizacion_responsable} -"
                    f" {responsable.razon_social_responsable}. CUIT:"
                    f" {responsable.cuit_organizacion_responsable}"
                    if responsable.cuit_organizacion_responsable else
                    f"{responsable.responsable_tecnico.usuario_responsable.last_name},"
                    f" {responsable.responsable_tecnico.usuario_responsable.first_name}."
                    f" CUIL: {responsable.responsable_tecnico.cuil_responsable}"
                    " (persona física)",
                    style=estilo_parrafo
                )
                fragmentos = parrafo.splitOn(canvas, A4[0], A4[1]-(y*mm))
                for linea in fragmentos[0].blPara.lines:
                    if y < 20:
                        y = 277
                        canvas.showPage()
                    canvas.drawString(
                        30*mm, y*mm,
                        ' '.join(
                            [
                                palabra
                                for palabra
                                in linea[1]
                            ]
                        )
                    )
                    y -= 5
                y -= 1
            y -= 1
        responsables = solicitud_servicio.responsablesolicitud_set.filter(
            Q(aceptacion_responsable=True) &
            Q(tiempo_decision_comitente__isnull=True)
        )
        if responsables.exists():
            canvas.setFont('Open Sans Italic', 12)
            canvas.drawCentredString(
                110*mm, y*mm,
                'Responsables Técnicos que aún no son aceptados:'
            )
            y -= 6
            canvas.setFont('Open Sans Medium', 12)
            for responsable in responsables:
                estilo_parrafo = ParagraphStyle(
                    name='estilo',
                    fontName='Open Sans Medium',
                    bulletFontName='Open Sans Medium',
                    fontSize=12,
                    leading=14.25,
                    leftIndent=30*mm,
                    rightIndent=20*mm,
                    spaceBefore=20*mm,
                    spaceAfter=20*mm
                )
                parrafo = Paragraph(
                    f"{responsable.responsable_tecnico.usuario_responsable.last_name},"
                    f" {responsable.responsable_tecnico.usuario_responsable.first_name}."
                    f" {responsable.puesto_organizacion_responsable} -"
                    f" {responsable.razon_social_responsable}. CUIT:"
                    f" {responsable.cuit_organizacion_responsable}"
                    if responsable.cuit_organizacion_responsable else
                    f"{responsable.responsable_tecnico.usuario_responsable.last_name},"
                    f" {responsable.responsable_tecnico.usuario_responsable.first_name}."
                    f" CUIL: {responsable.responsable_tecnico.cuil_responsable}"
                    " (persona física)",
                    style=estilo_parrafo
                )
                fragmentos = parrafo.splitOn(canvas, A4[0], A4[1]-(y*mm))
                for linea in fragmentos[0].blPara.lines:
                    if y < 20:
                        y = 277
                        canvas.showPage()
                    canvas.drawString(
                        30*mm, y*mm,
                        ' '.join(
                            [
                                palabra
                                for palabra
                                in linea[1]
                            ]
                        )
                    )
                    y -= 5
                y -= 1
            y -= 1
        responsables = solicitud_servicio.responsablesolicitud_set.filter(
            Q(tiempo_decision_responsable__isnull=True) &
            Q(aceptacion_comitente=True)
        )
        if responsables.exists():
            canvas.setFont('Open Sans Italic', 12)
            canvas.drawCentredString(
                110*mm, y*mm,
                'Responsables Técnicos que aún no aceptaron:'
            )
            y -= 6
            canvas.setFont('Open Sans Medium', 12)
            for responsable in responsables:
                estilo_parrafo = ParagraphStyle(
                    name='estilo',
                    fontName='Open Sans Medium',
                    bulletFontName='Open Sans Medium',
                    fontSize=12,
                    leading=14.25,
                    leftIndent=30*mm,
                    rightIndent=20*mm,
                    spaceBefore=20*mm,
                    spaceAfter=20*mm
                )
                parrafo = Paragraph(
                    f"{responsable.responsable_tecnico.usuario_responsable.last_name},"
                    f" {responsable.responsable_tecnico.usuario_responsable.first_name}."
                    f" {responsable.puesto_organizacion_responsable} -"
                    f" {responsable.razon_social_responsable}. CUIT:"
                    f" {responsable.cuit_organizacion_responsable}"
                    if responsable.cuit_organizacion_responsable else
                    f"{responsable.responsable_tecnico.usuario_responsable.last_name},"
                    f" {responsable.responsable_tecnico.usuario_responsable.first_name}."
                    f" CUIL: {responsable.responsable_tecnico.cuil_responsable}"
                    " (persona física)",
                    style=estilo_parrafo
                )
                fragmentos = parrafo.splitOn(canvas, A4[0], A4[1]-(y*mm))
                for linea in fragmentos[0].blPara.lines:
                    if y < 20:
                        y = 277
                        canvas.showPage()
                    canvas.drawString(
                        30*mm, y*mm,
                        ' '.join(
                            [
                                palabra
                                for palabra
                                in linea[1]
                            ]
                        )
                    )
                    y -= 5
                y -= 1
            y -= 1
        canvas.showPage()
        canvas.save()
        buffer.seek(0)
        return FileResponse(
            buffer,
            filename=f'solicitudServicio{solicitud}.pdf'
        )
