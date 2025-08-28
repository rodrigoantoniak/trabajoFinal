from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from typing import Optional, Self


class ValidadorContrasenia:
    """
    Validar que la contraseña tenga letras mayúsculas y
    minúsculas, dígitos y símbolos.
    """

    def validate(
        self: Self,
        password: str,
        user: Optional[User] = None
    ) -> None:
        mayuscula: bool = False
        minuscula: bool = False
        digito: bool = False
        simbolo: bool = False
        for caracter in password:
            if caracter.isupper():
                mayuscula = True
            elif caracter.islower():
                minuscula = True
            elif caracter.isdigit():
                digito = True
            elif (
                caracter.isascii() and
                not caracter.isspace()
            ):
                simbolo = True
            else:
                raise ValidationError(
                    'La contraseña posee un caracter'
                    ' inválido para tal.',
                    code='space_or_non_ascii_in_password'
                )
        if not (
            mayuscula and minuscula and
            digito and simbolo
        ):
            raise ValidationError(
                'La contraseña no tiene al menos un'
                ' tipo de caracter necesario.',
                code='not_varying_char_types_password',
            )

    def get_help_text(self: Self) -> str:
        return 'Su contraseña debe tener una letra' \
               ' mayúscula, una letra minúscula,' \
               ' un dígito y un símbolo. Todos los' \
               ' caracteres deben ser ASCII (no extendido)' \
               ' y no se permite espacios.'
