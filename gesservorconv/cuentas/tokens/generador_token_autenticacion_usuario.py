from django.conf import settings
from django.contrib.auth.models import User
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.http import base36_to_int, int_to_base36

from typing import Optional, Self
from collections.abc import Iterable
from datetime import datetime


class GeneradorTokenAutenticacionUsuario():
    sal_clave: str = settings.USER_AUTHENTICATION_TOKEN_GENERATOR_KEY_SALT
    algoritmo: Optional[str] = "sha3_256"
    _secreto: Optional[str] = None
    _alternativas_secreto: Optional[Iterable[str]] = None

    def _acceder_secreto(self: Self) -> str:
        return self._secreto or settings.SECRET_KEY

    def _mutar_secreto(self: Self, secreto: str) -> None:
        self._secreto = secreto

    secreto: property = property(_acceder_secreto, _mutar_secreto)

    def _acceder_alternativas(self: Self) -> Iterable[str]:
        if self._alternativas_secreto is None:
            return settings.SECRET_KEY_FALLBACKS
        return self._alternativas_secreto

    def _mutar_alternativas(
        self: Self,
        alternativas: Iterable[str]
    ):
        self._alternativas_secreto = alternativas

    alternativas_secreto: property = property(
        _acceder_alternativas,
        _mutar_alternativas
    )

    def crear_token(self: Self, usuario: User, codigo: str) -> str:
        """
        Devolver un token que puede ser usado una vez para habilitar
        al usuario en cuestión.
        """
        return self._hacer_token_con_marca_tiempo(
            usuario,
            self._num_segundos(self._ahora()),
            self.secreto,
            codigo
        )

    def revisar_token(
        self: Self,
        usuario: Optional[User],
        token: Optional[str],
        codigo: Optional[str]
    ) -> bool:
        """
        Revisar que un código de autenticación sea el correo para
        un token determinado.
        """
        if not (usuario and token and codigo):
            return False
        partes: tuple[str, str, str] = token.partition("-")
        if (partes[1] != "-") or ("-" in partes[2]):
            return False
        mt_b36: str = partes[0]
        try:
            mt: int = base36_to_int(mt_b36)
        except ValueError:
            return False
        for secreto in [self.secreto, *self.alternativas_secreto]:
            if constant_time_compare(
                self._hacer_token_con_marca_tiempo(
                    usuario,
                    mt,
                    secreto,
                    codigo
                ),
                token,
            ):
                break
        else:
            return False
        if (
            (self._num_segundos(self._ahora()) - mt) >
            settings.PASSWORD_RESET_TIMEOUT
        ):
            return False
        return True

    def _hacer_token_con_marca_tiempo(
        self: Self,
        usuario: User,
        marca_tiempo: int,
        secreto: str,
        codigo: str
    ) -> str:
        mt_b36: str = int_to_base36(marca_tiempo)
        cadena_hash: str = salted_hmac(
            self.sal_clave,
            self._hacer_valor_hash(usuario, marca_tiempo, codigo),
            secret=secreto,
            algorithm=self.algoritmo,
        ).hexdigest()[::2]
        return f"{mt_b36}-{cadena_hash}"

    def _hacer_valor_hash(
        self: Self,
        usuario: User,
        marca_tiempo: int,
        codigo: str
    ) -> str:
        """
        Codifica la clave primaria del usuario, correo electrónico, y un estado
        de usuario que es seguro que cambie tras activar la cuenta para
        producir un token que sea invalidado al ser usado:
        1. El campo que asienta si el usuario está activo o no; ya que al
        activar la cuenta, el valor del campo cambia de falso a verdadero.
        En caso de que fallen tales, settings.PASSWORD_RESET_TIMEOUT invalidará
        eventualmente el token.

        Al pasar estos datos por salted_hmac(), se previene la activación
        indebida de la cuenta con el token, lo cual prueba que el secreto
        no está comprometido.
        """
        ultimo_inicio_sesion = (
            ""
            if usuario.last_login is None
            else usuario.last_login.replace(microsecond=0, tzinfo=None)
        )
        return f"{usuario.pk}{usuario.password}{ultimo_inicio_sesion}" \
               f"{marca_tiempo}{usuario.email}{codigo}"

    def _num_segundos(self: Self, dt: datetime) -> int:
        return int((dt - datetime(2001, 1, 1)).total_seconds())

    def _ahora(self: Self) -> datetime:
        return datetime.now()


generador_token_autenticacion_usuario: GeneradorTokenAutenticacionUsuario = \
    GeneradorTokenAutenticacionUsuario()
