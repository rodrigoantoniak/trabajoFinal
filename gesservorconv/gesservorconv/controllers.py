from datetime import datetime, timedelta, timezone
from typing import Any, Optional, TypeAlias, Union

from django.conf import settings
from django.contrib.auth import authenticate, get_user, login, logout
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.backends.cached_db import SessionStore
from django.contrib.sessions.models import Session
from django.core.exceptions import BadRequest, PermissionDenied
from django.db.models.query import QuerySet
from django.http import JsonResponse, HttpRequest
from django.middleware import csrf
from django.urls import URLPattern, URLResolver
from django.views import generic

from gesservorconv import apis


DicRecursivo: TypeAlias = dict[str, Union[str, 'DicRecursivo']]


def rutas(urls: list[URLPattern | URLResolver]) -> DicRecursivo:
    retorno: dict[str, Any] = {}
    for url in urls:
        if isinstance(url, URLPattern):
            retorno[f'/{str(url.pattern)}'] = url.name
        elif isinstance(url, URLResolver):
            subrutas: list[URLPattern | URLResolver] = getattr(
                url.urlconf_name, 'urlpatterns', url.urlconf_name
            )
            if str(url.pattern) == '':
                retorno.update(rutas(subrutas))
            else:
                retorno[
                    f'/{str(url.pattern).removesuffix("/")}'
                ] = rutas(subrutas)
        else:
            raise AttributeError('Parámetro equivocado')
    return retorno


class ControladorBase(generic.View):
    def get(self, request: HttpRequest) -> JsonResponse:
        usuario: Union[User, AnonymousUser] = get_user(request)
        sesion_cliente: QuerySet[Session] = Session.objects.filter(
            pk=request.session.session_key,
            expire_date__gt=datetime.now(timezone.utc)
        )
        respuesta: JsonResponse
        if usuario.is_anonymous or sesion_cliente.count() == 0:
            sesiones_expiradas: QuerySet[Session] = Session.objects.filter(
                pk=request.session.session_key,
                expire_date__lte=datetime.now(timezone.utc)
            )
            sesiones_expiradas.delete()
            respuesta = JsonResponse(
                {
                    'usuario': 'text',
                    'contrasenia': 'password'
                },
                headers={
                    'Content-Language': 'es-AR',
                }
            )
            sesion_servidor: SessionStore = SessionStore()
            sesion_servidor.create()
            sesion_servidor.setdefault(
                csrf.CSRF_SESSION_KEY,
                csrf.get_token(request)
            )
            sesion_servidor.modified = True
            respuesta.set_cookie(
                key=settings.CSRF_COOKIE_NAME,
                value=csrf.get_token(request),
                max_age=settings.CSRF_COOKIE_AGE,
                path=settings.CSRF_COOKIE_PATH,
                secure=settings.CSRF_COOKIE_SECURE,
                httponly=settings.SESSION_COOKIE_HTTPONLY,
                samesite=settings.CSRF_COOKIE_SAMESITE
            )
            respuesta.set_cookie(
                key=settings.SESSION_COOKIE_NAME,
                value=sesion_servidor.session_key,
                max_age=settings.SESSION_COOKIE_AGE,
                path=settings.SESSION_COOKIE_PATH,
                secure=settings.SESSION_COOKIE_SECURE,
                httponly=settings.SESSION_COOKIE_HTTPONLY,
                samesite=settings.SESSION_COOKIE_SAMESITE
            )
            return respuesta
        api: dict[str, Any] = rutas(apis.urlpatterns)
        respuesta = JsonResponse(
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

    def post(self, request: HttpRequest) -> JsonResponse:
        nombre_usuario: Optional[str] = request.POST.get('usuario')
        contrasenia: Optional[str] = request.POST.get('contrasenia')
        token: Optional[str] = request.headers.get('X-CSRFToken')
        if nombre_usuario is None or contrasenia is None or token is None:
            return JsonResponse(
                status=403,
                data={
                    'codigo': 'Acceso denegado',
                    'excepcion': 'Para autenticarse, requiere de'
                                 ' "usuario" y "contrasenia"'
                },
                headers={
                    'Content-Language': 'es-AR'
                }
            )
        print(token)
        print(request.session[csrf.CSRF_SESSION_KEY])
        if token != request.session[csrf.CSRF_SESSION_KEY]:
            pass
        usuario: User = authenticate(
            request,
            username=nombre_usuario,
            password=contrasenia
        )
        if usuario is None:
            raise BadRequest(
                'Los datos de usuario y/o contrasenia no son correctos'
            )
        if not (usuario.is_active and usuario.is_superuser):
            return JsonResponse(
                status=403,
                data={
                    'codigo': 'Acceso denegado',
                    'excepcion': 'Los permisos del usuario no son adecuados'
                },
                headers={
                    'Content-Language': 'es-AR'
                }
            )
        login(request, usuario)
        csrf.rotate_token(request)
        respuesta: JsonResponse = JsonResponse(
            data={
                'codigo': 'Exito'
            },
            headers={
                'Content-Language': 'es-AR'
            }
        )
        respuesta.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=request.session.session_key,
            max_age=settings.SESSION_COOKIE_AGE,
            path=settings.SESSION_COOKIE_PATH,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            samesite=settings.SESSION_COOKIE_SAMESITE
        )
        return respuesta


class ControladorCierreSesion(generic.View):
    def get(self, request: HttpRequest) -> JsonResponse:
        logout(request)
        respuesta: JsonResponse = JsonResponse(
            {},
            headers={
                'Content-Language': 'es-AR'
            }
        )
        return respuesta
