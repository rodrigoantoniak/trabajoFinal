from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import LogoutView
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy

from typing import Optional, Self


class VistaCierreSesion(
    UserPassesTestMixin,
    SuccessMessageMixin,
    LogoutView
):
    next_page: Optional[str] = reverse_lazy('indice')
    success_message: str = "Ha cerrado sesión correctamente."

    def test_func(self: Self) -> bool:
        return self.request.user.is_authenticated

    def handle_no_permission(self: Self) -> HttpResponse:
        return HttpResponseRedirect(self.next_page)
