import json
from typing import Any, Union
from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.models import Session
from django.core.exceptions import BadRequest
from django.core.serializers import serialize
from django.db.models import QuerySet
from django.http import JsonResponse, HttpRequest
from django.views import generic

from datetime import datetime, timedelta, timezone


class ControladorUsuario(generic.View):
    def get(self, request: HttpRequest) -> JsonResponse:
        usuario: Union[User, AnonymousUser] = get_user(request)
        sesion_cliente: QuerySet[Session] = Session.objects.filter(
            pk=request.session.session_key
        )
        if (
            usuario.is_anonymous or
            sesion_cliente.count() == 0 or
            sesion_cliente.first().expire_date <= datetime.now(timezone.utc)
        ):
            raise BadRequest(
                'Para autenticarse, requiere de "usuario" y "contrasenia"'
            )
        usuarios: QuerySet[User] = User.objects.filter(
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        cadena: str = serialize(
            format='json',
            queryset=usuarios,
            fields=[
                'username',
                'email',
                'last_name',
                'first_name'
            ]
        )
        lista: list[dict[str, Any]] = json.loads(cadena)
        api: dict[int, Any] = {}
        for i, elemento in enumerate(lista):
            api[i] = elemento['fields']
        respuesta: JsonResponse = JsonResponse(
            api,
            headers={
                'Content-Language': 'es-AR'
            }
        )
        sesion: Session = sesion_cliente.first()
        sesion.expire_date = \
            datetime.now(timezone.utc) + \
            timedelta(seconds=settings.SESSION_COOKIE_AGE)
        sesion.save()
        respuesta.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=sesion.session_key,
            max_age=settings.SESSION_COOKIE_AGE,
            path=settings.SESSION_COOKIE_PATH,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            samesite=settings.SESSION_COOKIE_SAMESITE
        )
        return respuesta
