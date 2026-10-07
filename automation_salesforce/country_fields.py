"""Contrato país/modo → campos físicos de Salesforce.

Las tandas predictivas de Wolkvox son homogéneas por país y la UI ofrece dos
modos de campos. Cada cola congela el modo al momento de exportarse; los
runners lo validan antes de tocar Salesforce:

- ``argentina``: los intentos se documentan en ``Otra información`` y el
  motivo de cierre reemplaza ``Comentario``.
- ``colombia_mexico``: los intentos se documentan en ``Comentario`` y el
  motivo de cierre se agrega al final de ``Otra información`` conservando el
  texto previo.

Las colas históricas sin ``country`` se interpretan como ``argentina``, que
es el comportamiento previo a este cambio.
"""

from __future__ import annotations

from comment_reader import COMMENT_LABELS, OTHER_INFORMATION_LABELS

ARGENTINA = "argentina"
COLOMBIA_MEXICO = "colombia_mexico"
COUNTRY_MODES = (ARGENTINA, COLOMBIA_MEXICO)
DEFAULT_COUNTRY = ARGENTINA

# Rol funcional → clave del campo físico de Salesforce.
_FIELD_KEY = {
    ARGENTINA: {"attempts": "otra_informacion", "closure": "comentario"},
    COLOMBIA_MEXICO: {"attempts": "comentario", "closure": "otra_informacion"},
}
_LABELS = {
    "comentario": COMMENT_LABELS,
    "otra_informacion": OTHER_INFORMATION_LABELS,
}
_DISPLAY = {
    "comentario": "Comentario",
    "otra_informacion": "Otra información",
}


def normalize_country(value: object) -> str:
    """Valida el modo de la cola; el vacío hereda el modo histórico."""
    mode = str(value or "").strip().lower() or DEFAULT_COUNTRY
    if mode not in COUNTRY_MODES:
        raise ValueError(f"Modo de país desconocido: {mode!r}.")
    return mode


def field_key(country: object, role: str) -> str:
    """Clave estable del campo físico para snapshots y correcciones."""
    return _FIELD_KEY[normalize_country(country)][role]


def field_labels(country: object, role: str) -> tuple[str, ...]:
    """Etiquetas visibles del campo físico para el rol pedido."""
    return _LABELS[field_key(country, role)]


def field_display(country: object, role: str) -> str:
    """Nombre legible del campo físico para mensajes de la consola."""
    return _DISPLAY[field_key(country, role)]


# Cola fría que la conversión asigna como propietario final, por país.
# Argentina usa AR_LEAD_COLD; México MX_LEAD_COLD y Colombia CO_LEAD_COLD —
# el modo comparte los dos porque la tanda siempre es de un solo país.
_FINAL_OWNERS = {
    ARGENTINA: ("AR_LEAD_COLD",),
    COLOMBIA_MEXICO: ("MX_LEAD_COLD", "CO_LEAD_COLD"),
}


def final_owners(country: object) -> tuple[str, ...]:
    """Propietarios finales aceptados tras ``Convert Lead → Yes``."""
    return _FINAL_OWNERS[normalize_country(country)]
