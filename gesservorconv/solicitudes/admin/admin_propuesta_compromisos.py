from django import forms
from django.contrib import admin

from ..models import PropuestaCompromisos


class FormAdminPropuestaCompromisos(forms.ModelForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['es_valida_propuesta'].required = False
        self.fields['causa_rechazo_propuesta'].required = False

    class Meta:
        model = PropuestaCompromisos
        fields = (
            'solicitud_servicio_propuesta',
            'descripciones_compromisos_comitente',
            'descripciones_compromisos_unidad_ejecutora',
            'montos_retribuciones_economicas',
            'descripciones_retribuciones_economicas',
            'es_valida_propuesta',
            'causa_rechazo_propuesta'
        )


class AdminPropuestaCompromisos(admin.ModelAdmin):
    form = FormAdminPropuestaCompromisos
