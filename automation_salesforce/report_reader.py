from __future__ import annotations

import re
from dataclasses import dataclass, field

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException


OWNER_HEADER = "propietario del candidato"
OWNER_HEADER_ALIASES = (OWNER_HEADER, "propietario")
DATE_HEADER = "fecha de creacion"
UNASSIGNED_OWNER = "AR_LEAD_QUALIF"
DEFAULT_RECORD_OBJECT_API_NAME = "Lead"
SALESFORCE_ID_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?)(?![A-Za-z0-9])"
)
DATE_VALUE_PATTERN = re.compile(
    r"(?<!\d)(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})(?!\d)"
)
REPORT_CANDIDATE_SELECTOR = (
    "table, [role='grid'], [role='treegrid'], lightning-datatable, lightning-base-datatable"
)
HEADER_SELECTOR = "thead th, [role='columnheader']"
HTML_ROW_SELECTOR = "tbody tr"
ARIA_ROW_SELECTOR = "[role='row']"
ROW_CELL_SELECTOR = "th[scope='row'], td, [role='gridcell']"
LEAD_ID_ATTRIBUTE_NAMES = (
    "data-recordid",
    "data-record-id",
    "data-row-key-value",
    "data-key",
    "data-id",
)
DEEP_SELECTOR_SCRIPT = """
const start = arguments[0] || document;
const selector = arguments[1];
const scopes = new Set();
const elements = new Set();
const matches = [];

function collect(scope) {
    if (!scope || scopes.has(scope)) {
        return;
    }
    scopes.add(scope);
    for (const element of scope.querySelectorAll(selector)) {
        if (!elements.has(element)) {
            elements.add(element);
            matches.push(element);
        }
    }
    for (const host of scope.querySelectorAll("*")) {
        if (host.shadowRoot) {
            collect(host.shadowRoot);
        }
    }
}

collect(start);
if (start.shadowRoot) {
    collect(start.shadowRoot);
}
return matches;
"""
LEAF_ROWS_SCRIPT = """
const rows = arguments[0];
return rows.filter(candidate => !rows.some(
    other => other !== candidate && candidate.contains(other)
));
"""
HORIZONTAL_SCROLL_SCRIPT = """
let current = arguments[0];
const reset = arguments[1];
while (current) {
    if (current.scrollWidth > current.clientWidth) {
        const before = current.scrollLeft;
        if (reset) {
            current.scrollLeft = 0;
            return {moved: before > 0, at_end: false};
        }
        current.scrollLeft = Math.min(current.scrollLeft + current.clientWidth, current.scrollWidth - current.clientWidth);
        return {moved: current.scrollLeft > before, at_end: current.scrollLeft >= current.scrollWidth - current.clientWidth};
    }
    const root = current.getRootNode ? current.getRootNode() : null;
    current = current.parentElement || (root && root.host) || null;
}
return {moved: false, at_end: true};
"""
VERTICAL_SCROLL_SCRIPT = """
let current = arguments[0];
while (current) {
    if (current.scrollHeight > current.clientHeight + 1) {
        const before = current.scrollTop;
        current.scrollTop = Math.min(current.scrollTop + Math.max(current.clientHeight - 80, 100), current.scrollHeight - current.clientHeight);
        return {moved: current.scrollTop > before};
    }
    const root = current.getRootNode ? current.getRootNode() : null;
    current = current.parentElement || (root && root.host) || null;
}
const before = window.scrollY;
window.scrollBy(0, Math.max(window.innerHeight - 80, 100));
return {moved: window.scrollY > before};
"""


@dataclass(frozen=True)
class VisibleLead:
    lead_id: str
    created_at: str
    grid_position: int = 0
    status: str = "SIN_GESTION"
    details: dict[str, str] = field(default_factory=dict)


def deduplicate_visible_leads(leads: list[VisibleLead]) -> list[VisibleLead]:
    """Elimina representaciones DOM repetidas sin descartar filas sin ID."""
    seen_lead_ids = set()
    unique_leads = []
    for lead in leads:
        if lead.lead_id and lead.lead_id in seen_lead_ids:
            continue
        unique_leads.append(lead)
        if lead.lead_id:
            seen_lead_ids.add(lead.lead_id)
    return unique_leads


def merge_visible_leads(leads: list[VisibleLead]) -> list[VisibleLead]:
    merged: dict[str, VisibleLead] = {}
    for lead in leads:
        previous = merged.get(lead.lead_id)
        if previous is None:
            merged[lead.lead_id] = lead
            continue
        details = {**previous.details, **{key: value for key, value in lead.details.items() if value}}
        merged[lead.lead_id] = VisibleLead(lead.lead_id, previous.created_at or lead.created_at, previous.grid_position, previous.status, details)
    return list(merged.values())


def scroll_table_right(driver, table_element, reset: bool = False) -> bool:
    result = driver.execute_script(HORIZONTAL_SCROLL_SCRIPT, table_element, reset)
    return bool(result.get("moved"))


def scroll_table_down(driver, table_element) -> bool:
    result = driver.execute_script(VERTICAL_SCROLL_SCRIPT, table_element)
    return bool(result.get("moved"))


def read_full_report(
    driver,
    timeout_seconds: int,
    record_object_api_name: str,
    field_aliases: dict[str, list[str]],
    diagnostics: list[dict[str, object]],
    max_vertical_passes: int = 80,
    max_horizontal_passes: int = 20,
) -> tuple[int, list[VisibleLead]]:
    """Recorre la bandeja de arriba hacia abajo y de izquierda a derecha, sin abrir Leads.

    Con ``max_vertical_passes=1`` funciona como lectura rápida: solo las filas ya
    cargadas, recorriendo las columnas horizontalmente.
    """
    collected: list[VisibleLead] = []
    total_rows_seen = 0
    for _ in range(max_vertical_passes):
        table = find_report_table(driver, timeout_seconds)
        scroll_table_right(driver, table, reset=True)
        known_ids = {lead.lead_id for lead in collected}
        for _ in range(max_horizontal_passes):
            visible_rows, leads = read_visible_unassigned_leads(
                driver, timeout_seconds, record_object_api_name, field_aliases, diagnostics
            )
            total_rows_seen = max(total_rows_seen, visible_rows)
            collected.extend(leads)
            table = find_report_table(driver, timeout_seconds)
            if not scroll_table_right(driver, table, reset=False):
                break
        new_ids = {lead.lead_id for lead in collected} - known_ids
        table = find_report_table(driver, timeout_seconds)
        if not scroll_table_down(driver, table) and not new_ids:
            break
    return total_rows_seen, merge_visible_leads(collected)


def normalize_label(value: str) -> str:
    return " ".join(
        str(value or "").lower().translate(str.maketrans("áéíóúüñ", "aeiouun")).split()
    )


def find_header_index(headers: list[str], expected_header: str) -> int | None:
    normalized = [normalize_label(header) for header in headers]
    try:
        return normalized.index(normalize_label(expected_header))
    except ValueError:
        return None


def find_owner_header_index(headers: list[str]) -> int | None:
    for header in OWNER_HEADER_ALIASES:
        index = find_header_index(headers, header)
        if index is not None:
            return index
    return None


def resolve_field_indexes(
    headers: list[str], field_aliases: dict[str, list[str]]
) -> dict[str, int | None]:
    return {
        field_name: next(
            (index for alias in aliases if (index := find_header_index(headers, alias)) is not None),
            None,
        )
        for field_name, aliases in field_aliases.items()
    }


def extract_row_details(
    values: list[str], field_indexes: dict[str, int | None]
) -> dict[str, str]:
    return {
        field_name: values[index].strip() if index is not None and index < len(values) else ""
        for field_name, index in field_indexes.items()
    }


def unmapped_columns(
    headers: list[str], values: list[str], field_indexes: dict[str, int | None]
) -> dict[str, str]:
    """Conserva toda columna leída de la bandeja aunque no tenga alias configurado."""
    mapped = {index for index in field_indexes.values() if index is not None}
    columns = {}
    for index, value in enumerate(values):
        if index in mapped or not str(value or "").strip():
            continue
        label = headers[index] if index < len(headers) and headers[index] else f"Columna {index + 1}"
        columns[f"col:{label}"] = str(value).strip()
    return columns


def is_unassigned_owner(value: str) -> bool:
    return re.sub(r"\s+", "", str(value or "")) == UNASSIGNED_OWNER


def is_visible_element(element) -> bool:
    visibility_check = getattr(element, "is_displayed", None)
    if visibility_check is None:
        return True
    try:
        return bool(visibility_check())
    except WebDriverException:
        return False


def row_has_unassigned_owner(values: list[str], row_text: str) -> bool:
    if any(is_unassigned_owner(value) for value in values):
        return True
    return any(is_unassigned_owner(line) for line in str(row_text or "").splitlines())


def find_elements(driver, root, selector: str):
    """Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe."""
    if hasattr(driver, "execute_script"):
        script_root = None if root is driver else root
        return driver.execute_script(DEEP_SELECTOR_SCRIPT, script_root, selector)
    return root.find_elements(By.CSS_SELECTOR, selector)


def find_report_rows(driver, table_element):
    """Prioriza filas HTML y elimina contenedores ARIA que duplican registros."""
    html_rows = find_elements(driver, table_element, HTML_ROW_SELECTOR)
    if html_rows:
        return html_rows

    aria_rows = find_elements(driver, table_element, ARIA_ROW_SELECTOR)
    if hasattr(driver, "execute_script") and aria_rows:
        try:
            return driver.execute_script(LEAF_ROWS_SCRIPT, aria_rows)
        except WebDriverException:
            pass
    return aria_rows


def record_route_pattern(record_object_api_name: str) -> re.Pattern:
    object_name = re.escape(record_object_api_name or DEFAULT_RECORD_OBJECT_API_NAME)
    return re.compile(
        rf"/{object_name}/([A-Za-z0-9]{{15}}(?:[A-Za-z0-9]{{3}})?)(?:/view|[/?#]|$)",
        re.IGNORECASE,
    )


def extract_lead_id(
    row_element,
    driver=None,
    record_object_api_name: str = DEFAULT_RECORD_OBJECT_API_NAME,
) -> str:
    search_driver = driver or row_element
    route_pattern = record_route_pattern(record_object_api_name)

    for link in find_elements(search_driver, row_element, "a[href]"):
        match = route_pattern.search(link.get_attribute("href") or "")
        if match:
            return match.group(1)

    for element in [row_element]:
        for attribute_name in LEAD_ID_ATTRIBUTE_NAMES:
            match = SALESFORCE_ID_PATTERN.search(
                element.get_attribute(attribute_name) or ""
            )
            if match:
                return match.group(1)
    return ""


def lead_id_from_values(values: list[str], lead_id_index: int | None) -> str:
    candidates = [values[lead_id_index]] if lead_id_index is not None and lead_id_index < len(values) else values
    for value in candidates:
        compact = re.sub(r"\s+", "", str(value or ""))
        if re.fullmatch(r"[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?", compact):
            return compact
    return ""


def row_diagnostics(row_element, owner_found: bool, lead_id_found: bool) -> dict[str, object]:
    """Metadatos por fila para diagnóstico local; nunca incluye valores de celdas."""
    return {
        "cell_count": len(row_values(row_element)),
        "text_length": len(str(row_element.text or "")),
        "owner_found": owner_found,
        "lead_id_found": lead_id_found,
    }


def row_values(row_element, driver=None) -> list[str]:
    search_driver = driver or row_element
    cells = find_elements(search_driver, row_element, ROW_CELL_SELECTOR)
    return [cell.text.strip() for cell in cells]


def header_labels(table_element, driver=None) -> list[str]:
    search_driver = driver or table_element
    headers = find_elements(search_driver, table_element, HEADER_SELECTOR)
    return [header.text.strip() for header in headers if header.text.strip()]


def report_header_labels(table_element, driver) -> list[str]:
    """Usa los encabezados de la grilla o, si Lightning los separa, los del reporte visible."""
    labels = header_labels(table_element, driver)
    if labels:
        return labels
    return header_labels(driver, driver)


def column_offset(headers: list[str], values: list[str]) -> int:
    """Alinea celdas con encabezados usando la columna de propietario como referencia."""
    owner_header = find_owner_header_index(headers)
    owner_cell = next((index for index, value in enumerate(values) if is_unassigned_owner(value)), None)
    if owner_header is None or owner_cell is None:
        return max(len(values) - len(headers), 0) if headers else 0
    return owner_cell - owner_header


def aligned_values(values: list[str], offset: int, header_count: int) -> list[str]:
    aligned = values[offset:] if offset > 0 else [""] * (-offset) + values
    return aligned[:header_count] if header_count else aligned


def extract_created_at(values: list[str], date_index: int | None) -> str:
    if date_index is not None and len(values) > date_index:
        return values[date_index]
    for value in values:
        match = DATE_VALUE_PATTERN.search(value)
        if match:
            return match.group(0)
    return ""


def report_structure_summary(driver) -> list[dict[str, object]]:
    """Devuelve metadatos estructurales sin leer valores de filas ni encabezados."""
    summary = []
    for table in find_elements(driver, driver, REPORT_CANDIDATE_SELECTOR):
        headers = header_labels(table, driver)
        rows = find_report_rows(driver, table)
        cell_counts = [len(find_elements(driver, row, ROW_CELL_SELECTOR)) for row in rows]
        summary.append(
            {
                "tag": table.tag_name,
                "role": table.get_attribute("role") or "",
                "header_count": len(headers),
                "owner_header_found": find_owner_header_index(headers) is not None,
                "row_count": len(rows),
                "rows_with_cells": sum(count > 0 for count in cell_counts),
                "max_cell_count": max(cell_counts, default=0),
            }
        )
    return summary


def report_accessibility_summary(driver) -> dict[str, object]:
    """Inspecciona contextos DOM sin extraer textos, celdas ni identificadores."""
    main_structure = report_structure_summary(driver)
    frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
    frame_summaries = []

    if not hasattr(driver, "switch_to"):
        return {
            "main_structure": main_structure,
            "frame_count": len(frames),
            "frames": frame_summaries,
        }

    for index in range(len(frames)):
        try:
            driver.switch_to.default_content()
            current_frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
            driver.switch_to.frame(current_frames[index])
            frame_summaries.append(
                {
                    "index": index,
                    "accessible": True,
                    "structure": report_structure_summary(driver),
                }
            )
        except WebDriverException:
            frame_summaries.append({"index": index, "accessible": False, "structure": []})
        finally:
            driver.switch_to.default_content()

    return {
        "main_structure": main_structure,
        "frame_count": len(frames),
        "frames": frame_summaries,
    }


def select_report_table(driver, require_owner_header: bool):
    ranked_candidates = []
    for table in find_elements(driver, driver, REPORT_CANDIDATE_SELECTOR):
        headers = header_labels(table, driver)
        owner_header_found = find_owner_header_index(headers) is not None
        if require_owner_header and not owner_header_found:
            continue
        row_count = len(find_report_rows(driver, table))
        if owner_header_found or row_count > 0:
            ranked_candidates.append((row_count, table))
    if not ranked_candidates:
        return None
    return max(ranked_candidates, key=lambda candidate: candidate[0])[1]


def find_report_table(driver, timeout_seconds: int):
    def table_with_owner_header(current_driver):
        current_driver.switch_to.default_content()
        table = select_report_table(current_driver, require_owner_header=True)
        if table is not None:
            return table

        frames = current_driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        for index in range(len(frames)):
            current_driver.switch_to.default_content()
            current_frames = current_driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
            current_driver.switch_to.frame(current_frames[index])
            table = select_report_table(current_driver, require_owner_header=True)
            if table is not None:
                return table

        for index in range(len(frames)):
            current_driver.switch_to.default_content()
            current_frames = current_driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
            current_driver.switch_to.frame(current_frames[index])
            table = select_report_table(current_driver, require_owner_header=False)
            if table is not None:
                return table

        current_driver.switch_to.default_content()
        table = select_report_table(current_driver, require_owner_header=False)
        if table is not None:
            return table
        current_driver.switch_to.default_content()
        return False

    return WebDriverWait(driver, timeout_seconds).until(table_with_owner_header)


def read_visible_unassigned_leads(
    driver,
    timeout_seconds: int,
    record_object_api_name: str = DEFAULT_RECORD_OBJECT_API_NAME,
    field_aliases: dict[str, list[str]] | None = None,
    diagnostics: list[dict[str, object]] | None = None,
) -> tuple[int, list[VisibleLead]]:
    table = find_report_table(driver, timeout_seconds)
    headers = report_header_labels(table, driver)
    date_index = find_header_index(headers, DATE_HEADER)
    field_indexes = resolve_field_indexes(headers, field_aliases or {})
    lead_id_index = field_indexes.get("lead_id")
    if diagnostics is not None:
        diagnostics.append({"headers": headers, "resolved_fields": [name for name, index in field_indexes.items() if index is not None]})
    row_elements = find_report_rows(driver, table)
    data_rows = [
        row
        for row in row_elements
        if is_visible_element(row)
        and (row_values(row, driver) or str(row.text or "").strip())
    ]
    visible_rows = []
    for grid_position, row in enumerate(data_rows, start=1):
        raw_values = row_values(row, driver)
        owner_found = row_has_unassigned_owner(raw_values, row.text)
        values = aligned_values(raw_values, column_offset(headers, raw_values), len(headers)) if headers else raw_values
        lead_id = extract_lead_id(row, driver, record_object_api_name) if owner_found else ""
        if owner_found and not lead_id:
            lead_id = lead_id_from_values(values, lead_id_index) or lead_id_from_values(raw_values, None)
        if diagnostics is not None:
            diagnostics.append(row_diagnostics(row, owner_found, bool(lead_id)))
        if not owner_found or not lead_id:
            continue
        created_at = extract_created_at(values, date_index)
        details = extract_row_details(values, field_indexes) if field_aliases else {}
        if details:
            details["lead_id"] = lead_id
            if not details.get("fecha_creacion"):
                details["fecha_creacion"] = created_at
            if not details.get("propietario_candidato"):
                details["propietario_candidato"] = UNASSIGNED_OWNER
            details.update(unmapped_columns(headers, values, field_indexes))
        visible_rows.append(
            VisibleLead(
                lead_id=lead_id,
                created_at=created_at,
                grid_position=grid_position,
                details=details,
            )
        )
    return len(data_rows), deduplicate_visible_leads(visible_rows)
