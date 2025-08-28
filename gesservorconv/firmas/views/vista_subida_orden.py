from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.postgres.functions import TransactionNow
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import transaction
from django.db.models import Max, Q, QuerySet
from django.forms import BaseFormSet, formset_factory
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import View

import cv2
from datetime import datetime
from difflib import SequenceMatcher
from io import BytesIO
import math
from matplotlib import pyplot as plt
import numpy as np
import os
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
from pytz import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from skimage import measure, morphology
from skimage.color import label2rgb
from skimage.measure import regionprops
from skimage.metrics import normalized_root_mse
from typing import Any, Dict, Self

from ..models import OrdenServicio, FirmaOrden
from ..forms import FormularioEscaneo

from cuentas.models import Comitente, ResponsableTecnico, Secretario
from servicios.models import Servicio

from gesservorconv.mixins import (
    MixinAccesoRequerido,
    MixinPermisoRequerido
)


class VistaSubidaOrden(
    MixinAccesoRequerido,
    UserPassesTestMixin,
    View
):
    template_name: str = "firmas/subir_orden.html"

    def test_func(self: Self) -> bool:
        return self.request.user.groups.filter(
            name="ayudante"
        )

    def handle_no_permission(self: Self) -> HttpResponse:
        if self.request.user.is_anonymous:
            messages.warning(
                self.request,
                "La sesión ha caducado"
            )
            direccion: str = (
                reverse_lazy("cuentas:iniciar_sesion") +
                "?siguiente=" + self.request.path
            )
            if self.request.htmx:
                return HttpResponse(
                    self.request.get_full_path(),
                    headers={
                        "HX-Redirect": direccion
                    }
                )
            return HttpResponseRedirect(direccion)
        if self.request.user.is_staff or self.request.user.is_superuser:
            logout(self.request)
            messages.error(
                self.request,
                (
                    "El usuario %(nombre)s no tiene permiso a"
                    " esta página. Por ello, se ha cerrado"
                    " la sesión."
                ) % {
                    "nombre": self.request.user.username
                }
            )
            return HttpResponseRedirect(
                reverse_lazy("cuentas:iniciar_sesion")
            )
        messages.error(
            self.request,
            "Usted no está a cargo de la Secretaría."
        )
        return HttpResponseRedirect(
            reverse_lazy('cuentas:perfil')
        )

    def get_context_data(
        self: Self,
        **kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        contexto: Dict[str, Any] = {}
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
        cantidad_imagenes: int = FirmaOrden.objects.filter(
            orden_firmada__solicitud_servicio__id_solicitud=orden
        ).aggregate(
            Max('pagina_firma', default=1)
        )
        fabrica_formset: type[BaseFormSet] = formset_factory(
            form=FormularioEscaneo,
            extra=cantidad_imagenes['pagina_firma__max'],
            max_num=cantidad_imagenes['pagina_firma__max'],
            validate_max=True,
            min_num=cantidad_imagenes['pagina_firma__max'],
            validate_min=True
        )
        contexto["formset"] = fabrica_formset(
            {
                "form-TOTAL_FORMS": str(
                    cantidad_imagenes['pagina_firma__max']
                ),
                "form-INITIAL_FORMS": "0",
            }
        )
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
        firmas: QuerySet[FirmaOrden] = FirmaOrden.objects.filter(
            orden_firmada__solicitud_servicio__id_solicitud=orden
        )
        cantidad_imagenes: dict[str, int] = firmas.aggregate(
            Max('pagina_firma', default=1)
        )
        fabrica_formset: type[BaseFormSet] = formset_factory(
            form=FormularioEscaneo,
            extra=cantidad_imagenes['pagina_firma__max'],
            max_num=cantidad_imagenes['pagina_firma__max'],
            validate_max=True,
            min_num=cantidad_imagenes['pagina_firma__max'],
            validate_min=True
        )
        formset: BaseFormSet = fabrica_formset(
            request.POST, request.FILES
        )
        if formset.is_valid():
            carpeta: str = (
                f"{settings.MEDIA_ROOT}"
                f"/{OrdenServicio.archivo_orden_firmada.field.upload_to}{orden}"
            )
            os.mkdir(carpeta)
            documento_a_firmar: ContentFile = (
                OrdenServicio.objects.get(
                    Q(solicitud_servicio__id_solicitud=orden)
                ).archivo_orden_original.open()
            )
            paginas: list[Image.Image] = convert_from_bytes(
                documento_a_firmar.read(),
                dpi=600,
                output_folder=carpeta,
                fmt="png"
            )
            documento_a_firmar.close()
            imagenes: list[Image.Image] = []
            firmas_pagina: QuerySet[FirmaOrden]
            imagen: Image.Image
            for indice, form in enumerate(formset):
                # alineación de imagen de escaneado (documentación de OpenCV)
                imagen = Image.open(
                    form.cleaned_data.get("archivo_escaneo")
                )
                im1: cv2.UMat = cv2.cvtColor(
                    np.asarray(paginas[indice]),
                    cv2.COLOR_BGR2RGB
                )
                im1_byn: cv2.UMat = cv2.cvtColor(
                    im1, cv2.COLOR_BGR2GRAY
                )
                im2: cv2.UMat = cv2.cvtColor(
                    np.asarray(imagen),
                    cv2.COLOR_BGR2RGB
                )
                im2_byn: cv2.UMat = cv2.cvtColor(
                    im2, cv2.COLOR_BGR2GRAY
                )
                orb: cv2.ORB = cv2.ORB_create(3500)
                kp1, d1 = orb.detectAndCompute(im1_byn, None)
                kp2, d2 = orb.detectAndCompute(im2_byn, None)
                matcher: cv2.DescriptorMatcher = cv2.DescriptorMatcher_create(
                    cv2.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING
                )
                matches: tuple[cv2.DMatch] = matcher.match(d1, d2, None)
                matches: tuple[cv2.DMatch] = sorted(
                    matches,
                    key=lambda x: x.distance,
                    reverse=False
                )
                nBuenasCoincidencias: int = int(len(matches) * 0.1)
                matches: tuple[cv2.DMatch] = matches[:nBuenasCoincidencias]
                puntos1: np.ndarray[np.float32] = np.zeros(
                    (len(matches), 2),
                    dtype=np.float32
                )
                puntos2: np.ndarray[np.float32] = np.zeros(
                    (len(matches), 2),
                    dtype=np.float32
                )
                for i, match in enumerate(matches):
                    puntos1[i, :] = kp1[match.queryIdx].pt
                    puntos2[i, :] = kp2[match.trainIdx].pt
                h, mascara = cv2.findHomography(
                    puntos2, puntos1, cv2.RANSAC
                )
                altura, base, canales = im1.shape
                im2_reg: cv2.UMat = cv2.warpPerspective(
                    im2, h, (base, altura)
                )
                # imwrite es sólo para efectos demostrativos
                cv2.imwrite(
                    os.path.join(
                        carpeta,
                        f"pagina{indice+1}.png"
                    ),
                    im2_reg
                )
                texto1: str = pytesseract.image_to_string(
                    cv2.threshold(
                        cv2.medianBlur(
                            cv2.filter2D(
                                cv2.cvtColor(
                                    np.asarray(paginas[indice]),
                                    cv2.COLOR_BGR2GRAY
                                ),
                                -1,
                                np.array(
                                    [[0, -1, 0], [-1, 5, -1], [0, -1, 0]]
                                )
                            ),
                            7
                        ),
                        127,
                        255,
                        cv2.THRESH_BINARY
                    )[1],
                    lang="spa",
                    config="--psm 12 --oem 1"
                )
                with open(
                    os.path.join(
                        carpeta,
                        f"pagina{indice+1}-texto1.txt"
                    ),
                    "w"
                ) as f:
                    f.write(texto1)
                texto2: str = pytesseract.image_to_string(
                    cv2.threshold(
                        cv2.medianBlur(
                            cv2.filter2D(
                                cv2.cvtColor(
                                    im2_reg,
                                    cv2.COLOR_BGR2GRAY
                                ),
                                -1,
                                np.array(
                                    [[0, -1, 0], [-1, 5, -1], [0, -1, 0]]
                                )
                            ),
                            7
                        ),
                        127,
                        255,
                        cv2.THRESH_BINARY
                    )[1],
                    lang="spa",
                    config="--psm 12 --oem 1"
                )
                with open(
                    os.path.join(
                        carpeta,
                        f"pagina{indice+1}-texto2.txt"
                    ),
                    "w"
                ) as f:
                    f.write(texto2)
                # 0.001 es constante de textos iguales
                if (
                    math.sqrt(
                        SequenceMatcher(None, texto1, texto2).ratio()
                    ) / len(texto1.split())
                ) < 0.001:
                    contexto: Dict[str, Any] = self.get_context_data()
                    contexto["formset"] = fabrica_formset()
                    messages.error(
                        request,
                        f"La página {indice+1} no es el impreso correcto"
                    )
                    return render(
                        request,
                        self.template_name,
                        contexto
                    )
                firmas_pagina = firmas.filter(
                    pagina_firma=indice+1
                )
                for numero, firma in enumerate(firmas_pagina):
                    contornos = cv2.findContours(
                        cv2.adaptiveThreshold(
                            cv2.medianBlur(
                                cv2.filter2D(
                                    cv2.cvtColor(
                                        im2_reg[
                                            int(
                                                (
                                                    A4[1]
                                                    - 2.5*mm
                                                    - firma.coord_y_firma
                                                )*len(im2_reg)/A4[1]
                                            ):
                                            int(
                                                (
                                                    A4[1]
                                                    + 40*mm
                                                    - firma.coord_y_firma
                                                )*len(im2_reg)/A4[1]
                                            ),
                                            int(
                                                (
                                                    firma.coord_x_firma
                                                    - 2.5*mm
                                                )*len(im2_reg[0])/A4[0]
                                            ):
                                            int(
                                                (
                                                    52.5*mm
                                                    + firma.coord_x_firma
                                                )*len(im2_reg[0])/A4[0]
                                            )
                                        ],
                                        cv2.COLOR_BGR2GRAY
                                    ),
                                    -1,
                                    np.array(
                                        [[0, -1, 0], [-1, 5, -1], [0, -1, 0]]
                                    )
                                ),
                                7
                            ),
                            255,
                            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                            cv2.THRESH_BINARY,
                            11,
                            2
                        ),
                        cv2.RETR_EXTERNAL,
                        cv2.CHAIN_APPROX_SIMPLE
                    )[0]
                    for cnt in contornos:
                        approx = cv2.approxPolyDP(
                            cnt,
                            0.02 * cv2.arcLength(cnt, True),
                            True
                        )
                        if len(approx) == 4:
                            x, y, w, h = cv2.boundingRect(approx)
                            if (
                                35*mm*len(im2_reg)/A4[1]
                                < h
                                < 40*mm*len(im2_reg)/A4[1] and
                                47.5*mm*len(im2_reg)/A4[1]
                                < w
                                < 52.5*mm*len(im2_reg)/A4[1]
                            ):
                                cv2.drawContours(
                                    im2_reg[
                                        int(
                                            (
                                                A4[1]
                                                - 2.5*mm
                                                - firma.coord_y_firma
                                            )*len(im2_reg)/A4[1]
                                        ):
                                        int(
                                            (
                                                A4[1]
                                                + 40*mm
                                                - firma.coord_y_firma
                                            )*len(im2_reg)/A4[1]
                                        ),
                                        int(
                                            (
                                                firma.coord_x_firma
                                                - 2.5*mm
                                            )*len(im2_reg[0])/A4[0]
                                        ):
                                        int(
                                            (
                                                52.5*mm
                                                + firma.coord_x_firma
                                            )*len(im2_reg[0])/A4[0]
                                        )
                                    ],
                                    [approx],
                                    -1,
                                    (0, 255, 0),
                                    50
                                )
                                plt.imsave(
                                    os.path.join(
                                        carpeta,
                                        f"pagina{indice+1}-bloqueFirma{numero+1}.png"
                                    ),
                                    im2_reg[
                                        int(
                                            (
                                                A4[1]
                                                - 2.5*mm
                                                - firma.coord_y_firma
                                            )*len(im2_reg)/A4[1]
                                        ):
                                        int(
                                            (
                                                A4[1]
                                                + 40*mm
                                                - firma.coord_y_firma
                                            )*len(im2_reg)/A4[1]
                                        ),
                                        int(
                                            (
                                                firma.coord_x_firma
                                                - 2.5*mm
                                            )*len(im2_reg[0])/A4[0]
                                        ):
                                        int(
                                            (
                                                52.5*mm
                                                + firma.coord_x_firma
                                            )*len(im2_reg[0])/A4[0]
                                        )
                                    ]
                                )
                                break
                    else:
                        contexto: Dict[str, Any] = self.get_context_data()
                        contexto["formset"] = fabrica_formset()
                        # TODO: poner de quién es la firma
                        messages.error(
                            request,
                            f"En la página {indice+1}, no se halla"
                            " el bloque de firma de"
                            f" {firma.usuario_firmante.last_name},"
                            f" {firma.usuario_firmante.first_name}"
                        )
                        return render(
                            request,
                            self.template_name,
                            contexto
                        )
                    # Parámetros constantes para firma
                    constant_parameter_1 = 125
                    constant_parameter_2 = 100
                    constant_parameter_3 = 150
                    constant_parameter_4 = 85
                    img = cv2.adaptiveThreshold(
                        cv2.medianBlur(
                            cv2.filter2D(
                                cv2.cvtColor(
                                    im2_reg[
                                        int(
                                            (
                                                A4[1]
                                                + 2.5*mm
                                                - firma.coord_y_firma
                                            )*len(im2_reg)/A4[1]
                                        ):
                                        int(
                                            (
                                                A4[1]
                                                + 32.5*mm
                                                - firma.coord_y_firma
                                            )*len(im2_reg)/A4[1]
                                        ),
                                        int(
                                            (
                                                firma.coord_x_firma
                                                + 2.5*mm
                                            )*len(im2_reg[0])/A4[0]
                                        ):
                                        int(
                                            (
                                                47.5*mm
                                                + firma.coord_x_firma
                                            )*len(im2_reg[0])/A4[0]
                                        )
                                    ],
                                    cv2.COLOR_BGR2GRAY
                                ),
                                -1,
                                np.array(
                                    [[0, -1, 0], [-1, 5, -1], [0, -1, 0]]
                                )
                            ),
                            7
                        ),
                        255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY,
                        17,
                        2
                    )
                    blobs = img > img.mean()
                    blobs_labels = measure.label(blobs, background=1)
                    image_label_overlay = label2rgb(blobs_labels, image=img)
                    the_biggest_component = 0
                    total_area = 0
                    counter = 0
                    average = 0.0
                    for region in regionprops(blobs_labels):
                        if (region.area > 10):
                            total_area = total_area + region.area
                            counter = counter + 1
                        if (region.area >= 250):
                            if (region.area > the_biggest_component):
                                the_biggest_component = region.area

                    average = (total_area/counter)
                    a4_small_size_outliar_constant = (
                        (average/constant_parameter_1)*constant_parameter_2
                    )+constant_parameter_3
                    a4_big_size_outliar_constant = (
                        a4_small_size_outliar_constant*constant_parameter_4
                    )
                    pre_version = morphology.remove_small_objects(
                        blobs_labels,
                        a4_small_size_outliar_constant
                    )
                    component_sizes = np.bincount(pre_version.ravel())
                    too_small = component_sizes > (a4_big_size_outliar_constant)
                    too_small_mask = too_small[pre_version]
                    pre_version[too_small_mask] = 0
                    plt.imsave(
                        os.path.join(
                            carpeta,
                            f"pre_version-pagina{indice+1}-firma{numero+1}.png"
                        ),
                        pre_version
                    )
                    img = cv2.imread(
                        os.path.join(
                            carpeta,
                            f"pre_version-pagina{indice+1}-firma{numero+1}.png"
                        ),
                        0
                    )
                    img = cv2.threshold(
                        img,
                        0,
                        255,
                        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
                    )[1]
                    cv2.imwrite(
                        os.path.join(
                            carpeta,
                            f"version-pagina{indice+1}-firma{numero+1}.png"
                        ),
                        img
                    )
                    # 0.09 es constante de si hay una firma
                    if (
                        normalized_root_mse(
                            cv2.resize(
                                cv2.threshold(
                                    cv2.medianBlur(
                                        img,
                                        7
                                    ),
                                    175,
                                    255,
                                    cv2.THRESH_BINARY
                                )[1],
                                (1200, 900)
                            ),
                            cv2.resize(
                                cv2.cvtColor(
                                    im1[
                                        int(
                                            (
                                                A4[1]
                                                + 1.5*mm
                                                - firma.coord_y_firma
                                            )*len(im2_reg)/A4[1]
                                        ):
                                        int(
                                            (
                                                A4[1]
                                                + 31.5*mm
                                                - firma.coord_y_firma
                                            )*len(im2_reg)/A4[1]
                                        ),
                                        int(
                                            (
                                                firma.coord_x_firma
                                                + 2.5*mm
                                            )*len(im2_reg[0])/A4[0]
                                        ):
                                        int(
                                            (
                                                47.5*mm
                                                + firma.coord_x_firma
                                            )*len(im2_reg[0])/A4[0]
                                        )
                                    ],
                                    cv2.COLOR_RGB2GRAY
                                ),
                                (1200, 900)
                            )
                        )
                    ) < 0.09:
                        contexto: Dict[str, Any] = self.get_context_data()
                        contexto["formset"] = fabrica_formset()
                        messages.error(
                            request,
                            f"En la página {i+1}, falta la firma de"
                            f" {firma.usuario_firmante.last_name},"
                            f" {firma.usuario_firmante.first_name}"
                        )
                        return render(
                            request,
                            self.template_name,
                            contexto
                        )
                imagenes.append(imagen)
            imagen = imagenes[0]
            buffer: BytesIO = BytesIO()
            if len(imagenes) > 1:
                imagen.save(
                    buffer,
                    format="pdf",
                    resolution=100.0,
                    save_all=True,
                    append_images=imagenes[1:]
                )
            else:
                imagen.save(
                    buffer,
                    format="pdf",
                    resolution=100.0
                )
            buffer.seek(0)
            archivo: ContentFile = ContentFile(
                content=buffer.getvalue(),
                name=f"{datetime.now(timezone(settings.TIME_ZONE)).isoformat()}.pdf"
            )
            orden_servicio: OrdenServicio = OrdenServicio.objects.get(
                solicitud_servicio__id_solicitud=orden
            )
            orden_servicio.archivo_orden_firmada = archivo
            orden_servicio.ultima_accion_orden = TransactionNow()
            servicio: Servicio = Servicio(
                orden_servicio=orden_servicio,
                convenio=None,
                pagado=False,
                completado=False
            )
            with transaction.atomic():
                orden_servicio.save()
                servicio.save()
            messages.success(
                request,
                "Se ha subido la orden de servicios correctamente"
            )
            return HttpResponseRedirect(
                reverse_lazy("firmas:lista_ordenes_ayudante")
            )
        contexto: Dict[str, Any] = self.get_context_data()
        contexto["formset"] = fabrica_formset()
        messages.error(
            request,
            "Carga inválida de imágenes. Inténtelo de nuevo"
        )
        return render(
            request,
            self.template_name,
            contexto
        )
