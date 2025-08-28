from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.template import Template
from django.template.context import Context
from django.template.loader import get_template, render_to_string
from django_hosts.resolvers import get_host, reverse

from re import DOTALL, findall, MULTILINE, S, sub
from typing import Any

from ..models import Comitente

from gesservorconv.hosts import puerto


def correo_comitente_a_admin(
    sender: type[Comitente],
    instance: Comitente,
    created: bool,
    **kwargs: dict[str, Any]
) -> None:
    if (
        created and
        (
            instance.habilitado_comitente is None or
            any(
                habilitado is None for habilitado in
                instance.habilitado_organizaciones_comitente
            )
        )
    ):
        contexto: dict[str, Any] = {
            'perfil': str(Comitente._meta.verbose_name).title(),
            'usuario': instance.usuario_comitente,
            'protocolo': 'https' if settings.SECURE_SSL_REDIRECT else 'http',
            'dominio': f'{get_host().regex}:{puerto}'
                       if puerto else get_host().regex,
            'cuil': (
                instance.cuil_comitente if
                instance.habilitado_comitente is None else
                None
            ),
            'organizaciones': [
                f'{instance.puestos_organizaciones_comitente[i]} -'
                f' {instance.razones_sociales_comitente[i]}. CUIT:'
                f' {instance.cuit_organizaciones_comitente[i]}'
                for i, nulo in enumerate(
                    instance.habilitado_organizaciones_comitente
                ) if nulo is None
            ],
            'url': reverse(
                viewname='admin:cuentas_comitente_change',
                host='administrador6' if settings.SECURE_SSL_REDIRECT else
                     'administrador',
                args=[instance.pk]
            ),
        }
        mensaje_html: str = render_to_string(
            template_name='correo_registro.html',
            context=contexto
        )
        plantilla: str = get_template(
            template_name='correo_registro.html'
        )
        contenido_plano: str = ''
        bloque_procesado: str
        for texto in findall(
            r">[^><]*[^><\s]+[^><]*<",
            plantilla.template.source.replace(
                "<li>",
                "<li>* "
            ),
            DOTALL | MULTILINE | S
        ):
            bloque_procesado = sub(
                r'\s+', ' ',
                ' '.join(texto[1:-1].split()), 0,
                DOTALL | MULTILINE | S
            )
            contenido_plano = f'{contenido_plano}{bloque_procesado}\n'
        mensaje_plano: Template = Template(
            template_string=contenido_plano
        )
        mail.send_mail(
            'Habilitaciones de Comitente',
            message=mensaje_plano.render(context=Context(contexto)),
            html_message=mensaje_html,
            from_email=settings.SERVER_EMAIL,
            recipient_list=[
                admin.email for admin in User.objects.filter(
                    is_active=True,
                    is_superuser=True,
                )
            ]
        )
