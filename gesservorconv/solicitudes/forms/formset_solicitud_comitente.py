from django import forms

from typing import NewType

from ..models import SolicitudServicio, ComitenteSolicitud

formset_comitentes_solicitud: NewType = forms.inlineformset_factory(
    parent_model=SolicitudServicio,
    model=ComitenteSolicitud,
    form=FormularioDireccion,
    fields=(
        "tipo_campo_direccion",
        "valor_campo_direccion"
    ),
    min_num=1,
    validate_min=True
)
