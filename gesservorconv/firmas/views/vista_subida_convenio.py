from django.contrib import messages
from django.contrib.postgres.functions import TransactionNow
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from typing import Any, Dict, Self

from ..models import Convenio
from ..forms import FormularioConvenio

from cuentas.models import Comitente, ResponsableTecnico, Secretario
from servicios.models import Servicio


class VistaSubidaConvenio(FormView):
    template_name: str = "firmas/subir_convenio.html"
    form_class: type[FormularioConvenio] = FormularioConvenio
    success_url: str = reverse_lazy("firmas:lista_convenios_secretario")

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
        request: HttpRequest,
        convenio: int
    ) -> HttpResponse:
        contexto: Dict[str, Any] = self.get_context_data()
        contexto["convenio"] = convenio
        return render(
            request,
            self.template_name,
            contexto
        )

    def post(
        self: Self,
        request: HttpRequest,
        convenio: int
    ) -> HttpResponse:
        formulario: FormularioConvenio = FormularioConvenio(
            request.POST, request.FILES
        )
        if formulario.is_valid():
            convenio: Convenio = Convenio.objects.get(
                pk=convenio
            )
            convenio.archivo_convenio = request.FILES["archivo_convenio"]
            convenio.tiempo_subida_convenio = TransactionNow()
            servicio: Servicio = Servicio(
                orden_servicio=None,
                convenio=convenio,
                pagado=False,
                completado=False
            )
            with transaction.atomic():
                convenio.save()
                servicio.save()
            messages.success(
                request,
                "Se ha subido el convenio correctamente"
            )
            return HttpResponseRedirect(self.success_url)
