from typing import Any, Dict, Optional, Self
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.paginator import Page, Paginator
from django.contrib.auth import logout
from django.contrib.auth.models import Permission
from django.db.models import Q
from django.db.models.query import QuerySet, RawQuerySet
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView

from django_htmx.http import HttpResponseClientRedirect, push_url

from datetime import datetime, timedelta, timezone

from .models import Django, Cuentas, Solicitudes

from cuentas.models import Comitente, ResponsableTecnico, Secretario

from gesservorconv.mixins import MixinAccesoRequerido
from gesservorconv.views import HtmxHttpRequest


class VistaAuditoria(
    MixinAccesoRequerido,
    UserPassesTestMixin,
    ListView
):
    model: type[Django] = Django
    template_name: str = "auditoria/listar_auditoria.html"
    paginate_by: int = 25
    page_kwarg: Optional[str] = None
    allow_empty: bool = True

    def _gestionar_permisos_sin_buscar_valor(
        self,
        cadena: str,
        permitidos: RawQuerySet
    ) -> str:
        codigos: list[str] = [p.codename for p in permitidos]
        modelos: dict[str, str] = {
            Django.__name__.lower(): "auditoria_django",
            Cuentas.__name__.lower(): "auditoria_cuentas",
            Solicitudes.__name__.lower(): "auditoria_solicitudes",
        }
        tablas_permitidas: list[str] = [
            nombre_tabla
            for modelo, nombre_tabla in modelos.items()
            if f"view_{modelo}" in codigos
        ]
        if not tablas_permitidas:
            return cadena + (
                " (SELECT * FROM auditoria_django"
                " WHERE viejo_auditoria IS NULL"
                " AND nuevo_auditoria IS NULL)"
            )
        subconsulta: str = " UNION ".join(
            f"SELECT * FROM {tabla}" for tabla in tablas_permitidas
        )
        return f"{cadena} ({subconsulta})"

    def _gestionar_permisos_buscando_valor(
        self,
        cadena: str,
        permitidos: RawQuerySet
    ) -> str:
        codigos: list[str] = [p.codename for p in permitidos]
        modelos: dict[str, str] = {
            Django.__name__.lower(): "auditoria_django",
            Cuentas.__name__.lower(): "auditoria_cuentas",
            Solicitudes.__name__.lower(): "auditoria_solicitudes",
        }
        tablas_permitidas: list[str] = [
            nombre_tabla
            for modelo, nombre_tabla in modelos.items()
            if f"view_{modelo}" in codigos
        ]
        if not tablas_permitidas:
            return cadena + (
                " (SELECT * FROM auditoria_django"
                " WHERE viejo_auditoria IS NULL"
                " AND nuevo_auditoria IS NULL)"
            )
        busqueda: str = (
            "(to_tsvector('spanish',"
            " array_to_string(avals(viejo_auditoria), ' ', ''))"
            " @@ websearch_to_tsquery('spanish', %(valor)s)) OR"
            " (to_tsvector('spanish',"
            " array_to_string(avals(nuevo_auditoria), ' ', ''))"
            " @@ websearch_to_tsquery('spanish', %(valor)s))"
        )
        subconsulta: str = " UNION ".join(
            f"SELECT * FROM {tabla} WHERE {busqueda}"
            for tabla in tablas_permitidas
        )
        return f"{cadena} ({subconsulta})"

    def _filtrar(
        self: Self,
        cadena: str,
        creado: Optional[str],
        editado: Optional[str],
        destruido: Optional[str]
    ) -> str:
        consulta: str = cadena + " AND"
        if (
            creado is not None and
            destruido is not None
        ):
            consulta = consulta + (
                " (viejo_auditoria IS NULL) OR"
                " (nuevo_auditoria IS NULL)"
            )
        elif (
            creado is not None and
            editado is not None
        ):
            consulta = consulta + (
                " (nuevo_auditoria IS NOT NULL)"
            )
        elif (
            editado is not None and
            destruido is not None
        ):
            consulta = consulta + (
                " (viejo_auditoria IS NOT NULL)"
            )
        elif creado is not None:
            consulta = consulta + (
                " (viejo_auditoria IS NULL) AND"
                " (nuevo_auditoria IS NOT NULL)"
            )
        elif destruido is not None:
            consulta = consulta + (
                " (viejo_auditoria IS NOT NULL) AND"
                " (nuevo_auditoria IS NULL)"
            )
        elif editado is not None:
            consulta = consulta + (
                " (viejo_auditoria IS NOT NULL) AND"
                " (nuevo_auditoria IS NOT NULL)"
            )
        return consulta

    def test_func(self: Self) -> bool:
        return self.request.user.is_staff

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
                respuesta: HttpResponse = HttpResponseClientRedirect(
                    reverse_lazy("cuentas:iniciar_sesion")
                )
                return push_url(respuesta, direccion)
            return HttpResponseRedirect(direccion)
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

    def get_queryset(self: Self) -> RawQuerySet:
        permisos: RawQuerySet = Permission.objects.raw(
            "SELECT DISTINCT ON (codename) id, codename"
            " FROM auth_permission WHERE id IN "
            "(SELECT permission_id FROM auth_user_user_permissions"
            " WHERE user_id = %(id_usuario)s UNION "
            "SELECT permission_id FROM auth_group_permissions"
            " NATURAL JOIN auth_user_groups WHERE user_id ="
            " %(id_usuario)s);",
            {"id_usuario": self.request.user.id}
        )
        consulta: str = (
            "SELECT id_auditoria, relname, tiempo_auditoria,"
            " ARRAY_AGG(ARRAY[va.key, va.value]"
            " ORDER BY pg_attribute.attnum)"
            " FILTER (WHERE va.key IS NOT NULL) AS viejo,"
            " ARRAY_AGG(ARRAY[na.key, na.value]"
            " ORDER BY pg_attribute.attnum)"
            " FILTER (WHERE na.key IS NOT NULL) AS nuevo FROM"
        )
        if self.request.user.is_superuser:
            consulta = consulta + (
                " (SELECT * FROM auditoria_django UNION"
                " SELECT * FROM auditoria_cuentas UNION"
                " SELECT * FROM auditoria_solicitudes)"
            )
        else:
            consulta = self._gestionar_permisos_sin_buscar_valor(
                consulta,
                permisos
            )
        consulta = consulta + (
            " AS auditoria INNER JOIN pg_class"
            " ON auditoria.tabla_auditoria = pg_class.oid"
            " INNER JOIN pg_attribute"
            " ON pg_attribute.attrelid = pg_class.oid"
            " AND pg_attribute.attnum > 0"
            " LEFT JOIN LATERAL each(viejo_auditoria) AS va"
            " ON va.key = pg_attribute.attname"
            " LEFT JOIN LATERAL each(nuevo_auditoria) AS na"
            " ON na.key = pg_attribute.attname"
            " GROUP BY id_auditoria, relname, tiempo_auditoria"
            " ORDER BY tiempo_auditoria DESC;"
        )
        auditoria: RawQuerySet = \
            Django.objects.raw(consulta)
        return auditoria

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

    def get(self: Self, request: HtmxHttpRequest) -> HttpResponse:
        if request.htmx:
            busqueda_tabla: Optional[str] = request.GET.get(
                "buscar_tabla"
            )
            busqueda_valor: Optional[str] = request.GET.get(
                "buscar_valor"
            )
            creado_incluido: Optional[str] = request.GET.get(
                "creado_incluido"
            )
            editado_incluido: Optional[str] = request.GET.get(
                "editado_incluido"
            )
            destruido_incluido: Optional[str] = request.GET.get(
                "destruido_incluido"
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
            tiempo_inicio: datetime = datetime.strptime(
                f"{buscar_fecha_inicio} {buscar_hora_inicio}",
                "%Y-%m-%d %H:%M"
            ) + timedelta(minutes=int(offset))
            tiempo_fin: datetime = datetime.strptime(
                f"{buscar_fecha_fin} {buscar_hora_fin}",
                "%Y-%m-%d %H:%M"
            ) + timedelta(minutes=int(offset))
            permisos: RawQuerySet = Permission.objects.raw(
                "SELECT DISTINCT ON (codename) id, codename"
                " FROM auth_permission WHERE id IN "
                "(SELECT permission_id FROM auth_user_user_permissions"
                " WHERE user_id = %(id_usuario)s UNION "
                "SELECT permission_id FROM auth_group_permissions"
                " NATURAL JOIN auth_user_groups WHERE user_id ="
                " %(id_usuario)s);",
                {"id_usuario": request.user.id}
            )
            consulta: str = ""
            auditoria: QuerySet | RawQuerySet
            if (
                (
                    creado_incluido is None and
                    editado_incluido is None and
                    destruido_incluido is None
                ) or (
                    len(permisos) == 0 and
                    not request.user.is_superuser
                )
            ):
                auditoria = Django.objects.none()
            elif (
                busqueda_tabla == "" and
                busqueda_valor == ""
            ):
                consulta = (
                    "SELECT id_auditoria, relname, tiempo_auditoria,"
                    " ARRAY_AGG(ARRAY[va.key, va.value]"
                    " ORDER BY pg_attribute.attnum)"
                    " FILTER (WHERE va.key IS NOT NULL) AS viejo,"
                    " ARRAY_AGG(ARRAY[na.key, na.value]"
                    " ORDER BY pg_attribute.attnum)"
                    " FILTER (WHERE na.key IS NOT NULL) AS nuevo FROM"
                )
                if request.user.is_superuser:
                    consulta = consulta + (
                        " (SELECT * FROM auditoria_django UNION"
                        " SELECT * FROM auditoria_cuentas UNION"
                        " SELECT * FROM auditoria_solicitudes)"
                    )
                else:
                    consulta = self._gestionar_permisos_sin_buscar_valor(
                        consulta,
                        permisos
                    )
                consulta = consulta + (
                    " AS auditoria INNER JOIN pg_class"
                    " ON auditoria.tabla_auditoria = pg_class.oid"
                    " INNER JOIN pg_attribute"
                    " ON pg_attribute.attrelid = pg_class.oid"
                    " AND pg_attribute.attnum > 0"
                    " LEFT JOIN LATERAL each(viejo_auditoria) AS va"
                    " ON va.key = pg_attribute.attname"
                    " LEFT JOIN LATERAL each(nuevo_auditoria) AS na"
                    " ON na.key = pg_attribute.attname"
                    " WHERE (date_trunc('minute', tiempo_auditoria) >= %s)"
                    " AND (date_trunc('minute', tiempo_auditoria) <= %s)"
                )
                if (
                    creado_incluido is None or
                    editado_incluido is None or
                    destruido_incluido is None
                ):
                    consulta = self._filtrar(
                        consulta,
                        creado_incluido,
                        editado_incluido,
                        destruido_incluido
                    )
                consulta = consulta + (
                    " GROUP BY id_auditoria, relname, tiempo_auditoria"
                    " ORDER BY tiempo_auditoria DESC;"
                )
                auditoria = Django.objects.raw(
                    consulta,
                    [
                        tiempo_inicio.replace(
                            tzinfo=timezone.utc
                        ).strftime("%Y-%m-%d %T"),
                        tiempo_fin.replace(
                            tzinfo=timezone.utc
                        ).strftime("%Y-%m-%d %T")
                    ]
                )
            elif (
                busqueda_tabla != "" and
                busqueda_valor == ""
            ):
                consulta = (
                    "SELECT id_auditoria, relname, tiempo_auditoria,"
                    " ARRAY_AGG(ARRAY[va.key, va.value]"
                    " ORDER BY pg_attribute.attnum)"
                    " FILTER (WHERE va.key IS NOT NULL) AS viejo,"
                    " ARRAY_AGG(ARRAY[na.key, na.value]"
                    " ORDER BY pg_attribute.attnum)"
                    " FILTER (WHERE na.key IS NOT NULL) AS nuevo FROM"
                )
                if request.user.is_superuser:
                    consulta = consulta + (
                        " (SELECT * FROM auditoria_django UNION"
                        " SELECT * FROM auditoria_cuentas UNION"
                        " SELECT * FROM auditoria_solicitudes)"
                    )
                else:
                    consulta = self._gestionar_permisos_sin_buscar_valor(
                        consulta,
                        permisos
                    )
                consulta = consulta + (
                    " AS auditoria INNER JOIN pg_class"
                    " ON auditoria.tabla_auditoria = pg_class.oid"
                    " INNER JOIN pg_attribute"
                    " ON pg_attribute.attrelid = pg_class.oid"
                    " AND pg_attribute.attnum > 0"
                    " LEFT JOIN LATERAL each(viejo_auditoria) AS va"
                    " ON va.key = pg_attribute.attname"
                    " LEFT JOIN LATERAL each(nuevo_auditoria) AS na"
                    " ON na.key = pg_attribute.attname"
                    " WHERE (date_trunc('minute', tiempo_auditoria)"
                    " >= %s) AND"
                    " (date_trunc('minute', tiempo_auditoria) <= %s)"
                    " AND (to_tsvector('simple', relname)"
                    " @@ websearch_to_tsquery('simple', %s))"
                )
                if (
                    creado_incluido is None or
                    editado_incluido is None or
                    destruido_incluido is None
                ):
                    consulta = self._filtrar(
                        consulta,
                        creado_incluido,
                        editado_incluido,
                        destruido_incluido
                    )
                consulta = consulta + (
                    " GROUP BY id_auditoria, relname, tiempo_auditoria"
                    " ORDER BY tiempo_auditoria DESC;"
                )
                auditoria = Django.objects.raw(
                    consulta,
                    [
                        tiempo_inicio.replace(
                            tzinfo=timezone.utc
                        ).strftime("%Y-%m-%d %T"),
                        tiempo_fin.replace(
                            tzinfo=timezone.utc
                        ).strftime("%Y-%m-%d %T"),
                        str(busqueda_tabla).strip()
                    ]
                )
            elif (
                busqueda_tabla == "" and
                busqueda_valor != ""
            ):
                consulta = (
                    "SELECT id_auditoria, tiempo_auditoria,"
                    " ARRAY_AGG(ARRAY[va.key, va.value]"
                    " ORDER BY pg_attribute.attnum)"
                    " FILTER (WHERE va.key IS NOT NULL) AS viejo,"
                    " ARRAY_AGG(ARRAY[na.key, na.value]"
                    " ORDER BY pg_attribute.attnum)"
                    " FILTER (WHERE na.key IS NOT NULL) AS nuevo FROM"
                )
                if request.user.is_superuser:
                    consulta = consulta + (
                        "(SELECT * FROM auditoria_django WHERE"
                        " (to_tsvector('spanish',"
                        " array_to_string(avals(viejo_auditoria),' ', ''))"
                        " @@ websearch_to_tsquery('spanish', %(valor)s)) OR"
                        " (to_tsvector('spanish',"
                        " array_to_string(avals(nuevo_auditoria),' ', ''))"
                        " @@ websearch_to_tsquery('spanish', %(valor)s))"
                        "UNION SELECT * FROM auditoria_cuentas WHERE"
                        " (to_tsvector('spanish',"
                        " array_to_string(avals(viejo_auditoria),' ', ''))"
                        " @@ websearch_to_tsquery('spanish', %(valor)s)) OR"
                        " (to_tsvector('spanish',"
                        " array_to_string(avals(nuevo_auditoria),' ', ''))"
                        " @@ websearch_to_tsquery('spanish', %(valor)s))"
                        "UNION SELECT * FROM auditoria_solicitudes WHERE"
                        " (to_tsvector('spanish',"
                        " array_to_string(avals(viejo_auditoria),' ', ''))"
                        " @@ websearch_to_tsquery('spanish', %(valor)s)) OR"
                        " (to_tsvector('spanish',"
                        " array_to_string(avals(nuevo_auditoria),' ', ''))"
                        " @@ websearch_to_tsquery('spanish', %(valor)s)))"
                    )
                else:
                    consulta = self._gestionar_permisos_buscando_valor(
                        consulta,
                        permisos
                    )
                consulta = consulta + (
                    "AS auditoria INNER JOIN pg_class"
                    " ON auditoria.tabla_auditoria = pg_class.oid"
                    " INNER JOIN pg_attribute"
                    " ON pg_attribute.attrelid = pg_class.oid"
                    " AND pg_attribute.attnum > 0"
                    " LEFT JOIN LATERAL each(viejo_auditoria) AS va"
                    " ON va.key = pg_attribute.attname"
                    " LEFT JOIN LATERAL each(nuevo_auditoria) AS na"
                    " ON na.key = pg_attribute.attname"
                    " WHERE (date_trunc('minute', tiempo_auditoria)"
                    " >= %(inicio)s) AND"
                    " (date_trunc('minute', tiempo_auditoria)"
                    " <= %(fin)s)"
                )
                if (
                    creado_incluido is None or
                    editado_incluido is None or
                    destruido_incluido is None
                ):
                    consulta = self._filtrar(
                        consulta,
                        creado_incluido,
                        editado_incluido,
                        destruido_incluido
                    )
                consulta = consulta + (
                    " GROUP BY id_auditoria, relname, tiempo_auditoria"
                    " ORDER BY tiempo_auditoria DESC;"
                )
                auditoria = Django.objects.raw(
                    consulta,
                    {
                        "valor": str(busqueda_valor).strip(),
                        "inicio": tiempo_inicio.replace(
                            tzinfo=timezone.utc
                        ).strftime("%Y-%m-%d %T"),
                        "fin": tiempo_fin.replace(
                            tzinfo=timezone.utc
                        ).strftime("%Y-%m-%d %T")
                    }
                )
            elif (
                busqueda_tabla != "" and
                busqueda_valor != ""
            ):
                consulta = (
                    "SELECT id_auditoria, tiempo_auditoria,"
                    " ARRAY_AGG(ARRAY[va.key, va.value]"
                    " ORDER BY pg_attribute.attnum)"
                    " FILTER (WHERE va.key IS NOT NULL) AS viejo,"
                    " ARRAY_AGG(ARRAY[na.key, na.value]"
                    " ORDER BY pg_attribute.attnum)"
                    " FILTER (WHERE na.key IS NOT NULL) AS nuevo FROM"
                )
                if request.user.is_superuser:
                    consulta = consulta + (
                        "(SELECT * FROM auditoria_django WHERE"
                        " (to_tsvector('spanish',"
                        " array_to_string(avals(viejo_auditoria),' ', ''))"
                        " @@ websearch_to_tsquery('spanish', %(valor)s)) OR"
                        " (to_tsvector('spanish',"
                        " array_to_string(avals(nuevo_auditoria),' ', ''))"
                        " @@ websearch_to_tsquery('spanish', %(valor)s))"
                        "UNION SELECT * FROM auditoria_cuentas WHERE"
                        " (to_tsvector('spanish',"
                        " array_to_string(avals(viejo_auditoria),' ', ''))"
                        " @@ websearch_to_tsquery('spanish', %(valor)s)) OR"
                        " (to_tsvector('spanish',"
                        " array_to_string(avals(nuevo_auditoria),' ', ''))"
                        " @@ websearch_to_tsquery('spanish', %(valor)s))"
                        "UNION SELECT * FROM auditoria_cuentas WHERE"
                        " (to_tsvector('spanish',"
                        " array_to_string(avals(viejo_auditoria),' ', ''))"
                        " @@ websearch_to_tsquery('spanish', %(valor)s)) OR"
                        " (to_tsvector('spanish',"
                        " array_to_string(avals(nuevo_auditoria),' ', ''))"
                        " @@ websearch_to_tsquery('spanish', %(valor)s)))"
                    )
                else:
                    consulta = self._gestionar_permisos_buscando_valor(
                        consulta,
                        permisos
                    )
                consulta = consulta + (
                    "AS auditoria INNER JOIN pg_class"
                    " ON auditoria.tabla_auditoria = pg_class.oid"
                    " INNER JOIN pg_attribute"
                    " ON pg_attribute.attrelid = pg_class.oid"
                    " AND pg_attribute.attnum > 0"
                    " LEFT JOIN LATERAL each(viejo_auditoria) AS va"
                    " ON va.key = pg_attribute.attname"
                    " LEFT JOIN LATERAL each(nuevo_auditoria) AS na"
                    " ON na.key = pg_attribute.attname"
                    " WHERE (date_trunc('minute', tiempo_auditoria)"
                    " >= %(inicio)s) AND"
                    " (date_trunc('minute', tiempo_auditoria)"
                    " <= %(fin)s) AND"
                    " (to_tsvector('simple', relname)"
                    " @@ websearch_to_tsquery('simple', %(tabla)s))"
                )
                if (
                    creado_incluido is None or
                    editado_incluido is None or
                    destruido_incluido is None
                ):
                    consulta = self._filtrar(
                        consulta,
                        creado_incluido,
                        editado_incluido,
                        destruido_incluido
                    )
                consulta = consulta + (
                    " GROUP BY id_auditoria, relname, tiempo_auditoria"
                    " ORDER BY tiempo_auditoria DESC;"
                )
                auditoria = Django.objects.raw(
                    consulta,
                    {
                        "tabla": str(busqueda_tabla).strip(),
                        "valor": str(busqueda_valor).strip(),
                        "inicio": tiempo_inicio.replace(
                            tzinfo=timezone.utc
                        ).strftime("%Y-%m-%d %T"),
                        "fin": tiempo_fin.replace(
                            tzinfo=timezone.utc
                        ).strftime("%Y-%m-%d %T")
                    }
                )
            paginador: Paginator = Paginator(
                auditoria,
                self.paginate_by
            )
            objeto_pagina: Page = paginador.get_page(
                request.GET.get("pagina")
            )
            return render(
                request,
                "parciales/_auditoria.html",
                {
                    "queryset": auditoria,
                    "page_obj": objeto_pagina,
                    "htmx": True
                }
            )
        return super(ListView, self).get(request)
