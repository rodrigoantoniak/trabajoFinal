from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.template import Template
from django.template.context import Context
from django.template.loader import get_template, render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_hosts.resolvers import get_host, reverse

from re import DOTALL, findall, MULTILINE, S, sub
from typing import Any

from ..tokens import generador_token_activacion_cuenta

from gesservorconv.hosts import puerto


def correo_activacion_a_usuario(
    sender: type[User],
    instance: User,
    created: bool,
    **kwargs: dict[str, Any]
) -> None:
    if created and not instance.is_active:
        contexto: dict[str, Any] = {
            'nombre_usuario': instance.username,
            'protocolo': 'https' if settings.SECURE_SSL_REDIRECT else 'http',
            'dominio': f'{get_host().regex}:{puerto}'
                       if puerto else get_host().regex,
            'url': reverse(
                viewname='cuentas:activar_cuenta',
                host=settings.DEFAULT_HOST,
                args=[
                    urlsafe_base64_encode(force_bytes(instance.pk)),
                    generador_token_activacion_cuenta.crear_token(instance)
                ]
            ),
        }
        mensaje_html: str = render_to_string(
            template_name='correo_activacion_usuario.html',
            context=contexto
        )
        plantilla: str = get_template(
            template_name='correo_activacion_usuario.html'
        )
        contenido_plano: str = ''
        bloque_procesado: str
        for texto in findall(
            r">[^><]*[^><\s]+[^><]*<\/",
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
            subject='Activación de usuario',
            message=mensaje_plano.render(context=Context(contexto)),
            html_message=mensaje_html,
            from_email=settings.SERVER_EMAIL,
            recipient_list=[instance.email]
        )
