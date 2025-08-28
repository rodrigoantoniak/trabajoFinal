from typing import Any
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django_hosts.resolvers import reverse

from ..models import ResponsableTecnico


def correo_responsable_a_admin(
    sender: type[ResponsableTecnico],
    instance: ResponsableTecnico,
    created: bool,
    **kwargs: dict[str, Any]
) -> None:
    if created:
        contexto: dict[str, Any] = {
            'perfil': str(ResponsableTecnico._meta.verbose_name).title(),
            'nombre_usuario': instance.usuario_responsable.get_username(),
            'protocolo': 'https' if settings.SECURE_SSL_REDIRECT else 'http',
            'url': reverse(
                viewname='admin:cuentas_responsabletecnico_change',
                host='administrador6' if settings.SECURE_SSL_REDIRECT else
                     'administrador',
                args=[instance.pk]
            ),
        }
        mensaje_html: str = render_to_string(
            template_name='correo_registro.html',
            context=contexto
        )
        mensaje_plano: str = strip_tags(mensaje_html)
        mail.send_mail(
            'Creación de Responsable Técnico',
            mensaje_plano,
            from_email=settings.SERVER_EMAIL,
            recipient_list=[
                admin.email for admin in User.objects.filter(
                    is_active=True,
                    is_staff=True,
                    is_superuser=True,
                )
            ]
        )
