from django import forms

from ..models import ComitenteSolicitud


class FormularioComitenteSolicitud(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormularioComitenteSolicitud, self).__init__(*args, **kwargs)
        self.empty_permitted = False

    class Meta():
        model = ComitenteSolicitud
        fields = (
            'comitente',
            'valor_campo_direccion'
        )
