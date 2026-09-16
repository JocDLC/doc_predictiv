from __future__ import annotations

import re

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from report_reader import DEFAULT_RECORD_OBJECT_API_NAME


OTHER_INFORMATION_LABELS = ("otra información", "otra informacion")
SALESFORCE_ID_PATTERN = re.compile(r"[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?$")
RECORD_OBJECT_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]*$")
INT_PATTERN = re.compile(r"^\s*(\d+)\s+INT\b", re.IGNORECASE | re.MULTILINE)
FIELD_TEXT_SCRIPT = """
const labels = arguments[0];

function normalize(value) {
    return String(value || '')
        .toLocaleLowerCase()
        .normalize('NFD')
        .replace(/[\\u0300-\\u036f]/g, '')
        .trim()
        .replace(/\\s+/g, ' ');
}

function collect(scope, visited, elements) {
    if (!scope || visited.has(scope)) {
        return;
    }
    visited.add(scope);
    for (const element of scope.querySelectorAll('*')) {
        elements.push(element);
        if (element.shadowRoot) {
            collect(element.shadowRoot, visited, elements);
        }
    }
}

function fieldContainers(element) {
    const containers = [];
    let current = element;
    while (current) {
        if (current.matches && current.matches(
            'records-record-layout-item, lightning-output-field, .slds-form-element'
        )) {
            containers.push(current);
        }
        const root = current.getRootNode ? current.getRootNode() : null;
        current = current.parentElement || (root && root.host) || null;
    }
    return containers;
}

function textAfterLabel(value) {
    const lines = String(value || '').split(/\\r?\\n/).map(line => line.trim());
    const labelIndex = lines.findIndex(line => labels.includes(normalize(line)));
    if (labelIndex >= 0) {
        return lines.slice(labelIndex + 1).filter(Boolean).join('\\n').trim();
    }
    return String(value || '').trim();
}

function isVisible(element) {
    if (!element || !element.isConnected) {
        return false;
    }
    const style = window.getComputedStyle(element);
    return style.display !== 'none'
        && style.visibility !== 'hidden'
        && style.opacity !== '0'
        && element.getClientRects().length > 0;
}

function valueFromField(container) {
    const descendants = [];
    collect(container, new Set(), descendants);
    const preferred = descendants.filter(element => element.matches && element.matches(
        'textarea, input:not([type="hidden"]), lightning-formatted-text, '
        + 'lightning-base-formatted-text, .slds-form-element__static, [data-output-element-id]'
    ));
    for (const element of preferred) {
        const rawValue = element.value || element.innerText || element.textContent || '';
        const value = textAfterLabel(rawValue);
        if (value && !labels.includes(normalize(value))) {
            return value;
        }
    }
    const ignoredLeafTexts = new Set([...labels, 'edit', 'editar']);
    const leafValues = [];
    for (const element of descendants) {
        if (element.children.length || element.shadowRoot || element.matches('button, script, style')) {
            continue;
        }
        const value = textAfterLabel(element.value || element.innerText || element.textContent || '');
        if (value && !ignoredLeafTexts.has(normalize(value))) {
            leafValues.push(value);
        }
    }
    if (leafValues.length) {
        return leafValues.join('\\n');
    }
    return textAfterLabel(container.innerText || container.textContent || '');
}

const elements = [];
collect(document, new Set(), elements);
for (const element of elements) {
    if (!isVisible(element) || !labels.includes(normalize(element.textContent))) {
        continue;
    }
    const containers = fieldContainers(element);
    for (const container of containers) {
        const value = valueFromField(container);
        if (value) {
            return { found: true, text: value };
        }
    }
    if (containers.length) {
        return { found: true, text: '' };
    }
}
return { found: false, text: '' };
"""
FIELD_STRUCTURE_SCRIPT = """
const labels = arguments[0];

function normalize(value) {
    return String(value || '')
        .toLocaleLowerCase()
        .normalize('NFD')
        .replace(/[\\u0300-\\u036f]/g, '')
        .trim()
        .replace(/\\s+/g, ' ');
}

function collect(scope, visited, elements) {
    if (!scope || visited.has(scope)) {
        return;
    }
    visited.add(scope);
    for (const element of scope.querySelectorAll('*')) {
        elements.push(element);
        if (element.shadowRoot) {
            collect(element.shadowRoot, visited, elements);
        }
    }
}

function fieldContainers(element) {
    const containers = [];
    let current = element;
    while (current) {
        if (current.matches && current.matches(
            'records-record-layout-item, lightning-output-field, .slds-form-element'
        )) {
            containers.push(current);
        }
        const root = current.getRootNode ? current.getRootNode() : null;
        current = current.parentElement || (root && root.host) || null;
    }
    return containers;
}

const elements = [];
collect(document, new Set(), elements);
for (const element of elements) {
    if (!labels.includes(normalize(element.textContent))) {
        continue;
    }
    const containers = fieldContainers(element).map(container => {
        const descendants = [];
        collect(container, new Set(), descendants);
        return {
            tag: container.tagName.toLowerCase(),
            role: container.getAttribute('role') || '',
            text_length: (container.innerText || container.textContent || '').length,
            descendants: descendants.slice(0, 40).map(child => ({
                tag: child.tagName.toLowerCase(),
                role: child.getAttribute('role') || '',
                text_length: (child.innerText || child.textContent || '').length,
                value_length: String(child.value || '').length,
                editable: Boolean(child.isContentEditable)
            }))
        };
    });
    return { label_found: true, containers };
}
return { label_found: false, containers: [] };
"""


def normalize_label(value: str) -> str:
    return " ".join(
        str(value or "").lower().translate(str.maketrans("áéíóúüñ", "aeiouun")).split()
    )


def text_without_field_label(field_text: str) -> str:
    lines = str(field_text or "").splitlines()
    if lines and normalize_label(lines[0]) in OTHER_INFORMATION_LABELS:
        return "\n".join(lines[1:]).strip()
    return str(field_text or "").strip()


def field_result_if_found(driver):
    result = field_result_in_any_frame(driver, FIELD_TEXT_SCRIPT)
    return result if result.get("found") else False


def field_result_in_any_frame(driver, script: str) -> dict:
    """Busca el campo visible en el documento principal y en iframes accesibles."""
    switch_to = getattr(driver, "switch_to", None)
    if switch_to is None:
        return driver.execute_script(script, OTHER_INFORMATION_LABELS)

    results = []
    switch_to.default_content()
    try:
        results.append(driver.execute_script(script, OTHER_INFORMATION_LABELS))
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        for frame in frames:
            try:
                switch_to.frame(frame)
                results.append(driver.execute_script(script, OTHER_INFORMATION_LABELS))
            except WebDriverException:
                continue
            finally:
                switch_to.default_content()
    finally:
        switch_to.default_content()

    found_results = [result for result in results if result.get("found")]
    return next(
        (result for result in found_results if result.get("text")),
        found_results[0] if found_results else {"found": False, "text": ""},
    )


def field_result_with_text(driver):
    result = field_result_if_found(driver)
    return result if result and result.get("text") else False


def find_other_information(driver, timeout_seconds: int) -> str:
    try:
        result = WebDriverWait(driver, timeout_seconds).until(field_result_with_text)
    except TimeoutException:
        result = field_result_if_found(driver)
        if not result:
            raise
    return text_without_field_label(result["text"])


def other_information_structure_summary(driver) -> dict:
    """Devuelve solo metadatos del DOM; nunca texto del comentario."""
    return field_result_in_any_frame(driver, FIELD_STRUCTURE_SCRIPT)


def next_attempt_number(comment: str) -> int:
    attempt_numbers = [int(match.group(1)) for match in INT_PATTERN.finditer(comment or "")]
    return max(attempt_numbers, default=0) + 1


def build_record_url(
    salesforce_url: str,
    record_id: str,
    record_object_api_name: str = DEFAULT_RECORD_OBJECT_API_NAME,
) -> str:
    normalized_id = str(record_id or "").strip()
    object_name = str(record_object_api_name or DEFAULT_RECORD_OBJECT_API_NAME).strip()
    if not SALESFORCE_ID_PATTERN.fullmatch(normalized_id):
        raise ValueError("El Lead ID debe tener 15 o 18 caracteres alfanuméricos.")
    if not RECORD_OBJECT_PATTERN.fullmatch(object_name):
        raise ValueError("El objeto Salesforce configurado no es válido.")
    return f"{salesforce_url.rstrip('/')}/lightning/r/{object_name}/{normalized_id}/view"
