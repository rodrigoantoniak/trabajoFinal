from .correo_activacion_a_usuario import correo_activacion_a_usuario
from .correo_comitente_a_admin import correo_comitente_a_admin
from .correo_responsable_a_admin import correo_responsable_a_admin
from .correo_notificacion import correo_notificacion
from .habilitacion_a_comitente import habilitacion_a_comitente

from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save

from ..models import Notificacion, Comitente, ResponsableTecnico


post_save.connect(correo_activacion_a_usuario, User)
post_save.connect(correo_comitente_a_admin, Comitente)
post_save.connect(correo_responsable_a_admin, ResponsableTecnico)
post_save.connect(correo_notificacion, Notificacion)
pre_save.connect(habilitacion_a_comitente, Comitente)
