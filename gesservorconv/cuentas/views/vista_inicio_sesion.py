from django.conf import settings
from django.core import mail
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import Template
from django.template.context import Context
from django.template.loader import get_template, render_to_string
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from django_ratelimit import UNSAFE
from django_ratelimit.core import get_usage
from django_ratelimit.decorators import ratelimit

from random import choice
from re import DOTALL, findall, MULTILINE, S, sub
from string import ascii_letters, digits
from typing import Any, Dict, Optional, Self

from ..tokens import generador_token_autenticacion_usuario


def _clave(group: str, request: HttpRequest) -> str:
    return (
        request.META['REMOTE_ADDR'] +
        request.POST.get('username')
    )


@method_decorator(
    ratelimit(
        group='vista_inicio_sesion',
        key=_clave,
        rate='5/h',
        method='POST',
        block=False
    ),
    name='post'
)
class VistaInicioSesion(UserPassesTestMixin, LoginView):
    template_name: str = 'cuentas/iniciar_sesion.html'
    redirect_authenticated_user: bool = True
    next_page: str = reverse_lazy('cuentas:perfil')

    def test_func(self: Self) -> bool:
        return self.request.user.is_anonymous

    def handle_no_permission(self: Self) -> HttpResponse:
        return HttpResponseRedirect(self.next_page)

    def get_context_data(self: Self, **kwargs: Dict[str, Any]):
        contexto: Dict[str, Any] = super().get_context_data(**kwargs)
        contexto['siguiente'] = self.request.GET.get('siguiente')
        return contexto

    def post(self: Self, request: HttpRequest) -> HttpResponse:
        esta_limitado: bool = getattr(request, 'limited', False)
        if esta_limitado:
            uso: Optional[dict[str, int | bool]] = get_usage(
                request,
                group='vista_inicio_sesion',
                key=_clave,
                rate='5/h',
                method=UNSAFE,
                increment=True
            )
            if uso:
                if uso['should_limit']:
                    messages.error(
                        request,
                        'Se ha excedido el límite de inicios de'
                        ' sesión por hora. Inténtelo de nuevo'
                        f' dentro de {uso["time_left"]} segundos.'
                    )
                    respuesta: HttpResponse = render(
                        request,
                        self.template_name,
                        status=429
                    )
                    respuesta.headers['Retry-After'] = uso["time_left"]
                    return respuesta
        return super().post(request)

    def form_valid(
        self: Self,
        form: AuthenticationForm
    ) -> HttpResponse:
        usuario: User = form.get_user()
        siguiente: Optional[str] = self.request.POST.get('siguiente')
        caracteres: str = ascii_letters + digits
        codigo: str = ''
        for i in range(6):
            codigo = codigo + choice(caracteres)
        contexto_correo: dict[str, Any] = {
            'protocolo': 'https' if settings.SECURE_SSL_REDIRECT else 'http',
            'dominio': self.request.get_host(),
            'nombre_usuario': usuario.username,
            'codigo': codigo,
        }
        mensaje_html: str = render_to_string(
            template_name='correo_autenticacion_usuario.html',
            context=contexto_correo
        )
        plantilla: str = get_template(
            template_name='correo_autenticacion_usuario.html'
        )
        contenido_plano: str = ''
        bloque_procesado: str
        for texto in findall(
            r'>[^><]*[^><\s]+[^><]*<\/',
            plantilla.template.source,
            DOTALL | MULTILINE | S
        ):
            bloque_procesado = sub(
                r'\s+', ' ',
                ' '.join(texto[1:-2].split()), 0,
                DOTALL | MULTILINE | S
            )
            contenido_plano = f'{contenido_plano}{bloque_procesado}\n'
        mensaje_plano: Template = Template(
            template_string=contenido_plano
        )
        mail.send_mail(
            subject='Autenticación de inicio de sesión',
            message=mensaje_plano.render(context=Context(contexto_correo)),
            html_message=mensaje_html,
            from_email=settings.SERVER_EMAIL,
            recipient_list=[usuario.email]
        )
        enlace: str = reverse_lazy(
            viewname='cuentas:autenticar_usuario',
            args=[
                urlsafe_base64_encode(force_bytes(usuario.pk)),
                generador_token_autenticacion_usuario.crear_token(
                    usuario, codigo
                )
            ]
        )
        if siguiente:
            enlace = f'{enlace}?siguiente={siguiente}'
        return HttpResponseRedirect(enlace)
