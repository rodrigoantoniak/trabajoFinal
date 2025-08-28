from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.views import PasswordResetView
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy

from typing import Self

from ..tokens import generador_token_por_defecto


class VistaRecuperacionCuenta(UserPassesTestMixin, PasswordResetView):
    email_template_name: str = 'correo_recuperacion.html'
    subject_template_name: str = "asunto_correo_recuperacion.txt"
    template_name: str = 'cuentas/recuperar_cuenta.html'
    success_url: str = reverse_lazy('cuentas:recuperar_hecho')
    token_generator: PasswordResetTokenGenerator = \
        generador_token_por_defecto

    def test_func(self: Self) -> bool:
        return self.request.user.is_anonymous

    def handle_no_permission(self: Self) -> HttpResponse:
        return HttpResponseRedirect(reverse_lazy('cuentas:perfil'))
