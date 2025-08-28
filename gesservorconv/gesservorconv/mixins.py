from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin
)
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.db.models.query import QuerySet
from django.shortcuts import resolve_url
from django.urls import reverse_lazy

from typing import Optional, Self
from urllib.parse import urlparse


class MixinAccesoRequerido(LoginRequiredMixin):
    login_url: Optional[str] = reverse_lazy("cuentas:iniciar_sesion")
    redirect_field_name: str = "siguiente"

    def handle_no_permission(self: Self):
        if self.raise_exception or self.request.user.is_authenticated:
            raise PermissionDenied(self.get_permission_denied_message())
        path = self.request.build_absolute_uri()
        resolved_login_url = resolve_url(self.get_login_url())
        login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
        current_scheme, current_netloc = urlparse(path)[:2]
        if (not login_scheme or login_scheme == current_scheme) and (
            not login_netloc or login_netloc == current_netloc
        ):
            path = self.request.get_full_path()
        messages.warning(
            self.request,
            'La sesión ha caducado'
        )
        return redirect_to_login(
            path,
            resolved_login_url,
            self.get_redirect_field_name(),
        )


class MixinPermisoRequerido(PermissionRequiredMixin):
    def has_permission(self: Self) -> bool:
        permisos: QuerySet[Permission] = self.get_permission_required()
        return set(
            f"{permiso.content_type.app_label}.{permiso.codename}"
            for permiso in permisos
        ).issubset(self.request.user.get_all_permissions())
