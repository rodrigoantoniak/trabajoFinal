from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator

from typing import Optional


class GeneradorTokenRecuperacionContrasenia(
    PasswordResetTokenGenerator
):
    key_salt: str = settings.PASSWORD_RESET_TOKEN_GENERATOR_KEY_SALT
    algorithm: Optional[str] = "sha3_256"


generador_token_por_defecto: GeneradorTokenRecuperacionContrasenia = \
    GeneradorTokenRecuperacionContrasenia()
