from typing import Optional
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Model
from django.views.generic.list import BaseListView


class BaseVistaLista(
    PermissionRequiredMixin,
    BaseListView
):
    model: Optional[Model] = None

    permission_required: Optional[str] = (
        'view_' + model.__name__ if
        model is not None else None
    )
