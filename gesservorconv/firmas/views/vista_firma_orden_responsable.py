from django.conf import settings
from django.contrib import messages
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.functions import TransactionNow
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import (
    Case, CharField, DecimalField, F, Min, Model, Q, QuerySet, Value, When
)
from django.db.models.fields.files import FieldFile
from django.db.models.functions import Cast, Concat
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import to_locale
from django.views.generic import FormView

from babel.dates import format_datetime
from babel.numbers import format_decimal
from cryptography.hazmat import backends
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import Certificate
from datetime import datetime, timedelta
from decimal import Decimal
from endesive.pdf import cms
from pytz import timezone
from reportlab.lib.units import mm
from typing import Any, Dict, Optional, Self

from ..forms import FormularioFirma
from ..models import FirmaOrden, OrdenServicio

from cuentas.models import Comitente, ResponsableTecnico, Secretario
from solicitudes.models import (
    PropuestaCompromisos,
    ResponsableSolicitud
)
from servicios.models import Servicio


class VistaFirmaOrdenResponsable(FormView):
    template_name: str = "firmas/firma_orden_responsable.html"
    form_class: type[FormularioFirma] = FormularioFirma
    success_url: str = reverse_lazy("firmas:lista_ordenes_responsable")

    def get_context_data(
        self: Self,
        **kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        contexto: Dict[str, Any] = super().get_context_data(**kwargs)
        contexto["usuario"] = self.request.user
        contexto["comitente"] = Comitente.objects.filter(
            Q(usuario_comitente=self.request.user) &
            (
                Q(habilitado_comitente=True) |
                Q(habilitado_organizaciones_comitente__contains=[
                    True
                ])
            )
        ).exists() if Comitente.objects.filter(
            Q(usuario_comitente=self.request.user) &
            Q(usuario_comitente__is_active=True)
        ).exists() else None
        contexto["responsable"] = ResponsableTecnico.objects.filter(
            Q(usuario_responsable=self.request.user) &
            (
                Q(habilitado_responsable=True) |
                Q(habilitado_organizaciones_responsable__contains=[
                    True
                ])
            )
        ).exists() if ResponsableTecnico.objects.filter(
            Q(usuario_responsable=self.request.user) &
            Q(usuario_responsable__is_active=True)
        ).exists() else None
        contexto["secretario"] = Secretario.objects.filter(
            Q(usuario_secretario=self.request.user) &
            Q(habilitado_secretario=True)
        ).exists() if Secretario.objects.filter(
            Q(usuario_secretario=self.request.user) &
            Q(usuario_secretario__is_active=True)
        ).exists() else None
        contexto["staff"] = self.request.user.is_staff
        contexto["admin"] = self.request.user.is_superuser
        return contexto

    def get(
        self: Self,
        request: HttpRequest,
        orden: int
    ) -> HttpResponse:
        contexto: Dict[str, Any] = self.get_context_data()
        contexto["orden"] = orden
        return render(
            request,
            self.template_name,
            contexto
        )

    def post(
        self: Self,
        request: HttpRequest,
        orden: int
    ) -> HttpResponse:
        formulario: FormularioFirma = self.form_class(
            request.POST, request.FILES
        )
        if formulario.is_valid():
            orden_servicio: OrdenServicio = OrdenServicio.objects.get(
                solicitud_servicio__id_solicitud=orden
            )
            firma: FirmaOrden = FirmaOrden.objects.get(
                orden_firmada=orden_servicio,
                usuario_firmante=request.user
            )
            p12: tuple[
                Optional[Any],
                Optional[Certificate],
                list[Certificate]
            ] = pkcs12.load_key_and_certificates(
                request.FILES["archivo_firma"].read(),
                request.POST.get("contrasenia_firma").encode("ascii"),
                backends.default_backend()
            )
            documento_a_firmar: ContentFile = (
                FirmaOrden.objects.filter(
                    Q(orden_firmada__solicitud_servicio__id_solicitud=orden) &
                    Q(tiempo_firma__isnull=False)
                ).order_by(
                    "-tiempo_firma"
                ).first().documento_firmado.open()
            )
            numero_firma: int = FirmaOrden.objects.filter(
                Q(orden_firmada__solicitud_servicio__id_solicitud=orden) &
                Q(tiempo_firma__isnull=False)
            ).count() + 1
            offset: str = datetime.now(
                timezone(settings.TIME_ZONE)
            ).astimezone().strftime("%z")
            firmado: bytes = cms.sign(
                documento_a_firmar.read(),
                {
                    "aligned": 0,
                    "sigflags": 3,
                    "sigflagsft": 123,
                    "sigpage": firma.pagina_firma-1,
                    "sigfield": f"Firma {numero_firma}",
                    "auto_sigfield": True,
                    "signform": False,
                    "sigandcertify": True,
                    "signaturebox": (
                        firma.coord_x_firma + 5*mm,
                        firma.coord_y_firma - 5*mm,
                        firma.coord_x_firma + 45*mm,
                        firma.coord_y_firma - 32.5*mm,
                    ),
                    "signature": f"{firma.usuario_firmante.last_name},"
                                 f" {firma.usuario_firmante.first_name}",
                    "signature_img_distort": False,
                    "contact": firma.usuario_firmante.email,
                    "location": "Posadas, Misiones, Argentina",
                    "signingdate": datetime.now(
                        timezone(settings.TIME_ZONE)
                    ).strftime(
                        "D:%Y%m%d%H%M%S"
                    ) + f"{offset[:3]}'{offset[3:]}'",
                    "reason": "Responsable Técnico"
                },
                p12[0],
                p12[1],
                p12[2],
                "sha256"
            )
            # Cerrar y volver a abrir el archivo resulta más seguro
            documento_a_firmar.close()
            documento_a_firmar: ContentFile = (
                FirmaOrden.objects.filter(
                    Q(orden_firmada__solicitud_servicio__id_solicitud=orden) &
                    Q(tiempo_firma__isnull=False)
                ).order_by(
                    "-tiempo_firma"
                ).first().documento_firmado.open()
            )
            # Agregando el contenido después es de la única forma que funciona
            archivo: ContentFile = ContentFile(
                content=b"",
                name=f"{datetime.now(timezone(settings.TIME_ZONE)).isoformat()}.pdf"
            )
            archivo.write(documento_a_firmar.read())
            archivo.write(firmado)
            documento_a_firmar.close()
            firma.documento_firmado = archivo
            firma.tiempo_firma = TransactionNow()
            orden_servicio.ultima_accion_orden = TransactionNow()
            with transaction.atomic():
                firma.save()
                orden_servicio.save()
            messages.success(request, "Se ha firmado la orden correctamente")
            return HttpResponseRedirect(self.success_url)
