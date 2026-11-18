"""Contratos del laboratorio WhatsApp (comparación Selenium / agent-browser).

El laboratorio envía el primer WhatsApp a leads de Argentina que pidieron ese
canal, documentando el intento en ``Otra información`` con la línea
``N INT Se envía WhatsApp DD/MM/AAAA HH:MM`` antes de pulsar el botón
``Send To Whatsapp`` de la ficha — la misma convención del Monitor de Bandeja,
pero conservando el historial y numerando desde ``max(INT)+1``.

Los textos de intento previstos y las huellas del historial viven en
``laboratory_store``: un proceso interrumpido reanuda con la MISMA línea, sin
recalcular N ni generar una segunda variante horaria.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from comment_reader import SALESFORCE_ID_PATTERN

LAB_OPERATION = "laboratorio_whatsapp"
LAB_SCHEMA_VERSION = 1
LAB_ENGINES = ("selenium", "agent_browser")
LAB_MODES = ("prueba", "real", "auditoria")
LAB_MODE_DEFAULT = "prueba"
LAB_BATCH_SIZE_DEFAULT = 10

# Zona explícita del intento documentado: la convención de los auxiliares es la
# hora de Argentina y no debe depender de la zona configurada en Windows.
ARGENTINA_TZ = timezone(timedelta(hours=-3))

# Estados de verificación (modo prueba, sin escritura).
STATUS_APTO = "apto"
STATUS_BLOQUEADO = "bloqueado"
STATUS_REVISION = "revision"
# Estados de ejecución real.
STATUS_ENVIADO = "documentado_enviado"
STATUS_WA_NO_CONFIRMADO = "documentado_wa_no_confirmado"
STATUS_WA_ERROR = "documentado_wa_error"
STATUS_DOC_ERROR = "error_documentacion"
STATUS_NO_ELEGIBLE = "no_elegible"
STATUS_OMITIDO = "omitido_duplicado"
STATUS_ERROR = "error"
# Estados de auditoría (solo lectura: verifica la línea reservada en la ficha).
STATUS_AUDIT_OK = "auditada"
STATUS_AUDIT_DISCREPANCIA = "audit_discrepancia"
STATUS_AUDIT_SIN_RESERVA = "audit_sin_reserva"

# Motivos de bloqueo (determinísticos, comparables entre motores).
BLOCK_PAIS_NO_AR = "pais_no_argentina"
BLOCK_PREFERENCIA = "sin_preferencia_whatsapp"
BLOCK_SIN_BOTON = "sin_boton_whatsapp"
BLOCK_CAMPO_ILEGIBLE = "campo_ilegible"
BLOCK_ID_INVALIDO = "id_invalido"
BLOCK_SESION = "sesion_vencida"
BLOCK_YA_ENVIADO = "ya_enviado_o_ambiguo"


def normalize_whitespace(value: object) -> str:
    return " ".join(str(value or "").split())


def normalize_key(value: object) -> str:
    """Normalización de comparación de textos de Salesforce."""
    text = str(value or "").casefold()
    text = text.translate(str.maketrans("áéíóúüñ", "aeiouun"))
    return normalize_whitespace(text)


def canonical_lead_id(value: object) -> str:
    lead_id = str(value or "").strip()
    if not SALESFORCE_ID_PATTERN.fullmatch(lead_id):
        raise ValueError(f"Lead ID inválido: {lead_id!r}")
    return lead_id


def is_argentina(value: object) -> bool:
    return "argentin" in normalize_key(value)


def wants_whatsapp(preference: object) -> bool:
    return "whatsapp" in normalize_key(preference)


def argentina_now(now: datetime | None = None) -> datetime:
    """Hora civil de Argentina (UTC-3) para la línea de intento."""
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(ARGENTINA_TZ)


def whatsapp_attempt_line(number: int, moment: datetime | None = None) -> str:
    """``N INT Se envía WhatsApp DD/MM/AAAA HH:MM`` en hora de Argentina."""
    if number < 1:
        raise ValueError("El número de intento debe ser mayor o igual a 1.")
    local = argentina_now(moment)
    return f"{number} INT Se envía WhatsApp {local:%d/%m/%Y %H:%M}"


_INT_PREFIX = re.compile(r"^\s*\d+\s+INT\b", re.IGNORECASE)


def has_attempt_lines(comment: object) -> bool:
    return bool(_INT_PREFIX.search(str(comment or "")))


def validate_laboratory_queue(payload: object) -> dict:
    """Valida la cola del laboratorio y devuelve el contrato normalizado.

    Estructura: ``operation`` fijo, ``schema_version``, ``mode`` prueba|real,
    ``engine`` selenium|agent_browser|comparacion y ``leads`` con
    ``{lead_id, nombre?, pais?, preferencia?}``. ``comparacion`` solo se
    acepta en modo prueba (ambos motores verifican sin escribir).
    """
    if not isinstance(payload, dict) or payload.get("operation") != LAB_OPERATION:
        raise ValueError(f"La cola del laboratorio no declara operation='{LAB_OPERATION}'.")
    mode = str(payload.get("mode") or LAB_MODE_DEFAULT).strip()
    if mode not in LAB_MODES:
        raise ValueError(f"mode inválido: {mode!r} (válidos: {', '.join(LAB_MODES)}).")
    engine = str(payload.get("engine") or "selenium").strip()
    valid_engines = (*LAB_ENGINES, "comparacion")
    if engine not in valid_engines:
        raise ValueError(f"engine inválido: {engine!r} (válidos: {', '.join(valid_engines)}).")
    if engine == "comparacion" and mode == "real":
        raise ValueError("engine='comparacion' no admite mode='real': en real cada lead usa un solo motor.")
    leads = payload.get("leads")
    if not isinstance(leads, list) or not leads:
        raise ValueError("La cola del laboratorio no contiene Leads.")
    seen: set[str] = set()
    validated = []
    for index, lead in enumerate(leads):
        if not isinstance(lead, dict):
            raise ValueError(f"Lead {index} de la cola del laboratorio no es un objeto válido.")
        lead_id = canonical_lead_id(lead.get("lead_id"))
        if lead_id in seen:
            raise ValueError(f"Lead {index} duplicado en la cola del laboratorio.")
        seen.add(lead_id)
        entry = {"lead_id": lead_id}
        for key in ("nombre", "pais", "preferencia"):
            value = normalize_whitespace(lead.get(key))
            if value:
                entry[key] = value
        if engine == "comparacion":
            # Orden A/B alternado por lead: ningún motor obtiene ventaja
            # sistemática (warmup/caché) en la comparación pareada.
            entry["engines"] = list(LAB_ENGINES) if index % 2 == 0 else list(reversed(LAB_ENGINES))
        else:
            entry["engines"] = [engine]
        validated.append(entry)
    campaign_id = normalize_whitespace(payload.get("campaign_id"))
    batch_size = payload.get("batch_size", LAB_BATCH_SIZE_DEFAULT)
    if not isinstance(batch_size, int) or not 1 <= batch_size <= 500:
        raise ValueError("batch_size debe ser un entero entre 1 y 500.")
    return {
        "leads": validated,
        "mode": mode,
        "engine": engine,
        "campaign_id": campaign_id or "laboratorio_default",
        "dataset_id": normalize_whitespace(payload.get("dataset_id")),
        "batch_size": batch_size,
        "run_id": normalize_whitespace(payload.get("run_id")),
        "source_file": normalize_whitespace(payload.get("source_file")),
        "schema_version": int(payload.get("schema_version") or LAB_SCHEMA_VERSION),
    }


def build_queue(
    leads: list[dict],
    *,
    mode: str,
    engine: str,
    campaign_id: str,
    dataset_id: str = "",
    batch_size: int = LAB_BATCH_SIZE_DEFAULT,
    source_file: str = "",
) -> dict:
    """Arma el payload de cola (lo usa la UI y los tests)."""
    return validate_laboratory_queue(
        {
            "operation": LAB_OPERATION,
            "schema_version": LAB_SCHEMA_VERSION,
            "mode": mode,
            "engine": engine,
            "campaign_id": campaign_id,
            "dataset_id": dataset_id,
            "batch_size": batch_size,
            "source_file": source_file,
            "leads": leads,
        }
    )
