from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Permission
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.functions import TransactionNow
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import (
    Case, CharField, DecimalField, F, Min, Model, Q, QuerySet, Value, When
)
from django.db.models.functions import Cast, Concat
from django.http import (
    FileResponse,
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse
)
from django.urls import reverse_lazy
from django.utils.translation import to_locale
from django.views.generic import View

import reportlab
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.paragraph import Paragraph

from babel.numbers import format_decimal
from datetime import datetime
from io import BytesIO
from os.path import join
from pathlib import Path
from pytz import timezone
from typing import Self

from ..models import FirmaOrden, OrdenServicio

from solicitudes.models import (
    PropuestaCompromisos,
    ResponsableSolicitud
)
from cuentas.models import Comitente, ResponsableTecnico, Secretario

from gesservorconv.mixins import (
    MixinAccesoRequerido,
    MixinPermisoRequerido
)
from gesservorconv.report_lab import Documento


class VistaOrdenServicio(
    MixinAccesoRequerido,
    UserPassesTestMixin,
    View
):
    def test_func(self: Self) -> bool:
        return self.request.user.groups.filter(
            name="ayudante"
        )

    def handle_no_permission(self: Self) -> HttpResponse:
        if self.request.user.is_anonymous:
            messages.warning(
                self.request,
                "La sesión ha caducado"
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
        messages.error(
            self.request,
            "Usted no está a cargo de la Secretaría."
        )
        return HttpResponseRedirect(
            reverse_lazy('cuentas:perfil')
        )

    def get(
        self,
        request: HttpRequest,
        orden: int
    ) -> FileResponse:
        ruta: str = join(
            Path(__file__).resolve().parent.parent.parent,
            'gesservorconv/static/ttf'
        )
        pdfmetrics.registerFont(
            TTFont(
                'Nimbus Roman No9 L Regular',
                f'{ruta}/NimbusRomNo9L-Regu.ttf'
            )
        )
        pdfmetrics.registerFont(
            TTFont(
                'Nimbus Roman No9 L Bold',
                f'{ruta}/NimbusRomNo9L-Medi.ttf'
            )
        )
        pdfmetrics.registerFont(
            TTFont(
                'Nimbus Roman No9 L Italic',
                f'{ruta}/NimbusRomNo9L-ReguItal.ttf'
            )
        )
        pdfmetrics.registerFont(
            TTFont(
                'Nimbus Roman No9 L Bold Italic',
                f'{ruta}/NimbusRomNo9L-MediItal.ttf'
            )
        )
        pdfmetrics.registerFontFamily(
            'Nimbus Roman No9 L',
            normal='Nimbus Roman No9 L Regular',
            bold='Nimbus Roman No9 L Bold',
            italic='Nimbus Roman No9 L Italic',
            boldItalic='Nimbus Roman No9 L Bold Italic'
        )
        reportlab.rl_config.warnOnMissingFontGlyphs = 0
        ordenes_servicio: QuerySet[OrdenServicio] = \
            OrdenServicio.objects.filter(
                solicitud_servicio__id_solicitud=orden
            ).annotate(
                compromisos_comitente=Cast(
                    PropuestaCompromisos.objects.get(
                        solicitud_servicio_propuesta=orden,
                        es_valida_propuesta=True
                    ).descripciones_compromisos_comitente,
                    output_field=ArrayField(CharField())
                )
            ).annotate(
                compromisos_unidad_ejecutora=Cast(
                    PropuestaCompromisos.objects.get(
                        solicitud_servicio_propuesta=orden,
                        es_valida_propuesta=True
                    ).descripciones_compromisos_unidad_ejecutora,
                    output_field=ArrayField(CharField())
                )
            ).annotate(
                retribuciones_economicas=Cast(
                    PropuestaCompromisos.objects.get(
                        solicitud_servicio_propuesta=orden,
                        es_valida_propuesta=True
                    ).descripciones_retribuciones_economicas,
                    output_field=ArrayField(CharField())
                )
            ).annotate(
                montos=Cast(
                    PropuestaCompromisos.objects.get(
                        solicitud_servicio_propuesta=orden,
                        es_valida_propuesta=True
                    ).montos_retribuciones_economicas,
                    output_field=ArrayField(
                        DecimalField(
                            max_digits=16,
                            decimal_places=2
                        )
                    )
                )
            ).annotate(
                comitentes_en_solicitud=ArrayAgg(
                    Case(
                        When(
                            Q(
                                solicitud_servicio__comitentesolicitud__cuit_organizacion_comitente__isnull=True
                            ),
                            then=Concat(
                                F("solicitud_servicio__comitentesolicitud__comitente__usuario_comitente__last_name"),
                                Value(", "),
                                F("solicitud_servicio__comitentesolicitud__comitente__usuario_comitente__first_name"),
                                Value(". CUIL: "),
                                Cast(
                                    "solicitud_servicio__comitentesolicitud__comitente__cuil_comitente",
                                    output_field=CharField()
                                ),
                                Value(" (persona física)")
                            )
                        ),
                        When(
                            Q(
                                solicitud_servicio__comitentesolicitud__cuit_organizacion_comitente__isnull=False
                            ),
                            then=Concat(
                                F("solicitud_servicio__comitentesolicitud__comitente__usuario_comitente__last_name"),
                                Value(", "),
                                F("solicitud_servicio__comitentesolicitud__comitente__usuario_comitente__first_name"),
                                Value(". "),
                                F("solicitud_servicio__comitentesolicitud__puesto_organizacion_comitente"),
                                Value(" - "),
                                F("solicitud_servicio__comitentesolicitud__razon_social_comitente"),
                                Value(". CUIT: "),
                                Cast(
                                    "solicitud_servicio__comitentesolicitud__cuit_organizacion_comitente",
                                    output_field=CharField()
                                )
                            )
                        ),
                        default=None
                    ),
                    distinct=True,
                    default=Value([])
                )
            ).annotate(
                responsables_en_solicitud=ArrayAgg(
                    Case(
                        When(
                            ~Q(
                                pk__in=ResponsableSolicitud.objects.filter(
                                    (
                                        Q(
                                            tiempo_decision_responsable__isnull=True
                                        ) &
                                        (
                                            Q(
                                                tiempo_decision_comitente__isnull=True
                                            ) |
                                            Q(
                                                aceptacion_comitente=True
                                            )
                                        )
                                    ) |
                                    (
                                        Q(
                                            tiempo_decision_comitente__isnull=True
                                        ) &
                                        (
                                            Q(
                                                tiempo_decision_responsable__isnull=True
                                            ) |
                                            Q(
                                                aceptacion_responsable=True
                                            )
                                        )
                                    )
                                ).values_list(
                                    "solicitud_servicio", flat=True
                                )
                            ),
                            then=Concat(
                                F("solicitud_servicio__responsablesolicitud__responsable_tecnico__usuario_responsable__last_name"),
                                Value(", "),
                                F("solicitud_servicio__responsablesolicitud__responsable_tecnico__usuario_responsable__first_name"),
                                Value(". CUIL: "),
                                Cast(
                                    "solicitud_servicio__responsablesolicitud__responsable_tecnico__cuil_responsable",
                                    output_field=CharField()
                                ),
                                Value(" (persona física)")
                            )
                        ),
                        When(
                            ~Q(
                                pk__in=ResponsableSolicitud.objects.filter(
                                    (
                                        Q(
                                            tiempo_decision_responsable__isnull=True
                                        ) &
                                        (
                                            Q(
                                                tiempo_decision_comitente__isnull=True
                                            ) |
                                            Q(
                                                aceptacion_comitente=True
                                            )
                                        )
                                    ) |
                                    (
                                        Q(
                                            tiempo_decision_comitente__isnull=True
                                        ) &
                                        (
                                            Q(
                                                tiempo_decision_responsable__isnull=True
                                            ) |
                                            Q(
                                                aceptacion_responsable=True
                                            )
                                        )
                                    )
                                ).values_list(
                                    "solicitud_servicio", flat=True
                                )
                            ),
                            then=Concat(
                                F("solicitud_servicio__responsablesolicitud__responsable_tecnico__usuario_responsable__last_name"),
                                Value(", "),
                                F("solicitud_servicio__responsablesolicitud__responsable_tecnico__usuario_responsable__first_name"),
                                Value(". "),
                                F("solicitud_servicio__responsablesolicitud__puesto_organizacion_responsable"),
                                Value(" - "),
                                F("solicitud_servicio__responsablesolicitud__razon_social_responsable"),
                                Value(". CUIT: "),
                                Cast(
                                    "solicitud_servicio__responsablesolicitud__cuit_organizacion_responsable",
                                    output_field=CharField()
                                )
                            )
                        ),
                        default=None
                    ),
                    distinct=True,
                    default=Value([])
                )
            )
        # Si no corresponde, volver a lista de ordenes y
        # notificar el error adecuadamente
        orden_servicio: OrdenServicio = ordenes_servicio.first()
        buffer: BytesIO = BytesIO()
        canvas: Documento = Documento(
            buffer,
            pagesize=A4,
            bottomup=1,
            pageCompression=1,
            pdfVersion=(2, 0),
            initialFontName='Nimbus Roman No9 L Regular',
            initialFontSize=12,
            lang=settings.LANGUAGE_CODE
        )
        canvas.setTitle('Orden de Servicio')
        canvas.setFont('Nimbus Roman No9 L Bold Italic', 14)
        canvas.drawCentredString(
            110*mm, 277*mm,
            'ORDEN DE SERVICIOS'
        )
        canvas.setFont('Nimbus Roman No9 L Bold', 12)
        canvas.drawString(
            30*mm, 272*mm,
            f'ORDEN DE SERVICIO N° {orden_servicio.solicitud_servicio.id_solicitud}'
        )
        canvas.setFont('Nimbus Roman No9 L Regular', 12)
        canvas.drawString(
            30*mm, 268*mm,
            '(2 copias)'
        )
        y: float
        parrafo: Paragraph
        fragmentos: list[Paragraph]
        estilo_parrafo: ParagraphStyle = ParagraphStyle(
            name='titulos',
            fontName='Nimbus Roman No9 L Regular',
            fontSize=12,
            leading=14.25,
            leftIndent=30*mm,
            rightIndent=20*mm,
            alignment=TA_JUSTIFY
        )
        parrafo = Paragraph(
            "La Facultad de Ciencias Exactas, Químicas y Naturales"
            " se compromete a prestar el Servicio Técnico llamado <i>"
            f"{orden_servicio.solicitud_servicio.nombre_solicitud}"
            "</i>; cuyas características y condiciones se detallan a"
            " continuación:",
            estilo_parrafo
        )
        fragmentos = parrafo.splitOn(canvas, A4[0], A4[1]-52*mm)
        (_, y) = fragmentos[0].wrapOn(canvas, A4[0], A4[1]-32*mm)
        fragmentos[0].drawOn(canvas, 0, A4[1]-32*mm-y)
        y = A4[1]-38*mm-y
        parrafo = Paragraph(
            "<u>I- <b>Descripción del Servicio:</b></u>",
            estilo_parrafo
        )
        fragmentos = parrafo.splitOn(canvas, A4[0], y-20*mm)
        fragmentos[0].wrapOn(canvas, 0, y)
        fragmentos[0].drawOn(canvas, 0, y)
        y -= 5*mm
        parrafo = Paragraph(
            orden_servicio.solicitud_servicio.descripcion_solicitud,
            ParagraphStyle(
                name='descripcion',
                fontName='Nimbus Roman No9 L Regular',
                fontSize=12,
                leading=14.25,
                firstLineIndent=5*mm,
                leftIndent=30*mm,
                rightIndent=20*mm,
                alignment=TA_JUSTIFY
            )
        )
        fragmentos = parrafo.splitOn(canvas, A4[0], y-20*mm)
        fragmentos[0].wrapOn(canvas, 0, y)
        fragmentos[0].drawOn(canvas, 0, y)
        while len(fragmentos) == 2:
            canvas.showPage()
            fragmentos = fragmentos[1].splitOn(canvas, A4[0], A4[1]-40*mm)
            (_, y) = fragmentos[1].wrapOn(canvas, A4[0], A4[1]-20*mm)
            fragmentos[0].drawOn(canvas, 0, A4[1]-20*mm-y)
            y = A4[1]-20*mm-y
        if y >= 32*mm:
            y -= 6*mm
        else:
            canvas.showPage()
            y = A4[1]-20*mm
        parrafo = Paragraph(
            "<u>II- <b>Comitentes:</b></u>",
            estilo_parrafo
        )
        fragmentos = parrafo.splitOn(canvas, A4[0], y-20*mm)
        fragmentos[0].wrapOn(canvas, 0, y)
        fragmentos[0].drawOn(canvas, 0, y)
        estilo_parrafo = ParagraphStyle(
            name='lista',
            fontName='Nimbus Roman No9 L Regular',
            fontSize=12,
            leading=14.25,
            bulletFontName='Nimbus Roman No9 L Regular',
            bulletFontSize=12,
            bulletIndent=35*mm,
            bulletType='bullet',
            leftIndent=40*mm,
            rightIndent=20*mm,
            alignment=TA_JUSTIFY
        )
        lista: list[Paragraph] = [
            Paragraph(
                f'<bullet>&bull;</bullet>{c}',
                style=estilo_parrafo,
            )
            for c in
            orden_servicio.comitentes_en_solicitud
        ]
        aux: float = y
        for comitente in lista:
            fragmentos = comitente.splitOn(canvas, A4[0], aux)
            (_, y) = fragmentos[0].wrapOn(canvas, A4[0], aux)
            fragmentos[0].drawOn(canvas, 0, aux-y)
            aux -= y
            while len(fragmentos) == 2:
                canvas.showPage()
                fragmentos = fragmentos[1].splitOn(canvas, A4[0], A4[1]-40*mm)
                (_, y) = fragmentos[1].wrapOn(canvas, A4[0], A4[1]-20*mm)
                fragmentos[0].drawOn(canvas, 0, A4[1]-20*mm-y)
                aux = A4[1]-20*mm-y
        if aux >= 32*mm:
            y = aux - 6*mm
        else:
            canvas.showPage()
            y = A4[1]-20*mm
        estilo_parrafo = ParagraphStyle(
            name='titulos',
            fontName='Nimbus Roman No9 L Regular',
            fontSize=12,
            leading=14.25,
            leftIndent=30*mm,
            rightIndent=20*mm,
            alignment=TA_JUSTIFY
        )
        parrafo = Paragraph(
            "<u>III- <b>Responsables Técnicos:</b></u>",
            estilo_parrafo
        )
        fragmentos = parrafo.splitOn(canvas, A4[0], y-20*mm)
        fragmentos[0].wrapOn(canvas, 0, y)
        fragmentos[0].drawOn(canvas, 0, y)
        estilo_parrafo = ParagraphStyle(
            name='lista',
            fontName='Nimbus Roman No9 L Regular',
            fontSize=12,
            leading=14.25,
            bulletFontName='Nimbus Roman No9 L Regular',
            bulletFontSize=12,
            bulletIndent=35*mm,
            bulletType='bullet',
            leftIndent=40*mm,
            rightIndent=20*mm,
            alignment=TA_JUSTIFY
        )
        lista = [
            Paragraph(
                f'<bullet>&bull;</bullet>{rt}',
                style=estilo_parrafo,
            )
            for rt in
            orden_servicio.responsables_en_solicitud
        ]
        aux = y
        for rt in lista:
            fragmentos = rt.splitOn(canvas, A4[0], aux)
            (_, y) = fragmentos[0].wrapOn(canvas, A4[0], aux)
            fragmentos[0].drawOn(canvas, 0, aux-y)
            aux -= y
            while len(fragmentos) == 2:
                canvas.showPage()
                fragmentos = fragmentos[1].splitOn(canvas, A4[0], A4[1]-40*mm)
                (_, y) = fragmentos[1].wrapOn(canvas, A4[0], A4[1]-20*mm)
                fragmentos[0].drawOn(canvas, 0, A4[1]-20*mm-y)
                aux = A4[1]-20*mm-y
        if aux >= 32*mm:
            y = aux - 6*mm
        else:
            canvas.showPage()
            y = A4[1]-20*mm
        if orden_servicio.compromisos_comitente != []:
            estilo_parrafo = ParagraphStyle(
                name='titulos',
                fontName='Nimbus Roman No9 L Regular',
                fontSize=12,
                leading=14.25,
                leftIndent=30*mm,
                rightIndent=20*mm,
                alignment=TA_JUSTIFY
            )
            parrafo = Paragraph(
                "<u>IV- <b>Compromisos de Comitente:</b></u>",
                estilo_parrafo
            )
            fragmentos = parrafo.splitOn(canvas, A4[0], y-20*mm)
            fragmentos[0].wrapOn(canvas, 0, y)
            fragmentos[0].drawOn(canvas, 0, y)
            estilo_parrafo = ParagraphStyle(
                name='lista',
                fontName='Nimbus Roman No9 L Regular',
                fontSize=12,
                leading=14.25,
                bulletFontName='Nimbus Roman No9 L Regular',
                bulletFontSize=12,
                bulletIndent=35*mm,
                bulletType='bullet',
                leftIndent=40*mm,
                rightIndent=20*mm,
                alignment=TA_JUSTIFY
            )
            lista = [
                Paragraph(
                    f'<bullet>&bull;</bullet>{cc}',
                    style=estilo_parrafo,
                )
                for cc in
                orden_servicio.compromisos_comitente
            ]
            aux = y
            for cc in lista:
                fragmentos = cc.splitOn(canvas, A4[0], aux)
                (_, y) = fragmentos[0].wrapOn(canvas, A4[0], aux)
                fragmentos[0].drawOn(canvas, 0, aux-y)
                aux -= y
                while len(fragmentos) == 2:
                    canvas.showPage()
                    fragmentos = fragmentos[1].splitOn(
                        canvas,
                        A4[0],
                        A4[1]-40*mm
                    )
                    (_, y) = fragmentos[1].wrapOn(canvas, A4[0], A4[1]-20*mm)
                    fragmentos[0].drawOn(canvas, 0, A4[1]-20*mm-y)
                    aux = A4[1]-20*mm-y
            if aux >= 32*mm:
                y = aux - 6*mm
            else:
                canvas.showPage()
                y = A4[1]-20*mm
        estilo_parrafo = ParagraphStyle(
            name='titulos',
            fontName='Nimbus Roman No9 L Regular',
            fontSize=12,
            leading=14.25,
            leftIndent=30*mm,
            rightIndent=20*mm,
            alignment=TA_JUSTIFY
        )
        parrafo = Paragraph(
            "<u>V- <b>Compromisos de Unidad Ejecutora:</b></u>"
            if orden_servicio.compromisos_comitente != [] else
            "<u>IV- <b>Compromisos de Unidad Ejecutora:</b></u>",
            estilo_parrafo
        )
        fragmentos = parrafo.splitOn(canvas, A4[0], y-20*mm)
        fragmentos[0].wrapOn(canvas, 0, y)
        fragmentos[0].drawOn(canvas, 0, y)
        estilo_parrafo = ParagraphStyle(
            name='lista',
            fontName='Nimbus Roman No9 L Regular',
            fontSize=12,
            leading=14.25,
            bulletFontName='Nimbus Roman No9 L Regular',
            bulletFontSize=12,
            bulletIndent=35*mm,
            bulletType='bullet',
            leftIndent=40*mm,
            rightIndent=20*mm,
            alignment=TA_JUSTIFY
        )
        lista = [
            Paragraph(
                f'<bullet>&bull;</bullet>{cue}',
                style=estilo_parrafo,
            )
            for cue in
            orden_servicio.compromisos_unidad_ejecutora
        ]
        aux = y
        for cue in lista:
            fragmentos = cue.splitOn(canvas, A4[0], aux)
            (_, y) = fragmentos[0].wrapOn(canvas, A4[0], aux)
            fragmentos[0].drawOn(canvas, 0, aux-y)
            aux -= y
            while len(fragmentos) == 2:
                canvas.showPage()
                fragmentos = fragmentos[1].splitOn(canvas, A4[0], A4[1]-40*mm)
                (_, y) = fragmentos[1].wrapOn(canvas, A4[0], A4[1]-20*mm)
                fragmentos[0].drawOn(canvas, 0, A4[1]-20*mm-y)
                aux = A4[1]-20*mm-y
        if aux >= 32*mm:
            y = aux - 6*mm
        else:
            canvas.showPage()
            y = A4[1]-20*mm
        estilo_parrafo = ParagraphStyle(
            name='titulos',
            fontName='Nimbus Roman No9 L Regular',
            fontSize=12,
            leading=14.25,
            leftIndent=30*mm,
            rightIndent=20*mm,
            alignment=TA_JUSTIFY
        )
        parrafo = Paragraph(
            "<u>VI- <b>Retribuciones Económicas:</b></u>"
            if orden_servicio.compromisos_comitente != [] else
            "<u>V- <b>Retribuciones Económicas:</b></u>",
            estilo_parrafo
        )
        fragmentos = parrafo.splitOn(canvas, A4[0], y-20*mm)
        fragmentos[0].wrapOn(canvas, 0, y)
        fragmentos[0].drawOn(canvas, 0, y)
        estilo_parrafo = ParagraphStyle(
            name='lista',
            fontName='Nimbus Roman No9 L Regular',
            fontSize=12,
            leading=14.25,
            bulletFontName='Nimbus Roman No9 L Regular',
            bulletFontSize=12,
            bulletIndent=35*mm,
            bulletType='bullet',
            leftIndent=40*mm,
            rightIndent=20*mm,
            alignment=TA_JUSTIFY
        )
        lista = [
            Paragraph(
                f'<bullet>&bull;</bullet>{re}',
                style=estilo_parrafo,
            )
            for re in
            orden_servicio.retribuciones_economicas
        ]
        lista.append(
            Paragraph(
                "<bullet>&bull;</bullet><u>Total:</u> $"
                f"{format_decimal(sum(orden_servicio.montos), format='0.00', locale=to_locale(settings.LANGUAGE_CODE))}"
                " pesos argentinos",
                style=estilo_parrafo
            )
        )
        aux = y
        for re in lista:
            fragmentos = re.splitOn(canvas, A4[0], aux)
            (_, y) = fragmentos[0].wrapOn(canvas, A4[0], aux)
            fragmentos[0].drawOn(canvas, 0, aux-y)
            aux -= y
            while len(fragmentos) == 2:
                canvas.showPage()
                fragmentos = fragmentos[1].splitOn(canvas, A4[0], A4[1]-40*mm)
                (_, y) = fragmentos[1].wrapOn(canvas, A4[0], A4[1]-20*mm)
                fragmentos[0].drawOn(canvas, 0, A4[1]-20*mm-y)
                aux = A4[1]-20*mm-y
        if aux >= 36*mm:
            y = aux - 5*mm
        else:
            canvas.showPage()
            y = A4[1]-20*mm
        estilo_parrafo = ParagraphStyle(
            name='estilo',
            fontName='Nimbus Roman No9 L Regular',
            fontSize=10,
            leading=12,
            leftIndent=30*mm,
            rightIndent=20*mm,
            alignment=TA_JUSTIFY
        )
        parrafo = Paragraph(
            "Todo Responsable Técnico suscrito a la Orden de Servicio"
            " asume la responsabilidad frente a daños y perjuicios"
            " (Artículo 774 inciso b, c y s.s. del Código Civil y"
            " Comercial) producidos por los actos y/o omisiones"
            " generadores de Responsabilidad Civil, cometidos por ellos"
            " o cualquiera de los integrantes del equipo de trabajo"
            " invoucrado contra el Beneficiario o Usuario -sea en"
            " personas, bienes o derechos-; donde responderán solidaria"
            " e ilimitadamente en los términos del Artículo 828 del"
            " Código Civil y Comercial, que tengan como origen la"
            " presentación pormal de la actividad ante la autoridad"
            " competente hasta los futuros agravios que puedan surgir a"
            " consecuencia de las mismas. Por ello, se exime de toda"
            " responsabilidad a la Facultad de Ciencias Exactas, Químicas"
            " y Naturales de la Universidad Nacional de Misiones.",
            estilo_parrafo
        )
        fragmentos = parrafo.splitOn(canvas, A4[0], aux-20*mm)
        (_, y) = fragmentos[0].wrapOn(canvas, A4[0], aux)
        fragmentos[0].drawOn(canvas, 0, aux-y)
        while len(fragmentos) == 2:
            canvas.showPage()
            fragmentos = fragmentos[1].splitOn(canvas, A4[0], A4[1]-40*mm)
            (_, y) = fragmentos[1].wrapOn(canvas, A4[0], A4[1]-20*mm)
            fragmentos[0].drawOn(canvas, 0, A4[1]-20*mm-y)
            y = A4[1]-20*mm-y
        aux -= y + 5*mm
        dibujo: Drawing = Drawing(
            50*mm,
            37.5*mm
        )
        dibujo.add(
            Rect(
                0,
                12.5*mm,
                50*mm,
                37.5*mm,
                strokeWidth=0.25,
                strokeColor="grey",
                fillColor=None
            )
        )
        dibujo.add(
            Rect(
                0,
                0,
                50*mm,
                12.5*mm,
                strokeWidth=0.25,
                strokeColor="grey",
                fillColor=None
            )
        )
        dibujo.add(
            String(
                25*mm,
                13.75*mm,
                "Firma",
                fontSize=10,
                textAnchor='middle'
            )
        )
        dibujo.add(
            String(
                25*mm,
                1.25*mm,
                "Fecha",
                fontSize=10,
                textAnchor='middle'
            )
        )
        dibujo.add(
            Line(
                3*mm,
                12.5*mm + 4.15*mm,
                47*mm,
                12.5*mm + 4.15*mm,
                strokeWidth=0.25,
                strokeColor="black"
            )
        )
        dibujo.add(
            Line(
                3*mm,
                4.15*mm,
                47*mm,
                4.15*mm,
                strokeWidth=0.25,
                strokeColor="black"
            )
        )
        dibujo.add(
            Line(
                14*mm,
                5*mm,
                16*mm,
                10*mm,
                strokeWidth=0.25,
                strokeColor="black"
            )
        )
        dibujo.add(
            Line(
                27*mm,
                5*mm,
                29*mm,
                10*mm,
                strokeWidth=0.25,
                strokeColor="black"
            )
        )
        estilo_parrafo = ParagraphStyle(
            name='epigrafe',
            fontName='Nimbus Roman No9 L Regular',
            fontSize=10,
            alignment=TA_CENTER
        )
        parrafos: list[set[Model, str]] = [
            (
                cs.comitente.usuario_comitente,
                f'Comitente'
                f'<br/>{cs.comitente.usuario_comitente.last_name},'
                f' {cs.comitente.usuario_comitente.first_name}'
            )
            for cs in
            orden_servicio.solicitud_servicio.comitentesolicitud_set.all()
        ]
        parrafos.extend(
            (
                rt.responsable_tecnico.usuario_responsable,
                f'Responsable Técnico'
                f'<br/>{rt.responsable_tecnico.usuario_responsable.last_name},'
                f' {rt.responsable_tecnico.usuario_responsable.first_name}'
            )
            for rt in
            orden_servicio.solicitud_servicio.responsablesolicitud_set.all()
        )
        secretario: Secretario = Secretario.objects.get(
            Q(habilitado_secretario=True)
        )
        parrafos.append(
            (
                secretario.usuario_secretario,
                'Secretaría de Extensión y Vinculación Tecnológica'
                f'<br/>{secretario.usuario_secretario.last_name},'
                f' {secretario.usuario_secretario.first_name}'
            )
        )
        firmantes: list[set[int, int, float, float]] = []
        izq: Paragraph
        der: Paragraph
        fi: list[Paragraph]
        fd: list[Paragraph]
        for i in range(len(parrafos)//2):
            izq = Paragraph(parrafos[i*2][1], estilo_parrafo)
            fi = izq.splitOn(canvas, 50*mm, aux-20*mm)
            (_, y) = fi[0].wrapOn(canvas, 50*mm, aux)
            der = Paragraph(parrafos[(i*2)+1][1], estilo_parrafo)
            fd = der.splitOn(canvas, 50*mm, aux-20*mm)
            if y < fd[0].wrapOn(canvas, 50*mm, aux)[1]:
                (_, y) = fd[0].wrapOn(canvas, 50*mm, aux)
            if 20*mm <= aux-y-40*mm:
                fi[0].drawOn(canvas, 45*mm, aux-y)
                dibujo.drawOn(canvas, 45*mm, aux-y-50*mm)
                if i*2 < orden_servicio.solicitud_servicio.comitentesolicitud_set.count():
                    firmantes.append(
                        (
                            parrafos[i*2][0],
                            canvas.getPageNumber(),
                            45*mm, aux-y
                        )
                    )
                elif i*2 < (
                    orden_servicio.solicitud_servicio.comitentesolicitud_set.count() +
                    orden_servicio.solicitud_servicio.responsablesolicitud_set.count()
                ):
                    firmantes.append(
                        (
                            parrafos[i*2][0],
                            canvas.getPageNumber(),
                            45*mm, aux-y
                        )
                    )
                else:
                    firmantes.append(
                        (
                            secretario.usuario_secretario,
                            canvas.getPageNumber(),
                            45*mm, aux-y
                        )
                    )
                fd[0].drawOn(canvas, 125*mm, aux-y)
                dibujo.drawOn(canvas, 125*mm, aux-y-50*mm)
                if (i*2)+1 < orden_servicio.solicitud_servicio.comitentesolicitud_set.count():
                    firmantes.append(
                        (
                            parrafos[(i*2)+1][0],
                            canvas.getPageNumber(),
                            125*mm, aux-y
                        )
                    )
                elif (i*2)+1 < (
                    orden_servicio.solicitud_servicio.comitentesolicitud_set.count() +
                    orden_servicio.solicitud_servicio.responsablesolicitud_set.count()
                ):
                    firmantes.append(
                        (
                            parrafos[(i*2)+1][0],
                            canvas.getPageNumber(),
                            125*mm, aux-y
                        )
                    )
                else:
                    firmantes.append(
                        (
                            secretario.usuario_secretario,
                            canvas.getPageNumber(),
                            125*mm, aux-y
                        )
                    )
                aux -= y+55*mm
            else:
                canvas.showPage()
                fi[0].drawOn(canvas, 45*mm, A4[1]-20*mm-y)
                dibujo.drawOn(canvas, 45*mm, A4[1]-y-70*mm)
                if i*2 < orden_servicio.solicitud_servicio.comitentesolicitud_set.count():
                    firmantes.append(
                        (
                            parrafos[i*2][0],
                            canvas.getPageNumber(),
                            45*mm, A4[1]-20*mm-y
                        )
                    )
                elif i*2 < (
                    orden_servicio.solicitud_servicio.comitentesolicitud_set.count() +
                    orden_servicio.solicitud_servicio.responsablesolicitud_set.count()
                ):
                    firmantes.append(
                        (
                            parrafos[i*2][0],
                            canvas.getPageNumber(),
                            45*mm, A4[1]-20*mm-y
                        )
                    )
                else:
                    firmantes.append(
                        (
                            secretario.usuario_secretario,
                            canvas.getPageNumber(),
                            45*mm, A4[1]-20*mm-y
                        )
                    )
                fd[0].drawOn(canvas, 125*mm, A4[1]-20*mm-y)
                dibujo.drawOn(canvas, 125*mm, A4[1]-y-70*mm)
                if (i*2)+1 < orden_servicio.solicitud_servicio.comitentesolicitud_set.count():
                    firmantes.append(
                        (
                            parrafos[(i*2)+1][0],
                            canvas.getPageNumber(),
                            125*mm, A4[1]-20*mm-y
                        )
                    )
                elif (i*2)+1 < (
                    orden_servicio.solicitud_servicio.comitentesolicitud_set.count() +
                    orden_servicio.solicitud_servicio.responsablesolicitud_set.count()
                ):
                    firmantes.append(
                        (
                            parrafos[(i*2)+1][0],
                            canvas.getPageNumber(),
                            125*mm, A4[1]-20*mm-y
                        )
                    )
                else:
                    firmantes.append(
                        (
                            secretario.usuario_secretario,
                            canvas.getPageNumber(),
                            125*mm, A4[1]-20*mm-y
                        )
                    )
                aux = A4[1]-y-75*mm
        if len(parrafos) % 2 == 1:
            parrafo = Paragraph(parrafos[-1][1], estilo_parrafo)
            fragmentos = parrafo.splitOn(canvas, 50*mm, aux-20*mm)
            (_, y) = fragmentos[0].wrapOn(canvas, 50*mm, aux)
            if 20*mm <= aux-y-40*mm:
                fragmentos[0].drawOn(canvas, 85*mm, aux-y)
                dibujo.drawOn(canvas, 85*mm, aux-y-50*mm)
                firmantes.append(
                    (
                        secretario.usuario_secretario,
                        canvas.getPageNumber(),
                        85*mm, aux-y
                    )
                )
                aux -= y+55*mm
            else:
                canvas.showPage()
                fragmentos[0].drawOn(canvas, 85*mm, A4[1]-20*mm-y)
                dibujo.drawOn(canvas, 85*mm, A4[1]-y-70*mm)
                firmantes.append(
                    (
                        secretario.usuario_secretario,
                        canvas.getPageNumber(),
                        85*mm, A4[1]-20*mm-y
                    )
                )
                aux = A4[1]-y-75*mm
        canvas.showPage()
        canvas.save()
        buffer.seek(0)
        archivo: ContentFile = ContentFile(
            content=buffer.getvalue(),
            name=f"{datetime.now(timezone(settings.TIME_ZONE)).isoformat()}.pdf"
        )
        orden_servicio.archivo_orden_original = archivo
        orden_servicio.ultima_accion_orden = TransactionNow()
        with transaction.atomic():
            orden_servicio.save()
            firma: FirmaOrden
            for firma_orden in firmantes:
                firma = FirmaOrden(
                    orden_firmada=orden_servicio,
                    usuario_firmante=firma_orden[0],
                    pagina_firma=firma_orden[1],
                    coord_x_firma=firma_orden[2],
                    coord_y_firma=firma_orden[3],
                    tiempo_firma=None,
                    documento_firmado=None
                )
                firma.save()
        buffer.seek(0)
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=f'ordenServicio{orden}.pdf'
        )
