from django.forms import (
    CharField,
    FileField,
    Form,
    ModelForm,
    PasswordInput
)
from .models import Convenio


class FormularioConvenio(ModelForm):
    class Meta:
        model: type[Convenio] = Convenio
        fields: list[str] = ['archivo_convenio']


class FormularioFirma(Form):
    archivo_firma: FileField = FileField(
        label='Archivo firmante',
        allow_empty_file=False,
        required=True
    )
    contrasenia_firma: CharField = CharField(
        label='Contraseña de firma',
        required=True,
        widget=PasswordInput()
    )


class FormularioEscaneo(Form):
    archivo_escaneo: FileField = FileField(
        label='Archivo escaneado',
        allow_empty_file=False,
        required=True
    )
