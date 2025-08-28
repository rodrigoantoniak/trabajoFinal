from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import generic

from typing import Any, Dict, Self

from ..models import Comitente, ResponsableTecnico, Secretario

from gesservorconv.mixins import MixinAccesoRequerido


class VistaRegistroComitente(
    MixinAccesoRequerido,
    generic.TemplateView
):
    template_name: str = 'cuentas/registrar_comitente.html'
    login_url: str = reverse_lazy('cuentas:iniciar_sesion')

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

    def post(
        self: Self,
        request: HttpRequest
    ) -> HttpResponse:
        return HttpResponse("")
        descripciones_compromisos_comitente: list[str] = \
            request.POST.getlist(
                "descripcion_compromiso_comitente",
                []
            )
        descripciones_compromisos_unidad_ejecutora: list[str] = \
            request.POST.getlist(
                "descripcion_compromiso_unidad_ejecutora",
                []
            )
        montos_retribuciones_economicas: list[str] = \
            request.POST.getlist(
                "monto_retribucion_economica",
                []
            )
