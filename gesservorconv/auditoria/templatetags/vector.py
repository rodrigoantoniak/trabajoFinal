from django import template


def enesimo(valor: list, arg: int):
    if (
        isinstance(valor, list)
        and isinstance(arg, int)
        and arg < len(valor)
    ):
        return valor[arg]
    return None


register = template.Library()
register.filter("enesimo", enesimo)
