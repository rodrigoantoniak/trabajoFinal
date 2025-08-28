from typing import Sequence
from ..models import Comitente

from django import forms


class FormularioComitente(forms.ModelForm):
    razon_social_comitente: forms.CharField = \
        forms.CharField(
            label="Razón social"
        )
    cuit_comitente: forms.IntegerField = \
        forms.IntegerField(
            max_value=37999999999,
            min_value=30000000000,
            widget=forms.TextInput,
            label="CUIT"
        )
    firma_digital_comitente: forms.BooleanField = \
        forms.BooleanField(
            label="¿Tiene firma digital?",
            required=False
        )

    class Meta:
        model: type[Comitente] = Comitente
        fields: Sequence[str] = (
            "razon_social_comitente",
            "cuit_comitente",
            "firma_digital_comitente"
        )
