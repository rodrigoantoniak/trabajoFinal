from typing import Sequence
from ..models import ResponsableTecnico

from django import forms


class FormularioResponsable(forms.ModelForm):
    cuil_responsable: forms.IntegerField = \
        forms.IntegerField(
            max_value=27999999999,
            min_value=20000000000,
            widget=forms.TextInput,
            label="CUIL"
        )
    firma_digital_responsable: forms.BooleanField = \
        forms.BooleanField(
            label="¿Tiene firma digital?",
            required=False
        )

    class Meta:
        model: type[ResponsableTecnico] = ResponsableTecnico
        fields: Sequence[str] = (
            "cuil_responsable",
            "firma_digital_responsable"
        )
