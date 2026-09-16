from __future__ import annotations

import re
from dataclasses import dataclass

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


@dataclass(frozen=True)
class VisibleLead:
    lead_id: str
    created_at: str
    grid_position: int = 0
    status: str = "SIN_GESTION"


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


def is_unassigned_owner(value: str) -> bool:
    return str(value or "").strip() == UNASSIGNED_OWNER


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


def row_values(row_element, driver=None) -> list[str]:
    search_driver = driver or row_element
    cells = find_elements(search_driver, row_element, ROW_CELL_SELECTOR)
    return [cell.text.strip() for cell in cells]


def header_labels(table_element, driver=None) -> list[str]:
    search_driver = driver or table_element
    headers = find_elements(search_driver, table_element, HEADER_SELECTOR)
    return [header.text.strip() for header in headers if header.text.strip()]


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
) -> tuple[int, list[VisibleLead]]:
    table = find_report_table(driver, timeout_seconds)
    headers = header_labels(table, driver)
    owner_index = find_owner_header_index(headers)
    date_index = find_header_index(headers, DATE_HEADER)
    row_elements = find_report_rows(driver, table)
    data_rows = [
        row
        for row in row_elements
        if is_visible_element(row)
        and (row_values(row, driver) or str(row.text or "").strip())
    ]
    visible_rows = []
    for grid_position, row in enumerate(data_rows, start=1):
        values = row_values(row, driver)
        if owner_index is not None:
            if len(values) <= owner_index or not is_unassigned_owner(values[owner_index]):
                continue
        elif not row_has_unassigned_owner(values, row.text):
            continue
        created_at = extract_created_at(values, date_index)
        lead_id = extract_lead_id(row, driver, record_object_api_name)
        if not lead_id:
            continue
        visible_rows.append(
            VisibleLead(
                lead_id=lead_id,
                created_at=created_at,
                grid_position=grid_position,
            )
        )
    return len(data_rows), deduplicate_visible_leads(visible_rows)
