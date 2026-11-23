"""Recogida de apertura: QUALIF ingresados fuera de toda franja de la bandeja.

Módulo puro (sin Selenium ni Salesforce): clasifica cada lead según la hora
de ``fecha_creacion`` contra las franjas — día-agnósticas, igual que
``within_schedule`` — y valida el rango manual ``[desde, hasta)`` que pide el
operador. El reporte muestra la fecha en la zona horaria del visor (= la PC
del bot): no hay conversión. El ``tz_offset`` de la bandeja no se usa acá —
existe solo para documentar intentos WhatsApp en la hora del país del lead.
"""

from __future__ import annotations

from datetime import datetime

from monitor_store import within_schedule

CLASIF_TURNO_PERSONAL = "turno_personal"
CLASIF_NO_HABIL = "no_habil_elegible"
CLASIF_FUERA_DE_RANGO = "fuera_de_rango"
CLASIF_REVISION = "revision"

CREACION_FORMAT = "%d/%m/%Y %I:%M %p"
RANGE_FORMAT = "%Y-%m-%dT%H:%M"


def creation_moment_local(details: dict | None) -> datetime | None:
    """``fecha_creacion`` del reporte, tal como la muestra el visor.

    Salesforce renderiza las fechas en la zona horaria del usuario que las
    mira — el usuario del bot comparte la hora de la PC, así que no hay
    conversión que hacer. None si falta o no parsea — sin fecha no hay
    clasificación confiable.
    """
    raw = str((details or {}).get("fecha_creacion") or "").strip()
    try:
        return datetime.strptime(raw, CREACION_FORMAT)
    except ValueError:
        return None


def _franja_cubre(slots: list[dict] | None, moment: datetime, bandeja_code: str) -> bool:
    """¿Alguna franja (propia o de un miembro del equipo) cubre esa hora en
    la bandeja? Una franja sin ``bandejas`` tildadas cubre todas; la lista
    vacía no cubre nada — ``within_schedule`` la trata como "siempre" para
    el gate, acá significa nadie a cargo."""
    return bool(slots) and within_schedule(slots, moment=moment, bandeja=bandeja_code)


def classify_lead(
    details: dict | None,
    bandeja: dict,
    schedule: list[dict] | None,
    equipo: list[dict] | None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> str:
    """Clasifica un lead para la recogida de apertura.

    - ``revision``: sin ``fecha_creacion`` parseable — se lista, no se toma.
    - ``fuera_de_rango``: fuera del ``[desde, hasta)`` pedido.
    - ``turno_personal``: una franja propia o de equipo cubre su hora de
      ingreso en esa bandeja — le pertenece a esa franja.
    - ``no_habil_elegible``: nadie cubría su hora de ingreso.
    """
    moment = creation_moment_local(details)
    if moment is None:
        return CLASIF_REVISION
    if desde is not None and moment < desde:
        return CLASIF_FUERA_DE_RANGO
    if hasta is not None and moment >= hasta:
        return CLASIF_FUERA_DE_RANGO
    code = bandeja.get("code")
    if _franja_cubre(schedule, moment, code):
        return CLASIF_TURNO_PERSONAL
    for member in equipo or []:
        if _franja_cubre(member.get("franjas"), moment, code):
            return CLASIF_TURNO_PERSONAL
    return CLASIF_NO_HABIL


def parse_apertura_range(
    desde_raw: object,
    hasta_raw: object,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Valida el rango manual: formato ``datetime-local``, ``desde < hasta``
    y ``hasta`` no futuro. Devuelve el par ya parseado."""
    try:
        desde = datetime.strptime(str(desde_raw or "").strip(), RANGE_FORMAT)
        hasta = datetime.strptime(str(hasta_raw or "").strip(), RANGE_FORMAT)
    except ValueError:
        raise ValueError("El período debe tener formato fecha y hora (AAAA-MM-DDTHH:MM).") from None
    if desde >= hasta:
        raise ValueError("El Desde debe ser anterior al Hasta.")
    if hasta > (now or datetime.now()):
        raise ValueError("El Hasta no puede ser futuro.")
    return desde, hasta
