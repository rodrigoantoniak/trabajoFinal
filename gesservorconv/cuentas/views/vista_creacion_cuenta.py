from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import generic

from typing import Self

from .. import forms


class VistaCreacionCuenta(
    UserPassesTestMixin,
    SuccessMessageMixin,
    generic.CreateView
):
    model: type[User] = User
    template_name: str = "cuentas/crear_cuenta.html"
    form_class: type[forms.FormularioUsuario] = forms.FormularioUsuario
    success_url: str = reverse_lazy("cuentas:iniciar_sesion")
    success_message: str = \
        "El usuario %(username)s fue creado correctamente." \
        " Se ha enviado un correo electrónico para activar su cuenta."

    def test_func(self: Self) -> bool:
        return self.request.user.is_anonymous

    def handle_no_permission(self: Self) -> HttpResponse:
        return HttpResponseRedirect(reverse_lazy("cuentas:perfil"))

    def form_valid(self: Self, form: forms.FormularioUsuario) -> HttpResponse:
        self.object: forms.FormularioUsuario = form.save(commit=False)
        self.object.is_active = False
        self.object.save()
        respuesta: HttpResponse = HttpResponseRedirect(self.success_url)
        messages.success(
            self.request,
            self.success_message % {"username": self.object.username}
        )
        return respuesta
