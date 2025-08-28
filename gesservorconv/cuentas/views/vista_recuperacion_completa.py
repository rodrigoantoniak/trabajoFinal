from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import PasswordResetCompleteView
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy

from typing import Self


class VistaRecuperacionCompleta(
    UserPassesTestMixin,
    PasswordResetCompleteView
):
    template_name: str = 'cuentas/recuperar_completado.html'

    def test_func(self: Self) -> bool:
        return self.request.user.is_anonymous

    def handle_no_permission(self: Self) -> HttpResponse:
        return HttpResponseRedirect(reverse_lazy('cuentas:perfil'))
