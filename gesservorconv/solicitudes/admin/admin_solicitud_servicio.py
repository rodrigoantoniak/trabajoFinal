from django import forms
from django.contrib import admin

from ..models import SolicitudServicio


class FormAdminSolicitudServicio(forms.ModelForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['cancelacion_solicitud'].required = False
        self.fields['solicitud_suspendida'].required = False

    class Meta:
        model = SolicitudServicio
        fields = (
            'nombre_solicitud',
            'descripcion_solicitud',
            'cancelacion_solicitud',
            'solicitud_suspendida'
        )


class AdminSolicitudServicio(admin.ModelAdmin):
    form = FormAdminSolicitudServicio
