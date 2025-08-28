from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Permission
from django.db.models import Q, QuerySet
from django.db.models.query import RawQuerySet
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseRedirect
)
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import to_locale
from django.views.generic import TemplateView

from babel.dates import format_datetime
from datetime import datetime, timedelta, timezone
from io import BytesIO
import matplotlib.colors as mplc
import matplotlib.dates as mpld
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
import pytz
from typing import Any, Dict, Optional, Self
from unidecode import unidecode
import xml.etree.ElementTree as ET

from ..models import Convenio

from solicitudes.models import Categoria

from cuentas.models import Comitente, ResponsableTecnico, Secretario

from gesservorconv.dates import Formateador, Ubicador
from gesservorconv.mixins import (
    MixinAccesoRequerido,
    MixinPermisoRequerido
)
from gesservorconv.views import HtmxHttpRequest


class VistaInformeConveniosResponsable(
    MixinAccesoRequerido,
    MixinPermisoRequerido,
    UserPassesTestMixin,
    TemplateView
):
    template_name: str = 'firmas/informe_convenios_responsable.html'
    permission_required: QuerySet[Permission] = Permission.objects.filter(
        codename=f'view_{Convenio.__name__.lower()}'
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

    def get_context_data(
        self: Self,
        **kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        contexto: Dict[str, Any] = super().get_context_data(**kwargs)
        contexto["usuario"] = self.request.user
        contexto["comitente"] = Comitente.objects.filter(
            Q(usuario_comitente=self.request.user) &
            (
                Q(habilitado_comitente=True) |
                Q(habilitado_organizaciones_comitente__contains=[
                    True
                ])
            )
        ).exists() if Comitente.objects.filter(
            Q(usuario_comitente=self.request.user) &
            Q(usuario_comitente__is_active=True)
        ).exists() else None
        contexto["responsable"] = ResponsableTecnico.objects.filter(
            Q(usuario_responsable=self.request.user) &
            (
                Q(habilitado_responsable=True) |
                Q(habilitado_organizaciones_responsable__contains=[
                    True
                ])
            )
        ).exists() if ResponsableTecnico.objects.filter(
            Q(usuario_responsable=self.request.user) &
            Q(usuario_responsable__is_active=True)
        ).exists() else None
        contexto["secretario"] = Secretario.objects.filter(
            Q(usuario_secretario=self.request.user) &
            Q(habilitado_secretario=True)
        ).exists() if Secretario.objects.filter(
            Q(usuario_secretario=self.request.user) &
            Q(usuario_secretario__is_active=True)
        ).exists() else None
        contexto["staff"] = self.request.user.is_staff
        contexto["admin"] = self.request.user.is_superuser
        return contexto

    def get(
        self: Self,
        request: HtmxHttpRequest
    ) -> FileResponse:
        """
        https://matplotlib.org/stable/gallery/user_interfaces/svg_histogram_sgskip.html
        """
        if request.htmx:
            lenguaje: str = request.GET.get(
                "local", settings.LANGUAGE_CODE
            )
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
            offset: Optional[str] = request.GET.get(
                "offset"
            )  # Offset en minutos
            grupos: str = request.GET.get(
                "grupos", "10"
            )
            if int(grupos) > 25:
                contexto: Dict[str, Any] = {}
                contexto['custom_popovers'] = ''
                contexto['hist_patches'] = ''
                contexto['svg'] = (
                    '<svg id="histograma" xmlns="http://www.w3.org/2000/svg"'
                    ' width="1" height="1"></svg>'
                )
                contexto['botones'] = (
                    '<div id="etiquetas" hx-swap-oob="outerHTML">'
                    '<p class="text-start">Cantidad de grupos excesiva</p>'
                    '</div>'
                )
                return render(
                    request,
                    'parciales/_estadistica_informe_convenios_responsable.html',
                    contexto
                )
            tiempo_inicio: datetime = (
                datetime.strptime(
                    f"{buscar_fecha_inicio} {buscar_hora_inicio}",
                    "%Y-%m-%d %H:%M"
                ) + timedelta(minutes=int(offset))
                if buscar_fecha_inicio and buscar_hora_inicio
                else datetime.fromtimestamp(0, timezone.utc)
            )
            tiempo_fin: datetime = (
                datetime.strptime(
                    f"{buscar_fecha_fin} {buscar_hora_fin}",
                    "%Y-%m-%d %H:%M"
                ) + timedelta(minutes=int(offset)+1)
                if buscar_fecha_fin and buscar_hora_fin
                else datetime.now(timezone.utc)
            )
            categorias: RawQuerySet[Categoria]
            if estado == "completo":
                categorias = Categoria.objects.raw(
                    "SELECT c.id,"
                    " c.nombre_categoria, f.acronimo_facultad,"
                    " ARRAY_AGG(DISTINCT hstore(ss)) as solicitudes"
                    " FROM solicitudes_servicio_categorias_solicitud AS sscs"
                    " INNER JOIN categorias AS c"
                    " ON sscs.categoria_id = c.id"
                    " INNER JOIN facultades AS f"
                    " ON c.facultad_categoria_id = f.id INNER JOIN"
                    " (SELECT comitentes_solicitud.solicitud_servicio_id,"
                    " MIN(tiempo_decision) AS tiempo_creacion"
                    " FROM comitentes_solicitud"
                    " NATURAL JOIN responsables_solicitud"
                    " INNER JOIN convenios ON"
                    " comitentes_solicitud.solicitud_servicio_id ="
                    " convenios.solicitud_servicio_id"
                    " INNER JOIN servicios ON"
                    " convenios.solicitud_servicio_id ="
                    " servicios.convenio_id"
                    " GROUP BY comitentes_solicitud.solicitud_servicio_id,"
                    " convenios.solicitud_servicio_id,"
                    " servicios.convenio_id"
                    " HAVING MIN(tiempo_decision) IS NOT NULL"
                    " AND %s = ANY(ARRAY_AGG(responsable_tecnico_id))"
                    " AND date_trunc('minute', MIN(tiempo_decision)) >= %s"
                    " AND date_trunc('minute', MIN(tiempo_decision)) < %s)"
                    " AS ss ON sscs.solicitudservicio_id ="
                    " ss.solicitud_servicio_id"
                    " GROUP BY c.id,"
                    " c.nombre_categoria, f.acronimo_facultad"
                    " UNION SELECT 0 as id,"
                    " '' AS nombre_categoria,"
                    " 'ninguna' AS acronimo_facultad,"
                    " ARRAY_AGG(hstore(ss)) as solicitudes FROM"
                    " (SELECT comitentes_solicitud.solicitud_servicio_id,"
                    " MIN(tiempo_decision) AS tiempo_creacion"
                    " FROM comitentes_solicitud"
                    " NATURAL JOIN responsables_solicitud"
                    " INNER JOIN convenios ON"
                    " comitentes_solicitud.solicitud_servicio_id ="
                    " convenios.solicitud_servicio_id"
                    " INNER JOIN servicios ON"
                    " convenios.solicitud_servicio_id ="
                    " servicios.convenio_id"
                    " GROUP BY comitentes_solicitud.solicitud_servicio_id,"
                    " convenios.solicitud_servicio_id,"
                    " servicios.convenio_id"
                    " HAVING MIN(tiempo_decision) IS NOT NULL"
                    " AND %s = ANY(ARRAY_AGG(responsable_tecnico_id))"
                    " AND date_trunc('minute', MIN(tiempo_decision)) >= %s"
                    " AND date_trunc('minute', MIN(tiempo_decision)) < %s)"
                    " AS ss"
                    " LEFT JOIN solicitudes_servicio_categorias_solicitud"
                    " AS sscs ON sscs.solicitudservicio_id ="
                    " ss.solicitud_servicio_id"
                    " LEFT JOIN categorias AS c"
                    " ON sscs.categoria_id = c.id"
                    " WHERE sscs.solicitudservicio_id IS NULL"
                    " GROUP BY c.id"
                    " ORDER BY acronimo_facultad, nombre_categoria;",
                    [
                        request.user.id,
                        tiempo_inicio.replace(
                            tzinfo=timezone.utc
                        ).isoformat(),
                        tiempo_fin.replace(
                            tzinfo=timezone.utc
                        ).isoformat(),
                        request.user.id,
                        tiempo_inicio.replace(
                            tzinfo=timezone.utc
                        ).isoformat(),
                        tiempo_fin.replace(
                            tzinfo=timezone.utc
                        ).isoformat()
                    ]
                )
            elif estado == "curso":
                categorias = Categoria.objects.raw(
                    "SELECT c.id,"
                    " c.nombre_categoria, f.acronimo_facultad,"
                    " ARRAY_AGG(DISTINCT hstore(ss)) as solicitudes"
                    " FROM solicitudes_servicio_categorias_solicitud AS sscs"
                    " INNER JOIN categorias AS c"
                    " ON sscs.categoria_id = c.id"
                    " INNER JOIN facultades AS f"
                    " ON c.facultad_categoria_id = f.id INNER JOIN"
                    " (SELECT comitentes_solicitud.solicitud_servicio_id,"
                    " MIN(tiempo_decision) AS tiempo_creacion"
                    " FROM comitentes_solicitud"
                    " NATURAL JOIN responsables_solicitud"
                    " INNER JOIN convenios ON"
                    " comitentes_solicitud.solicitud_servicio_id ="
                    " convenios.solicitud_servicio_id"
                    " GROUP BY comitentes_solicitud.solicitud_servicio_id,"
                    " convenios.solicitud_servicio_id"
                    " HAVING MIN(tiempo_decision) IS NOT NULL"
                    " AND convenios.cancelacion_convenio IS NULL"
                    " AND convenios.convenio_suspendido IS FALSE"
                    " AND %s = ANY(ARRAY_AGG(responsable_tecnico_id))"
                    " AND date_trunc('minute', MIN(tiempo_decision)) >= %s"
                    " AND date_trunc('minute', MIN(tiempo_decision)) < %s)"
                    " AS ss ON sscs.solicitudservicio_id ="
                    " ss.solicitud_servicio_id"
                    " GROUP BY c.id,"
                    " c.nombre_categoria, f.acronimo_facultad"
                    " UNION SELECT 0 as id,"
                    " '' AS nombre_categoria,"
                    " 'ninguna' AS acronimo_facultad,"
                    " ARRAY_AGG(hstore(ss)) as solicitudes FROM"
                    " (SELECT comitentes_solicitud.solicitud_servicio_id,"
                    " MIN(tiempo_decision) AS tiempo_creacion"
                    " FROM comitentes_solicitud"
                    " NATURAL JOIN responsables_solicitud"
                    " INNER JOIN convenios ON"
                    " comitentes_solicitud.solicitud_servicio_id ="
                    " convenios.solicitud_servicio_id"
                    " GROUP BY comitentes_solicitud.solicitud_servicio_id,"
                    " convenios.solicitud_servicio_id"
                    " HAVING MIN(tiempo_decision) IS NOT NULL"
                    " AND convenios.cancelacion_convenio IS NULL"
                    " AND convenios.convenio_suspendido IS FALSE"
                    " AND %s = ANY(ARRAY_AGG(responsable_tecnico_id))"
                    " AND date_trunc('minute', MIN(tiempo_decision)) >= %s"
                    " AND date_trunc('minute', MIN(tiempo_decision)) < %s)"
                    " AS ss"
                    " LEFT JOIN solicitudes_servicio_categorias_solicitud"
                    " AS sscs ON sscs.solicitudservicio_id ="
                    " ss.solicitud_servicio_id"
                    " LEFT JOIN categorias AS c"
                    " ON sscs.categoria_id = c.id"
                    " WHERE sscs.solicitudservicio_id IS NULL"
                    " GROUP BY c.id"
                    " ORDER BY acronimo_facultad, nombre_categoria;",
                    [
                        request.user.id,
                        tiempo_inicio.replace(
                            tzinfo=timezone.utc
                        ).isoformat(),
                        tiempo_fin.replace(
                            tzinfo=timezone.utc
                        ).isoformat(),
                        request.user.id,
                        tiempo_inicio.replace(
                            tzinfo=timezone.utc
                        ).isoformat(),
                        tiempo_fin.replace(
                            tzinfo=timezone.utc
                        ).isoformat()
                    ]
                )
            elif estado == "suspendido":
                categorias = Categoria.objects.raw(
                    "SELECT c.id,"
                    " c.nombre_categoria, f.acronimo_facultad,"
                    " ARRAY_AGG(DISTINCT hstore(ss)) as solicitudes"
                    " FROM solicitudes_servicio_categorias_solicitud AS sscs"
                    " INNER JOIN categorias AS c"
                    " ON sscs.categoria_id = c.id"
                    " INNER JOIN facultades AS f"
                    " ON c.facultad_categoria_id = f.id INNER JOIN"
                    " (SELECT comitentes_solicitud.solicitud_servicio_id,"
                    " MIN(tiempo_decision) AS tiempo_creacion"
                    " FROM comitentes_solicitud"
                    " NATURAL JOIN responsables_solicitud"
                    " INNER JOIN solicitudes_servicio ON"
                    " comitentes_solicitud.solicitud_servicio_id ="
                    " solicitudes_servicio.id_solicitud"
                    " INNER JOIN convenios ON"
                    " comitentes_solicitud.solicitud_servicio_id ="
                    " convenios.solicitud_servicio_id"
                    " WHERE convenios.cancelacion_convenio IS NULL"
                    " AND convenios.convenio_suspendido IS TRUE"
                    " GROUP BY comitentes_solicitud.solicitud_servicio_id"
                    " HAVING MIN(tiempo_decision) IS NOT NULL"
                    " AND %s = ANY(ARRAY_AGG(responsable_tecnico_id))"
                    " AND date_trunc('minute', MIN(tiempo_decision)) >= %s"
                    " AND date_trunc('minute', MIN(tiempo_decision)) < %s)"
                    " AS ss ON sscs.solicitudservicio_id ="
                    " ss.solicitud_servicio_id"
                    " GROUP BY c.id,"
                    " c.nombre_categoria, f.acronimo_facultad"
                    " UNION SELECT 0 as id,"
                    " '' AS nombre_categoria,"
                    " 'ninguna' AS acronimo_facultad,"
                    " ARRAY_AGG(hstore(ss)) as solicitudes FROM"
                    " (SELECT comitentes_solicitud.solicitud_servicio_id,"
                    " MIN(tiempo_decision) AS tiempo_creacion"
                    " FROM comitentes_solicitud"
                    " NATURAL JOIN responsables_solicitud"
                    " INNER JOIN solicitudes_servicio ON"
                    " comitentes_solicitud.solicitud_servicio_id ="
                    " solicitudes_servicio.id_solicitud"
                    " INNER JOIN convenios ON"
                    " comitentes_solicitud.solicitud_servicio_id ="
                    " convenios.solicitud_servicio_id"
                    " WHERE convenios.cancelacion_convenio IS NULL"
                    " AND convenios.convenio_suspendido IS TRUE"
                    " GROUP BY comitentes_solicitud.solicitud_servicio_id"
                    " HAVING MIN(tiempo_decision) IS NOT NULL"
                    " AND %s = ANY(ARRAY_AGG(responsable_tecnico_id))"
                    " AND date_trunc('minute', MIN(tiempo_decision)) >= %s"
                    " AND date_trunc('minute', MIN(tiempo_decision)) < %s)"
                    " AS ss"
                    " LEFT JOIN solicitudes_servicio_categorias_solicitud"
                    " AS sscs ON sscs.solicitudservicio_id ="
                    " ss.solicitud_servicio_id"
                    " LEFT JOIN categorias AS c"
                    " ON sscs.categoria_id = c.id"
                    " WHERE sscs.solicitudservicio_id IS NULL"
                    " GROUP BY c.id"
                    " ORDER BY acronimo_facultad, nombre_categoria;",
                    [
                        request.user.id,
                        tiempo_inicio.replace(
                            tzinfo=timezone.utc
                        ).isoformat(),
                        tiempo_fin.replace(
                            tzinfo=timezone.utc
                        ).isoformat(),
                        request.user.id,
                        tiempo_inicio.replace(
                            tzinfo=timezone.utc
                        ).isoformat(),
                        tiempo_fin.replace(
                            tzinfo=timezone.utc
                        ).isoformat()
                    ]
                )
            elif estado == "cancelado":
                categorias = Categoria.objects.raw(
                    "SELECT c.id,"
                    " c.nombre_categoria, f.acronimo_facultad,"
                    " ARRAY_AGG(DISTINCT hstore(ss)) as solicitudes"
                    " FROM solicitudes_servicio_categorias_solicitud AS sscs"
                    " INNER JOIN categorias AS c"
                    " ON sscs.categoria_id = c.id"
                    " INNER JOIN facultades AS f"
                    " ON c.facultad_categoria_id = f.id INNER JOIN"
                    " (SELECT comitentes_solicitud.solicitud_servicio_id,"
                    " MIN(tiempo_decision) AS tiempo_creacion"
                    " FROM comitentes_solicitud"
                    " NATURAL JOIN responsables_solicitud"
                    " INNER JOIN solicitudes_servicio ON"
                    " comitentes_solicitud.solicitud_servicio_id ="
                    " solicitudes_servicio.id_solicitud"
                    " INNER JOIN convenios ON"
                    " comitentes_solicitud.solicitud_servicio_id ="
                    " convenios.solicitud_servicio_id"
                    " WHERE convenios.cancelacion_convenio IS NOT NULL"
                    " GROUP BY comitentes_solicitud.solicitud_servicio_id"
                    " HAVING MIN(tiempo_decision) IS NOT NULL"
                    " AND %s = ANY(ARRAY_AGG(responsable_tecnico_id))"
                    " AND date_trunc('minute', MIN(tiempo_decision)) >= %s"
                    " AND date_trunc('minute', MIN(tiempo_decision)) < %s)"
                    " AS ss ON sscs.solicitudservicio_id ="
                    " ss.solicitud_servicio_id"
                    " GROUP BY c.id,"
                    " c.nombre_categoria, f.acronimo_facultad"
                    " UNION SELECT 0 as id,"
                    " '' AS nombre_categoria,"
                    " 'ninguna' AS acronimo_facultad,"
                    " ARRAY_AGG(hstore(ss)) as solicitudes FROM"
                    " (SELECT comitentes_solicitud.solicitud_servicio_id,"
                    " MIN(tiempo_decision) AS tiempo_creacion"
                    " FROM comitentes_solicitud"
                    " NATURAL JOIN responsables_solicitud"
                    " INNER JOIN solicitudes_servicio ON"
                    " comitentes_solicitud.solicitud_servicio_id ="
                    " solicitudes_servicio.id_solicitud"
                    " INNER JOIN convenios ON"
                    " comitentes_solicitud.solicitud_servicio_id ="
                    " convenios.solicitud_servicio_id"
                    " WHERE convenios.cancelacion_convenio IS NOT NULL"
                    " GROUP BY comitentes_solicitud.solicitud_servicio_id"
                    " HAVING MIN(tiempo_decision) IS NOT NULL"
                    " AND %s = ANY(ARRAY_AGG(responsable_tecnico_id))"
                    " AND date_trunc('minute', MIN(tiempo_decision)) >= %s"
                    " AND date_trunc('minute', MIN(tiempo_decision)) < %s)"
                    " AS ss"
                    " LEFT JOIN solicitudes_servicio_categorias_solicitud"
                    " AS sscs ON sscs.solicitudservicio_id ="
                    " ss.solicitud_servicio_id"
                    " LEFT JOIN categorias AS c"
                    " ON sscs.categoria_id = c.id"
                    " WHERE sscs.solicitudservicio_id IS NULL"
                    " GROUP BY c.id"
                    " ORDER BY acronimo_facultad, nombre_categoria;",
                    [
                        request.user.id,
                        tiempo_inicio.replace(
                            tzinfo=timezone.utc
                        ).isoformat(),
                        tiempo_fin.replace(
                            tzinfo=timezone.utc
                        ).isoformat(),
                        request.user.id,
                        tiempo_inicio.replace(
                            tzinfo=timezone.utc
                        ).isoformat(),
                        tiempo_fin.replace(
                            tzinfo=timezone.utc
                        ).isoformat()
                    ]
                )
            if len(categorias) == 0:
                contexto: Dict[str, Any] = {}
                contexto['custom_popovers'] = ''
                contexto['hist_patches'] = ''
                contexto['svg'] = (
                    '<svg id="histograma" xmlns="http://www.w3.org/2000/svg"'
                    ' width="1" height="1"></svg>'
                )
                contexto['botones'] = (
                    '<div id="etiquetas" hx-swap-oob="outerHTML">'
                    '<p class="text-start">No hay convenios</p>'
                    '</div>'
                )
                return render(
                    request,
                    'parciales/_estadistica_informe_convenios_responsable.html',
                    contexto
                )
            plt.switch_backend('agg')
            plt.rcParams['svg.fonttype'] = 'none'
            plt.rcParams['font.family'] = 'Open Sans Medium'
            plt.rcParams['legend.labelcolor'] = '#343a40'
            plt.rcParams['xtick.labelcolor'] = '#343a40'
            plt.rcParams['ytick.labelcolor'] = '#343a40'
            plt.rcParams['patch.force_edgecolor'] = True
            plt.rcParams['patch.edgecolor'] = '#343a40'
            ET.register_namespace('', 'http://www.w3.org/2000/svg')
            np.random.seed(19680801)
            fig, ax = plt.subplots(1, 1, layout='constrained')
            ax.grid('on', linestyle=':')
            aux: float = (
                tiempo_fin - tiempo_inicio
            ).total_seconds() // 60
            cuentas, bins, patches = plt.hist(
                [
                    [
                        mpld.date2num(
                            datetime.fromisoformat(
                                solicitud['tiempo_creacion']
                            )
                        )
                        for solicitud in
                        categoria.solicitudes
                    ]
                    for categoria in categorias
                ],
                bins=int(grupos) if int(grupos) <= int(aux) else int(aux),
                range=(
                    mpld.date2num(tiempo_inicio),
                    mpld.date2num(tiempo_fin)
                ),
                align="left",
                orientation="horizontal",
                label=[
                    f'{categoria.acronimo_facultad}:'
                    f' {categoria.nombre_categoria}'
                    if categoria.nombre_categoria != ''
                    else categoria.acronimo_facultad
                    for categoria in categorias
                ]
            )
            ax.set_xlabel("Cantidad")
            ax.set_ylabel("Tiempo")
            aux = aux + 1
            ax.yaxis.set_major_locator(
                Ubicador(
                    pytz.FixedOffset(-(int(offset)))
                    if offset else None,
                    1 if aux < 5 else 2,
                    {
                        mpld.YEARLY: 11,
                        mpld.MONTHLY: 12,
                        mpld.DAILY: 11,
                        mpld.HOURLY: 12,
                        mpld.MINUTELY: (
                            11 if 11 <= aux else aux
                        )
                    }
                )
            )
            ax.yaxis.set_major_formatter(
                Formateador(
                    ax.yaxis.get_major_locator(),
                    pytz.FixedOffset(-(int(offset)))
                    if offset else None,
                    to_locale(lenguaje)
                )
            )
            ax.xaxis.set_major_locator(
                MaxNLocator('auto', integer=True, min_n_ticks=1)
            )
            hndl, lgn = ax.get_legend_handles_labels()
            leyenda: plt.Legend = fig.legend(
                hndl, lgn,
                frameon=False,
                fontsize=10,
                loc='outside upper left'
            )
            hist_patches: dict[str, list[str]] = {}
            if isinstance(cuentas[0], np.ndarray):
                for ic, c in enumerate(patches):
                    hist_patches[f'hist_{ic}'] = []
                    for il, element in enumerate(c):
                        element.set_gid(f'hist_{ic}_patch_{il}')
                        hist_patches[f'hist_{ic}'].append(
                            f'hist_{ic}_patch_{il}'
                        )
            else:
                hist_patches['hist_0'] = []
                for il, element in enumerate(patches):
                    element.set_gid(f'hist_0_patch_{il}')
                    hist_patches['hist_0'].append(f'hist_0_patch_{il}')
            botones: ET.Element = ET.Element('div')
            botones.set('id', 'etiquetas')
            botones.set('class', 'btn-toolbar justify-content-start mx-1')
            botones.set('role', 'toolbar')
            botones.set('aria-label', 'Marcadores de etiquetas')
            botones.set('hx-swap-oob', 'outerHTML')
            boton: ET.Element
            custom_popovers: ET.Element = ET.Element('style')
            custom_popovers.set('id', 'custom-popovers')
            color: str
            hexa: str
            aux: str
            tri: tuple[float, float, float]
            estilos: str = ''
            clases: list[str] = []
            for i, t in enumerate(leyenda.get_texts()):
                leyenda.get_patches()[i].set_gid(f'leg_patch_{i}')
                t.set_gid(f'leg_text_{i}')
                hexa = mplc.to_hex(
                    leyenda.get_patches()[i].get_facecolor(),
                    False
                )
                tri = mplc.to_rgb(
                    leyenda.get_patches()[i].get_facecolor()
                )
                color = (
                    '#ffffff'
                    if (
                        tri[0]*0.299
                        + tri[1]*0.587
                        + tri[2]*0.114
                    ) < 0.5
                    else '#000000'
                )
                boton = ET.Element('button')
                boton.set('id', str(i))
                boton.set('class', 'btn btn-sm focus-ring me-2 mt-2')
                boton.set('onclick', 'toggle_hist(this);')
                boton.text = (
                    f'{categorias[i].acronimo_facultad}:'
                    f' {categorias[i].nombre_categoria}'
                    if categorias[i].nombre_categoria != ''
                    else categorias[i].acronimo_facultad
                )
                boton.set(
                    'style',
                    f'--bs-btn-bg: {hexa};'
                    f' --bs-btn-color: {color};'
                    f' --bs-focus-ring-color: {hexa};'
                )
                botones.append(boton)
                aux = (
                    categorias[i].acronimo_facultad.lower() + '_' +
                    unidecode(
                        categorias[i].nombre_categoria
                    ).replace(" ", "_").lower()
                )
                estilos = (
                    estilos +
                    f'\n\t.{aux}'
                    '{\n\t\t--bs-popover-border-color:'
                    f' {hexa};\n'
                    f'\t\t--bs-popover-header-bg: {hexa};\n'
                    f'\t\t--bs-popover-header-color: {color};\n'
                    '\t}\n'
                )
                clases.append(aux)
            custom_popovers.text = estilos
            buffer: BytesIO = BytesIO()
            plt.savefig(buffer, transparent=True, format='svg')
            arbol, xmlid = ET.XMLID(buffer.getvalue())
            buffer.close()
            arbol.set('id', 'histograma')
            arbol.set('class', 'mt-3 me-auto img-fluid')
            titulo: ET.Element = ET.Element('title')
            titulo.text = 'Histograma de Informe de Solicitud de Servicio'
            arbol.append(titulo)
            tabla: ET.Element = ET.Element('table')
            tabla.set(
                'class',
                'table table-sm table-hover table-striped-columns'
                ' table-bordered align-middle'
            )
            seccion: ET.Element = ET.Element('thead')
            fila: ET.Element = ET.Element('tr')
            fila.set('class', 'text-center')
            celda: ET.Element = ET.Element('th')
            celda.set('scope', 'col')
            celda.text = 'Resultados'
            fila.append(celda)
            for i in range(len(mpld.num2date(bins)) - 1):
                celda = ET.Element('td')
                celda.text = format_datetime(
                    mpld.num2date(bins)[i].astimezone(
                        timezone(timedelta(minutes=-(int(offset))))
                        if offset
                        else pytz.timezone(settings.TIME_ZONE)
                    ),
                    'short',
                    pytz.FixedOffset(-(int(offset)))
                    if offset else pytz.timezone(settings.TIME_ZONE),
                    to_locale(lenguaje)
                ) + '\n-\n' + format_datetime(
                    mpld.num2date(bins)[i+1].astimezone(
                        timezone(timedelta(minutes=-(int(offset))))
                        if offset
                        else pytz.timezone(settings.TIME_ZONE)
                    ),
                    'short',
                    pytz.FixedOffset(-(int(offset)))
                    if offset else pytz.timezone(settings.TIME_ZONE),
                    to_locale(lenguaje)
                )
                fila.append(celda)
            seccion.append(fila)
            tabla.append(seccion)
            seccion = ET.Element('tbody')
            seccion.set('class', 'table-group-divider')
            if isinstance(cuentas[0], np.ndarray):
                for ic, contenedor in enumerate(patches):
                    fila = ET.Element('tr')
                    celda = ET.Element('th')
                    celda.text = (
                        f'{categorias[ic].acronimo_facultad}:'
                        f' {categorias[ic].nombre_categoria}'
                        if categorias[ic].nombre_categoria != ''
                        else categorias[ic].acronimo_facultad
                    )
                    fila.append(celda)
                    for il, patch in enumerate(contenedor):
                        altura = patch.get_width()
                        if altura > 0:
                            el = xmlid[f'hist_{ic}_patch_{il}']
                            el.set('tabindex', '-1')
                            el.set('data-bs-toggle', 'popover')
                            el.set('data-bs-custom-class', clases[ic])
                            el.set(
                                'data-bs-title',
                                f'{categorias[ic].acronimo_facultad}:'
                                f' {categorias[ic].nombre_categoria}'
                                if categorias[ic].nombre_categoria != ''
                                else categorias[ic].acronimo_facultad
                            )
                            el.set(
                                'data-bs-content',
                                f'{int(altura)} solicitud{"es" if altura > 1 else ""}'
                            )
                            el.set('data-bs-trigger', 'click hover focus')
                        celda = ET.Element('td')
                        celda.text = str(int(altura))
                        fila.append(celda)
                    seccion.append(fila)
            else:
                fila = ET.Element('tr')
                celda = ET.Element('th')
                celda.text = (
                    f'{categorias[0].acronimo_facultad}:'
                    f' {categorias[0].nombre_categoria}'
                    if categorias[0].nombre_categoria != ''
                    else categorias[0].acronimo_facultad
                )
                fila.append(celda)
                for il, patch in enumerate(patches):
                    altura = patch.get_width()
                    if altura > 0:
                        el = xmlid[f'hist_0_patch_{il}']
                        el.set('tabindex', '-1')
                        el.set('data-bs-toggle', 'popover')
                        el.set('data-bs-custom-class', clases[0])
                        el.set(
                            'data-bs-title',
                            f'{categorias[0].acronimo_facultad}:'
                            f' {categorias[0].nombre_categoria}'
                            if categorias[0].nombre_categoria != ''
                            else categorias[0].acronimo_facultad
                        )
                        el.set(
                            'data-bs-content',
                            f'{int(altura)} solicitud{"es" if altura > 1 else ""}'
                        )
                        el.set('data-bs-trigger', 'click hover focus')
                    celda = ET.Element('td')
                    celda.text = str(int(altura))
                    fila.append(celda)
                seccion.append(fila)
            tabla.append(seccion)
            contexto: Dict[str, Any] = {}
            contexto['custom_popovers'] = ET.tostring(custom_popovers).decode()
            contexto['hist_patches'] = hist_patches
            contexto['svg'] = ET.tostring(arbol).decode()
            contexto['tabla'] = ET.tostring(tabla).decode()
            contexto['botones'] = ET.tostring(botones).decode()
            buffer.close()
            return render(
                request,
                'parciales/_estadistica_informe_convenios_responsable.html',
                contexto
            )
        return super().get(request)
