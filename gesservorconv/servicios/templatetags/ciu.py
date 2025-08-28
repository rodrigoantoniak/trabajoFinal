from django import template
from cuentas.models.validaciones import (
    es_valido_cuil,
    es_valido_cuit
)

from typing import Optional


def cuil(valor: int) -> Optional[str]:
    if (
        isinstance(valor, int)
        and es_valido_cuil(valor)
    ):
        return f'{str(valor)[0:2]}-{str(valor)[2:10]}-{str(valor)[10]}'
    return None


def cuit(valor: int) -> Optional[str]:
    if (
        isinstance(valor, int)
        and es_valido_cuit(valor)
    ):
        return f'{str(valor)[0:2]}-{str(valor)[2:10]}-{str(valor)[10]}'
    return None


def enesimo(valor: list, arg: int):
    if (
        isinstance(valor, list)
        and isinstance(arg, int)
        and arg < len(valor)
    ):
        return valor[arg]
    return None


register = template.Library()
register.filter("cuil", cuil)
register.filter("cuit", cuit)
register.filter("enesimo", enesimo)
