from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.views import PasswordResetConfirmView
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy

from typing import Self

from ..tokens import generador_token_por_defecto


class VistaRecuperacionContrasenia(
    UserPassesTestMixin,
    PasswordResetConfirmView
):
    template_name: str = 'cuentas/recuperar_contrasenia.html'
    success_url: str = reverse_lazy('cuentas:recuperar_completo')
    token_generator: PasswordResetTokenGenerator = \
        generador_token_por_defecto

    def test_func(self: Self) -> bool:
        return self.request.user.is_anonymous

    def handle_no_permission(self: Self) -> HttpResponse:
        return HttpResponseRedirect(self.success_url)
