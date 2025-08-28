from django import forms
from django.contrib import admin

from ..models import ResponsableTecnico


class FormAdminResponsableTecnico(forms.ModelForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['firma_digital_responsable'].required = False
        self.fields['habilitado_responsable'].required = False
        self.fields['razones_sociales_responsable'].required = False
        self.fields['cuit_organizaciones_responsable'].required = False
        self.fields['puestos_organizaciones_responsable'].required = False
        self.fields['habilitado_organizaciones_responsable'].required = False

    class Meta:
        model = ResponsableTecnico
        fields = (
            'usuario_responsable',
            'cuil_responsable',
            'firma_digital_responsable',
            'habilitado_responsable',
            'razones_sociales_responsable',
            'cuit_organizaciones_responsable',
            'puestos_organizaciones_responsable',
            'habilitado_organizaciones_responsable'
        )


class AdminResponsableTecnico(admin.ModelAdmin):
    form = FormAdminResponsableTecnico
