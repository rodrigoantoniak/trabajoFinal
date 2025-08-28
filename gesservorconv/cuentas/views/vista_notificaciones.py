from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Page, Paginator
from django.db.models import Q
from django.db.models.query import QuerySet
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import ListView

from typing import Any, Dict, Optional, Self

from ..models import (
    Comitente,
    Notificacion,
    ResponsableTecnico,
    Secretario
)

from gesservorconv.views import HtmxHttpRequest


class VistaNotificaciones(
    LoginRequiredMixin,
    ListView
):
    model: type[Notificacion] = Notificacion
    template_name: str = "cuentas/listar_notificaciones.html"
    paginate_by: int = 10
    page_kwarg: Optional[str] = None
    allow_empty: bool = True

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

    def get_queryset(self: Self) -> QuerySet[Notificacion]:
        notificaciones: QuerySet[Notificacion] = \
            Notificacion.objects.filter(
                usuario_notificacion=self.request.user
            ).order_by(
                "-tiempo_notificacion"
            )
        return notificaciones

    def get(self: Self, request: HtmxHttpRequest) -> HttpResponse:
        if request.htmx:
            notificaciones: QuerySet[Notificacion] = \
                self.get_queryset()
            paginador: Paginator = Paginator(
                notificaciones,
                self.paginate_by
            )
            objeto_pagina: Page = paginador.get_page(
                request.GET.get("pagina")
            )
            return render(
                request,
                "parciales/_lista_solicitudes_comitente.html",
                {
                    "queryset": notificaciones,
                    "page_obj": objeto_pagina
                }
            )
        return super(ListView, self).get(request)
