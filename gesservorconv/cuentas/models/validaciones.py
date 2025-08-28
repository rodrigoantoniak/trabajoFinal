def es_valido_cuil(cuil: int) -> bool:
    if cuil // 1000000000 not in [20, 23, 24, 27]:
        return False
    aux: int = cuil // 10
    factor: int = 2
    suma: int = 0
    while aux > 0:
        suma = suma + ((aux % 10) * factor)
        factor = 2 if factor == 7 else factor + 1
        aux = aux // 10
    if suma % 11 == 0:
        return cuil % 10 == 0 and cuil // 1000000000 != 23
    if suma % 11 == 1:
        return False
    return cuil % 10 == 11 - (suma % 11) and (
        cuil // 1000000000 != 23 or cuil % 10 in [3, 4, 9]
    )


def es_valido_cuit(cuit: int) -> bool:
    if cuit // 1000000000 not in [30, 33, 34]:
        return False
    aux: int = cuit // 10
    factor: int = 2
    suma: int = 0
    while aux > 0:
        suma = suma + ((aux % 10) * factor)
        factor = 2 if factor == 7 else factor + 1
        aux = aux // 10
    if suma % 11 == 0:
        return cuit % 10 == 0 and cuit // 1000000000 != 33
    if suma % 11 == 1:
        return False
    return cuit % 10 == 11 - (suma % 11) and (
        cuit // 1000000000 != 33 or cuit % 10 in [3, 9]
    )
