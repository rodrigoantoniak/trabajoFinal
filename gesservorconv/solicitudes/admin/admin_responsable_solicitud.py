from django import forms
from django.contrib import admin

from ..models import ResponsableSolicitud


class FormAdminResponsableSolicitud(forms.ModelForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['tiempo_decision_responsable'].required = False
        self.fields['tiempo_decision_comitente'].required = False
        self.fields['aceptacion_comitente'].required = False
        self.fields['aceptacion_responsable'].required = False

    class Meta:
        model = ResponsableSolicitud
        fields = (
            'responsable_tecnico',
            'solicitud_servicio',
            'tiempo_decision_responsable',
            'tiempo_decision_comitente',
            'aceptacion_comitente',
            'aceptacion_responsable'
        )


class AdminResponsableSolicitud(admin.ModelAdmin):
    form = FormAdminResponsableSolicitud
