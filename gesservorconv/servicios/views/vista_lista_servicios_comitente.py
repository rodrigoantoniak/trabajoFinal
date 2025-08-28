from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.db import connection
from django.db.models import Min, Q, QuerySet
from django.http import JsonResponse, HttpRequest
from django.views import generic
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import (
    Avg, BigIntegerField, Case, F, Min, Q, RowRange, When, Window
)
from django.db.models.functions import FirstValue, Lag
from django.db.models.query import QuerySet

from datetime import timedelta

from django.conf import settings
from django.core import mail
from django.db.models import QuerySet
from django.template import Template
from django.template.context import Context
from django.template.loader import get_template, render_to_string
from django_hosts.resolvers import get_host
from re import DOTALL, findall, MULTILINE, S, sub
from gesservorconv.hosts import puerto

from typing import Any, Self

from ..models import Servicio

from cuentas.models import Comitente


class VistaJsonSolicitudesSugeribles(
    generic.View
):
    def get(self: Self, request: HttpRequest) -> JsonResponse:
        resultado: list[dict[str, Any]]
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT cui, personas, AVG(delta) AS promedio,"
                " MAX(ultimo) AS mas_reciente FROM"
                " (SELECT ss.id_solicitud,"
                " ARRAY_AGG(CASE WHEN cs.cuit_organizacion_comitente IS NULL"
                " THEN c.usuario_comitente_id ELSE NULL END"
                " ORDER BY c.usuario_comitente_id) AS personas,"
                " ARRAY_AGG(CASE WHEN cs.cuit_organizacion_comitente IS NOT NULL"
                " THEN cs.cuit_organizacion_comitente ELSE c.cuil_comitente END"
                " ORDER BY c.cuil_comitente) AS cui,"
                " CASE WHEN LAG(MIN(cs.tiempo_decision), 1) OVER"
                " (PARTITION BY ARRAY_AGG(CASE"
                " WHEN (cs.cuit_organizacion_comitente IS NOT NULL)"
                " THEN cs.cuit_organizacion_comitente ELSE c.cuil_comitente END"
                " ORDER BY c.cuil_comitente) ORDER BY MIN(cs.tiempo_decision)"
                " ROWS BETWEEN CURRENT ROW AND CURRENT ROW)"
                " IS NOT NULL THEN (MIN(cs.tiempo_decision) -"
                " LAG(MIN(cs.tiempo_decision), 1) OVER"
                " (PARTITION BY ARRAY_AGG(CASE"
                " WHEN cs.cuit_organizacion_comitente IS NOT NULL"
                " THEN cs.cuit_organizacion_comitente ELSE c.cuil_comitente END"
                " ORDER BY c.cuil_comitente)"
                " ORDER BY MIN(cs.tiempo_decision)"
                " ROWS BETWEEN CURRENT ROW AND CURRENT ROW))"
                " ELSE '00:00:00' END AS delta,"
                " LAST_VALUE(MIN(cs.tiempo_decision)) OVER"
                " (PARTITION BY ARRAY_AGG(CASE"
                " WHEN (cs.cuit_organizacion_comitente IS NOT NULL)"
                " THEN cs.cuit_organizacion_comitente ELSE c.cuil_comitente END"
                " ORDER BY c.cuil_comitente) ORDER BY MIN(cs.tiempo_decision))"
                " AS ultimo"
                " FROM solicitudes_servicio AS ss"
                " INNER JOIN comitentes_solicitud AS cs"
                " ON (ss.id_solicitud = cs.solicitud_servicio_id)"
                " INNER JOIN comitentes AS c"
                " ON (cs.comitente_id = c.usuario_comitente_id)"
                " WHERE ss.id_solicitud IN"
                " (SELECT s.convenio_id FROM servicios AS s"
                " WHERE s.convenio_id IS NOT NULL)"
                " GROUP BY ss.id_solicitud)"
                " WHERE delta <> '00:00:00' GROUP BY cui, personas;"
            )
            columnas: list[str] = [
                col[0] for col in cursor.description
            ]
            resultado = [
                dict(zip(columnas, fila)) for fila in cursor.fetchall()
            ]
        usuarios: QuerySet[User] = User.objects.none()
        for grupo in resultado:
            usuarios = usuarios.union(
                User.objects.filter(
                    id__in=[
                        persona for persona in
                        grupo["personas"]
                        if persona is not None
                    ]
                )
            )
        print([usuario for usuario in usuarios])
        for usuario in usuarios:
            contexto: dict[str, Any] = {
                'usuario': usuario,
                'protocolo': (
                    'https' if settings.SECURE_SSL_REDIRECT else 'http'
                ),
                'dominio': (
                    f'{get_host().regex}:{puerto}'
                    if puerto else get_host().regex
                ),
            }
            mensaje_html: str = render_to_string(
                template_name='correo_sugerencia_convenio.html',
                context=contexto
            )
            plantilla: str = get_template(
                template_name='correo_sugerencia_convenio.html'
            )
            contenido_plano: str = ''
            bloque_procesado: str
            for texto in findall(
                r">[^><]*[^><\s]+[^><]*<\/",
                plantilla.template.source,
                DOTALL | MULTILINE | S
            ):
                bloque_procesado = sub(
                    r'\s+', ' ',
                    ' '.join(texto[1:-2].split()), 0,
                    DOTALL | MULTILINE | S
                )
                contenido_plano = f'{contenido_plano}{bloque_procesado}\n'
            mensaje_plano: Template = Template(
                template_string=contenido_plano
            )
            mail.send_mail(
                "Sugerencia de Convenio",
                message=mensaje_plano.render(context=Context(contexto)),
                html_message=mensaje_html,
                from_email=settings.SERVER_EMAIL,
                recipient_list=[usuario.email]
            )
        return JsonResponse(
            data={
                str(indice): {
                    "cui": grupo["cui"],
                    "personas": grupo["personas"],
                    "promedio": grupo["promedio"].seconds,
                    "ultimo": grupo["mas_reciente"]
                }
                for indice, grupo in
                enumerate(resultado)
            }
        )
