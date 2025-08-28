from django.conf import settings
from django.core import mail
from django.template import Template
from django.template.context import Context
from django.template.loader import get_template, render_to_string
from django_hosts.resolvers import get_host

from re import DOTALL, findall, MULTILINE, S, sub
from typing import Any

from ..models import Notificacion

from gesservorconv.hosts import puerto


def correo_notificacion(
    sender: type[Notificacion],
    instance: Notificacion,
    created: bool,
    **kwargs: dict[str, Any]
) -> None:
    if created:
        contexto: dict[str, Any] = {
            'notificacion': instance,
            'protocolo': 'https' if settings.SECURE_SSL_REDIRECT else 'http',
            'dominio': f'{get_host().regex}:{puerto}'
                       if puerto else get_host().regex,
        }
        mensaje_html: str = render_to_string(
            template_name='correo_notificacion.html',
            context=contexto
        )
        plantilla: str = get_template(
            template_name='correo_notificacion.html'
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
            instance.titulo_notificacion,
            message=mensaje_plano.render(context=Context(contexto)),
            html_message=mensaje_html,
            from_email=settings.SERVER_EMAIL,
            recipient_list=[instance.usuario_notificacion.email]
        )
