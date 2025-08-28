from django import forms
from django.contrib import admin

from typing import Self

from ..models import Comitente


class FormAdminComitente(forms.ModelForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['firma_digital_comitente'].required = False
        self.fields['habilitado_comitente'].required = False
        self.fields['razones_sociales_comitente'].required = False
        self.fields['cuit_organizaciones_comitente'].required = False
        self.fields['puestos_organizaciones_comitente'].required = False
        self.fields['habilitado_organizaciones_comitente'].required = False

    def clean(self: Self):
        super().clean()

    class Meta:
        model = Comitente
        fields = (
            'usuario_comitente',
            'cuil_comitente',
            'firma_digital_comitente',
            'habilitado_comitente',
            'razones_sociales_comitente',
            'cuit_organizaciones_comitente',
            'puestos_organizaciones_comitente',
            'habilitado_organizaciones_comitente'
        )


class AdminComitente(admin.ModelAdmin):
    form = FormAdminComitente
