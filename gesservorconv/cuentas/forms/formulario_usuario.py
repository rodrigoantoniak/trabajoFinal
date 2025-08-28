from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from typing import Sequence


class FormularioUsuario(UserCreationForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields[
            'username'
        ].help_text = 'Longitud máxima de 150 caracteres.' \
                      ' Sólo puede estar formado por letras,' \
                      ' números y los caracteres @/./+/-/_.'
        for field in self.fields.keys():
            self.fields[field].required = True

    class Meta(UserCreationForm.Meta):
        model: type[User] = User
        fields: Sequence[str] = \
            tuple(UserCreationForm.Meta.fields) + (
                'email', 'last_name', 'first_name',
                'password1', 'password2',
            )
