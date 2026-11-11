from django.core.exceptions import ValidationError


def calcular_dv_rut(cuerpo: str) -> str:
    """Calcula el dígito verificador de un RUT chileno usando el algoritmo Módulo 11."""
    suma = 0
    multiplicador = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1

    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def validar_y_formatear_rut(rut_raw: str) -> str:
    """
    Limpia, valida con Módulo 11 y formatea un RUT chileno al estándar XX.XXX.XXX-Y.
    Lanza ValidationError si el formato o el dígito verificador no son válidos.
    """
    if not rut_raw:
        raise ValidationError("Debe ingresar un RUT.")

    limpio = (
        str(rut_raw)
        .strip()
        .upper()
        .replace(".", "")
        .replace("-", "")
        .replace(" ", "")
    )

    if len(limpio) < 8 or len(limpio) > 9:
        raise ValidationError("El RUT debe contener entre 7 y 8 dígitos más su dígito verificador.")

    cuerpo, dv_ingresado = limpio[:-1], limpio[-1]
    if not cuerpo.isdigit() or not (dv_ingresado.isdigit() or dv_ingresado == "K"):
        raise ValidationError("El formato del RUT ingresado no es válido.")

    # Evitar RUTs ficticios de dígitos repetidos como 11.111.111-1
    if len(set(cuerpo)) == 1:
        raise ValidationError("El RUT ingresado no corresponde a un número válido.")

    dv_esperado = calcular_dv_rut(cuerpo)
    if dv_ingresado != dv_esperado:
        raise ValidationError(
            f"RUT inválido: para el número {int(cuerpo):,}".replace(",", ".")
            + f" el dígito verificador correcto es -{dv_esperado}."
        )

    cuerpo_formateado = f"{int(cuerpo):,}".replace(",", ".")
    return f"{cuerpo_formateado}-{dv_esperado}"
