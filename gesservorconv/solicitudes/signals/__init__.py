from .comitentes_asociados import comitentes_asociados
from .responsables_tecnicos import responsables_tecnicos
from .propuesta_comitente import propuesta_comitente

from django.db.models.signals import post_save

from ..models import (
    ComitenteSolicitud,
    ResponsableSolicitud,
    DecisionComitentePropuesta
)


post_save.connect(comitentes_asociados, ComitenteSolicitud)
post_save.connect(responsables_tecnicos, ResponsableSolicitud)
post_save.connect(propuesta_comitente, DecisionComitentePropuesta)
