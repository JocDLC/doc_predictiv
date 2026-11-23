"""Parseo del archivo de distribución de leads (exports .xlsx/.csv de Salesforce).

El archivo llega desde la UI al servidor local, se parsea en memoria y nunca
se persiste: ``parse_archivo`` devuelve ``{"sheets": [...]}`` con encabezados
y filas como dicts por columna (la UI mapea Lead ID y persona destino). Los
datos de clientes no salen de la máquina ni se escriben en logs.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from pathlib import Path

from comment_reader import SALESFORCE_ID_PATTERN

MAX_ROWS_PER_SHEET = 1000
SNIFF_BYTES = 4096
CSV_DELIMITERS = (";", ",", "\t")
DISTRIBUCION_OPERATION = "distribuir_leads"
DISTRIBUCION_MODOS = ("real", "prueba")
DISTRIBUCION_MODO_DEFAULT = "real"


def _cell_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value).strip()


def _dedupe_headers(raw_headers: list[object]) -> list[str]:
    """Encabezados únicos y no vacíos: columna sin nombre queda ``col_N``."""
    headers: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_headers):
        name = _cell_text(raw) or f"col_{index + 1}"
        candidate = name
        suffix = 2
        while candidate in seen:
            candidate = f"{name} ({suffix})"
            suffix += 1
        seen.add(candidate)
        headers.append(candidate)
    return headers


def _sheet_from_rows(raw_rows: list[list[object]], name: str) -> dict | None:
    """Primera fila = encabezados; el resto, dicts. Filas vacías se omiten."""
    if not raw_rows:
        return None
    headers = _dedupe_headers(raw_rows[0])
    rows = []
    for raw in raw_rows[1 : MAX_ROWS_PER_SHEET + 1]:
        row = {headers[index]: _cell_text(raw[index]) if index < len(raw) else "" for index in range(len(headers))}
        if any(row.values()):
            rows.append(row)
    if not rows:
        return None
    return {"name": name, "headers": headers, "rows": rows, "truncated": len(raw_rows) - 1 > MAX_ROWS_PER_SHEET}


def _parse_xlsx(content: bytes) -> dict:
    try:
        import openpyxl

        workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as error:
        raise ValueError(f"El archivo .xlsx no se pudo leer: {error}") from error
    sheets = []
    for worksheet in workbook.worksheets:
        raw_rows = [list(row) for row in worksheet.iter_rows(values_only=True)]
        sheet = _sheet_from_rows(raw_rows, worksheet.title)
        if sheet is not None:
            sheets.append(sheet)
    if not sheets:
        raise ValueError("El archivo .xlsx no tiene hojas con datos.")
    return {"sheets": sheets}


def _detect_delimiter(text: str) -> str:
    first_line = text.splitlines()[0] if text.splitlines() else ""
    return max(CSV_DELIMITERS, key=first_line.count)


def _parse_csv(content: bytes, filename: str) -> dict:
    text = None
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("El .csv no se pudo decodificar (utf-8/cp1252).")
    delimiter = _detect_delimiter(text)
    raw_rows = [list(row) for row in csv.reader(io.StringIO(text), delimiter=delimiter)]
    sheet = _sheet_from_rows(raw_rows, Path(filename).stem or "csv")
    if sheet is None:
        raise ValueError("El .csv no tiene encabezados ni filas con datos.")
    return {"sheets": [sheet]}


def parse_archivo(filename: str, content: bytes) -> dict:
    """Devuelve ``{"sheets": [{name, headers, rows, truncated}]}`` o ValueError."""
    suffix = Path(filename or "").suffix.lower()
    if not content:
        raise ValueError("El archivo está vacío.")
    if suffix == ".xlsx":
        return _parse_xlsx(content)
    if suffix in (".csv", ".txt"):
        return _parse_csv(content, filename)
    raise ValueError(f"Extensión no soportada: {suffix or filename}. Usá .xlsx o .csv")


def validate_distribucion_queue(payload: object) -> list[dict[str, str]]:
    """Valida la cola de distribución y devuelve ``[{lead_id, persona, nombre?}]``.

    La UI envía los pares lead/persona ya revisados en la vista previa; el
    ``nombre`` del lead es opcional y solo se conserva para mostrar la
    columna Lead en la tabla de resultados — nunca sale de la máquina.
    """
    if not isinstance(payload, dict) or payload.get("operation") != DISTRIBUCION_OPERATION:
        raise ValueError(f"La cola de distribución no declara operation='{DISTRIBUCION_OPERATION}'.")
    modo = payload.get("modo", DISTRIBUCION_MODO_DEFAULT)
    if modo not in DISTRIBUCION_MODOS:
        raise ValueError(f"modo de cola inválido: {modo!r} (válidos: {', '.join(DISTRIBUCION_MODOS)}).")
    leads = payload.get("leads")
    if not isinstance(leads, list) or not leads:
        raise ValueError("La cola de distribución no contiene Leads.")
    seen: set[str] = set()
    validated = []
    for index, lead in enumerate(leads):
        if not isinstance(lead, dict):
            raise ValueError(f"Lead {index} de la cola de distribución no es un objeto válido.")  # noqa: TRY004
        lead_id = str(lead.get("lead_id") or "").strip()
        if not SALESFORCE_ID_PATTERN.fullmatch(lead_id):
            raise ValueError(f"Lead {index} tiene un Lead ID inválido.")
        persona = str(lead.get("persona") or "").strip()
        if not persona:
            raise ValueError(f"Lead {index} no tiene persona destino.")
        if lead_id in seen:
            raise ValueError(f"Lead {index} duplicado en la cola de distribución.")
        seen.add(lead_id)
        entry = {"lead_id": lead_id, "persona": persona}
        nombre = str(lead.get("nombre") or "").strip()
        if nombre:
            entry["nombre"] = nombre
        validated.append(entry)
    return validated


def load_distribucion_queue(queue_path: str, queue_directory: Path) -> dict[str, object]:
    """Lee y valida una cola de distribución dentro del directorio local queues."""
    allowed_directory = queue_directory.resolve()
    candidate_path = Path(queue_path).expanduser().resolve()
    if candidate_path.parent != allowed_directory:
        raise ValueError("La cola de distribución debe estar dentro del directorio local queues.")
    try:
        payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"La cola de distribución no es un JSON válido: {error.msg}") from error
    return {
        "leads": validate_distribucion_queue(payload),
        "modo": str(payload.get("modo") or DISTRIBUCION_MODO_DEFAULT),
        "run_id": str(payload.get("run_id") or "").strip(),
        "source_file": str(payload.get("source_file") or "").strip(),
    }


def mezclar_apertura(
    filas: list[dict],
    disponibles: list[dict],
    lead_ids: list[str],
) -> tuple[list[dict], dict]:
    """Mezcla filas de Distribuir con leads de apertura por ``lead_id``.

    ``filas`` son las filas ya cargadas (del archivo); ``disponibles`` la
    salida de ``apertura_store.disponibles``; ``lead_ids`` los seleccionados
    a agregar. Reglas:

    - ``lead_id`` ya presente en ``filas`` → queda la fila del archivo con
      su destino (el archivo manda); se reporta en ``duplicados``.
    - ``lead_id`` no disponible en el store → ``omitidos`` (nunca se
      inventa una fila para un ID que el store no conoce).
    - el resto → fila nueva con ``origen="apertura"``, persona vacía a
      completar; no marca consumo (eso lo hace la corrida confirmada).

    Devuelve ``(merged, {"agregados", "duplicados", "omitidos"})``.
    """
    por_id = {str(d.get("lead_id") or ""): d for d in disponibles or []}
    existentes = {str(f.get("lead_id") or "") for f in filas or []}
    merged = list(filas or [])
    agregados = 0
    duplicados: list[str] = []
    omitidos: list[str] = []
    for lead_id in [str(x or "").strip() for x in lead_ids or []]:
        if not lead_id:
            continue
        if lead_id in existentes:
            duplicados.append(lead_id)
            continue
        disp = por_id.get(lead_id)
        if not disp:
            omitidos.append(lead_id)
            continue
        merged.append(
            {
                "lead_id": lead_id,
                "nombre": "",
                "persona": "",
                "origen": "apertura",
                "bandeja": disp.get("bandeja") or "",
                "lote_id": disp.get("lote_id") or "",
            }
        )
        existentes.add(lead_id)
        agregados += 1
    return merged, {"agregados": agregados, "duplicados": duplicados, "omitidos": omitidos}
