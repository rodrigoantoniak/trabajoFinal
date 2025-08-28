from django.forms import ModelForm

from .models import Pago, Progreso


class FormularioProgreso(ModelForm):
    class Meta:
        model: type[Progreso] = Progreso
        fields: list[str] = [
            'descripcion_progreso',
            'porcentaje_progreso'
        ]


class FormularioPago(ModelForm):
    class Meta:
        model: type[Pago] = Pago
        fields: list[str] = [
            'comitente_pago',
            'monto_pago'
        ]
