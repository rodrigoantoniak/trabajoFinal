from django.contrib import admin

from .models import Convenio, FirmaOrden, OrdenServicio

admin.site.register(OrdenServicio)
admin.site.register(FirmaOrden)
admin.site.register(Convenio)
