from __future__ import annotations

import re
from pathlib import Path

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from comment_reader import OTHER_INFORMATION_LABELS


INT_PREFIX_PATTERN = re.compile(r"^\s*\d+\s+INT\b", re.IGNORECASE)
EDIT_CONTROL_SCRIPT = """
const labels = arguments[0];

function normalize(value) {
    return String(value || '')
        .toLocaleLowerCase()
        .normalize('NFD')
        .replace(/[\\u0300-\\u036f]/g, '')
        .trim()
        .replace(/\\s+/g, ' ');
}

function isVisible(element) {
    if (!element || !element.isConnected) {
        return false;
    }
    const style = window.getComputedStyle(element);
    return style.display !== 'none'
        && style.visibility !== 'hidden'
        && element.getClientRects().length > 0;
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

const elements = [];
collect(document, new Set(), elements);
for (const element of elements) {
    if (!isVisible(element) || !labels.includes(normalize(element.textContent))) {
        continue;
    }
    const labelBounds = element.getBoundingClientRect();
    const candidates = [];
    for (const candidate of elements) {
        if (!isVisible(candidate)
            || !candidate.matches('button, a, [role="button"], lightning-button-icon, span')) {
            continue;
        }
        const description = normalize(
            candidate.getAttribute('title') || candidate.getAttribute('aria-label') || ''
        );
        const classes = normalize(candidate.getAttribute('class') || '');
        if (!(description.includes('edit') || description.includes('editar')
            || classes.includes('inline-edit'))) {
            continue;
        }
        const bounds = candidate.getBoundingClientRect();
        const verticalDistance = Math.abs(bounds.top - labelBounds.top);
        if (bounds.left >= labelBounds.left && verticalDistance <= 32) {
            candidates.push({ candidate, bounds, verticalDistance });
        }
    }
    candidates.sort((left, right) => {
        const leftScore = left.verticalDistance * 10000 + Math.abs(left.bounds.left - labelBounds.right);
        const rightScore = right.verticalDistance * 10000 + Math.abs(right.bounds.left - labelBounds.right);
        return leftScore - rightScore;
    });
    if (candidates.length) {
        return candidates[0].candidate;
    }
}
return null;
"""
FIELD_SCROLL_SCRIPT = """
const labels = arguments[0];

function normalize(value) {
    return String(value || '')
        .toLocaleLowerCase()
        .normalize('NFD')
        .replace(/[\\u0300-\\u036f]/g, '')
        .trim()
        .replace(/\\s+/g, ' ');
}

function isVisible(element) {
    if (!element || !element.isConnected) {
        return false;
    }
    const style = window.getComputedStyle(element);
    return style.display !== 'none'
        && style.visibility !== 'hidden'
        && element.getClientRects().length > 0;
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

const elements = [];
collect(document, new Set(), elements);
const fieldLabel = elements.find(element => isVisible(element)
    && labels.includes(normalize(element.textContent)));
if (fieldLabel) {
    fieldLabel.scrollIntoView({ block: 'center', inline: 'nearest' });
    return { field_found: true, progressed: true };
}

const scrollables = [document.scrollingElement];
for (const element of elements) {
    const style = window.getComputedStyle(element);
    const isScrollable = /auto|scroll/.test(style.overflowY)
        && element.scrollHeight > element.clientHeight;
    if (isScrollable && !scrollables.includes(element)) {
        scrollables.push(element);
    }
}
for (const element of scrollables) {
    if (element && element.scrollTop < element.scrollHeight - element.clientHeight - 1) {
        element.scrollBy(0, Math.max(element.clientHeight * 0.8, 500));
        return { field_found: false, progressed: true };
    }
}
return { field_found: false, progressed: false };
"""
EDITOR_CONTROL_SCRIPT = """
const labels = arguments[0];

function normalize(value) {
    return String(value || '')
        .toLocaleLowerCase()
        .normalize('NFD')
        .replace(/[\\u0300-\\u036f]/g, '')
        .trim()
        .replace(/\\s+/g, ' ');
}

function isVisible(element) {
    if (!element || !element.isConnected) {
        return false;
    }
    const style = window.getComputedStyle(element);
    return style.display !== 'none'
        && style.visibility !== 'hidden'
        && element.getClientRects().length > 0;
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
        if (current.matches && current.matches('.slds-form-element, lightning-input-field')) {
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
    if (!isVisible(element) || !labels.includes(normalize(element.textContent))) {
        continue;
    }
    for (const container of fieldContainers(element)) {
        const descendants = [];
        collect(container, new Set(), descendants);
        const editor = descendants.find(candidate => isVisible(candidate)
            && candidate.matches('textarea, input:not([type="hidden"])')
            && !candidate.readOnly
            && !candidate.disabled);
        if (editor) {
            return editor;
        }
    }
}
return null;
"""


def validate_draft_body(draft_body: str) -> str:
    normalized_body = " ".join(str(draft_body or "").split())
    if not normalized_body:
        raise ValueError("El borrador no puede estar vacío.")
    if INT_PREFIX_PATTERN.match(normalized_body):
        raise ValueError("El borrador no debe incluir el prefijo N INT.")
    return normalized_body


def load_draft_body(draft_path: str, queue_directory: Path) -> str:
    allowed_directory = queue_directory.resolve()
    candidate_path = Path(draft_path).expanduser().resolve()
    if candidate_path.parent != allowed_directory:
        raise ValueError("El borrador debe estar dentro del directorio local queues.")
    return validate_draft_body(candidate_path.read_text(encoding="utf-8"))


def compose_other_information(existing_comment: str, next_int: int, draft_body: str) -> str:
    if next_int < 1:
        raise ValueError("El próximo INT debe ser mayor o igual a 1.")
    normalized_body = validate_draft_body(draft_body)
    new_entry = f"{next_int} INT {normalized_body}"
    return f"{existing_comment}\n\n{new_entry}" if existing_comment else new_entry


def find_element_in_any_frame(driver, script: str):
    """Devuelve un único control visible y deja el driver en su contexto."""
    switch_to = getattr(driver, "switch_to", None)
    if switch_to is None:
        return driver.execute_script(script, OTHER_INFORMATION_LABELS)

    switch_to.default_content()
    element = driver.execute_script(script, OTHER_INFORMATION_LABELS)
    if element:
        return element
    frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
    for frame in frames:
        try:
            switch_to.frame(frame)
            element = driver.execute_script(script, OTHER_INFORMATION_LABELS)
            if element:
                return element
        except WebDriverException:
            pass
        switch_to.default_content()
    switch_to.default_content()
    return None


def find_edit_control(driver):
    edit_control = find_element_in_any_frame(driver, EDIT_CONTROL_SCRIPT)
    if edit_control:
        return edit_control
    scroll_toward_other_information(driver)
    return False


def find_editor_control(driver):
    return find_element_in_any_frame(driver, EDITOR_CONTROL_SCRIPT)


def scroll_toward_other_information(driver) -> bool:
    switch_to = getattr(driver, "switch_to", None)
    if switch_to is None:
        result = driver.execute_script(FIELD_SCROLL_SCRIPT, OTHER_INFORMATION_LABELS)
        return bool(result.get("progressed"))

    results = []
    switch_to.default_content()
    try:
        results.append(driver.execute_script(FIELD_SCROLL_SCRIPT, OTHER_INFORMATION_LABELS))
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        for frame in frames:
            try:
                switch_to.frame(frame)
                results.append(driver.execute_script(FIELD_SCROLL_SCRIPT, OTHER_INFORMATION_LABELS))
            except WebDriverException:
                pass
            finally:
                switch_to.default_content()
    finally:
        switch_to.default_content()
    return any(result.get("progressed") for result in results)


def replace_editor_value(editor, prepared_comment: str) -> None:
    editor.clear()
    editor.send_keys(prepared_comment)


def prepare_other_information(driver, prepared_comment: str, timeout_seconds: int) -> None:
    edit_control = WebDriverWait(driver, timeout_seconds).until(find_edit_control)
    edit_control.click()
    driver.switch_to.default_content()
    editor = WebDriverWait(driver, timeout_seconds).until(find_editor_control)
    replace_editor_value(editor, prepared_comment)
    driver.switch_to.default_content()
