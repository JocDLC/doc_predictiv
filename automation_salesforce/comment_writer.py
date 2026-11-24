from __future__ import annotations

import re
import time
from pathlib import Path

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from comment_reader import OTHER_INFORMATION_LABELS, execute_in_any_frame

INT_PREFIX_PATTERN = re.compile(r"^\s*\d+\s+INT\b", re.IGNORECASE)
EDIT_CONTROL_FINDER_SCRIPT = """
const labels = arguments[0];

function findEditControl() {

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
}
"""
# Búsqueda y acción dentro de la misma evaluación: en Edge 158 un WebElement
# devuelto por JS muere antes de la llamada siguiente (stale al serializar),
# así que el lápiz, el editor y Guardar se ubican y se usan de una vez.
EDIT_CONTROL_SCRIPT = (
    EDIT_CONTROL_FINDER_SCRIPT
    + """
return findEditControl();
"""
)
CLICK_EDIT_CONTROL_ATOMIC_SCRIPT = (
    EDIT_CONTROL_FINDER_SCRIPT
    + """
const control = findEditControl();
if (!control) {
    return 'not_found';
}
control.scrollIntoView({block: 'center', inline: 'nearest'});
control.click();
return 'clicked';
"""
)
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
EDITOR_HELPERS_SCRIPT = """
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

function isEditable(candidate) {
    return isVisible(candidate)
        && candidate.matches('textarea, input:not([type="hidden"])')
        && !candidate.readOnly
        && !candidate.disabled;
}

function labelForCandidate(candidate, elements) {
    const aria = candidate.getAttribute('aria-label');
    if (aria) {
        return aria;
    }
    const labelledBy = candidate.getAttribute('aria-labelledby');
    if (labelledBy) {
        const target = elements.find(element => element.id === labelledBy);
        if (target) {
            return target.textContent;
        }
    }
    let current = candidate;
    for (let depth = 0; depth < 8 && current; depth++) {
        const root = current.getRootNode ? current.getRootNode() : null;
        current = current.parentElement || (root && root.host) || null;
        if (!current || !current.matches) {
            continue;
        }
        const attrLabel = current.getAttribute('label')
            || current.getAttribute('field-label');
        if (attrLabel) {
            return attrLabel;
        }
        const descendants = [];
        collect(current, new Set(), descendants);
        const labelTag = descendants.find(element => element.tagName === 'LABEL'
            && labels.includes(normalize(element.textContent)));
        if (labelTag) {
            return labelTag.textContent;
        }
        const labelText = descendants.find(element =>
            labels.includes(normalize(element.textContent))
            && !descendants.some(other => other !== element
                && element.contains(other)
                && labels.includes(normalize(other.textContent))));
        if (labelText) {
            return labelText.textContent;
        }
    }
    return '';
}

function labelElements(elements) {
    return elements.filter(element => isVisible(element)
        && labels.includes(normalize(element.textContent))
        && !elements.some(other => other !== element
            && element.contains(other)
            && labels.includes(normalize(other.textContent))));
}

function editorAlignedWithLabel(label, editors) {
    const labelBounds = label.getBoundingClientRect();
    let best = null;
    for (const editor of editors) {
        const bounds = editor.getBoundingClientRect();
        const verticalDistance = Math.abs(bounds.top - labelBounds.top);
        if (bounds.left < labelBounds.left || verticalDistance > 80) {
            continue;
        }
        const score = verticalDistance * 1000
            + Math.abs(bounds.left - labelBounds.right)
            + (editor.tagName === 'TEXTAREA' ? 0 : 500000);
        if (!best || score < best.score) {
            best = { editor, score };
        }
    }
    return best ? best.editor : null;
}

const elements = [];
collect(document, new Set(), elements);
const editors = elements.filter(isEditable);
"""
EDITOR_CONTROL_FINDER_SCRIPT = (
    EDITOR_HELPERS_SCRIPT
    + """
function findEditor() {
    for (const editor of editors) {
        if (labels.includes(normalize(labelForCandidate(editor, elements)))) {
            return editor;
        }
    }
    for (const label of labelElements(elements)) {
        const editor = editorAlignedWithLabel(label, editors);
        if (editor) {
            return editor;
        }
    }
    return null;
}
"""
)
EDITOR_CONTROL_SCRIPT = (
    EDITOR_CONTROL_FINDER_SCRIPT
    + """
return findEditor();
"""
)
EDITOR_PRESENT_ATOMIC_SCRIPT = (
    EDITOR_CONTROL_FINDER_SCRIPT
    + """
return findEditor() ? 'found' : 'not_found';
"""
)
SET_EDITOR_VALUE_ATOMIC_SCRIPT = (
    EDITOR_CONTROL_FINDER_SCRIPT
    + """
const editor = findEditor();
if (!editor) {
    return 'not_found';
}
editor.scrollIntoView({block: 'center', inline: 'nearest'});
editor.focus();
// El editor puede vivir dentro de un LWC (lightning-textarea/input): el
// framework re-sincroniza el nodo interno desde la propiedad `value` del
// host, así que un write solo en el textarea se pierde en silencio.
const host = editor.closest('lightning-textarea, lightning-input, lightning-combobox')
    || (editor.getRootNode && editor.getRootNode() && editor.getRootNode().host) || null;
if (host && host !== editor && 'value' in host) {
    try { host.value = arguments[1]; } catch (err) { /* propiedad de solo lectura */ }
}
editor.value = arguments[1];
// Los eventos deben cruzar el shadow boundary (composed) para que el
// formulario actualice su modelo; sin eso un commit posterior (picklist,
// blur de otro campo) re-sincroniza el editor vacío.
editor.dispatchEvent(new Event('input', {bubbles: true, composed: true}));
editor.dispatchEvent(new Event('change', {bubbles: true, composed: true}));
if (host && host !== editor) {
    host.dispatchEvent(new Event('change', {bubbles: true, composed: true}));
}
// Lightning confirma el valor del campo al perder el foco (blur/focusout);
// el clic JS sobre Guardar no lo genera y sin esto el formulario persiste
// el valor anterior en silencio (bug verificado en leads reales).
editor.blur();
editor.dispatchEvent(new FocusEvent('blur', {bubbles: true}));
editor.dispatchEvent(new FocusEvent('focusout', {bubbles: true}));
return editor.value;
"""
)
READ_EDITOR_VALUE_ATOMIC_SCRIPT = (
    EDITOR_CONTROL_FINDER_SCRIPT
    + """
const editor = findEditor();
return editor ? editor.value : 'not_found';
"""
)
# Deja el editor enfocado con todo su contenido seleccionado: el tipeo
# confiable que sigue (CDP Input.insertText) reemplaza la selección.
FOCUS_EDITOR_ATOMIC_SCRIPT = (
    EDITOR_CONTROL_FINDER_SCRIPT
    + """
const editor = findEditor();
if (!editor) {
    return 'not_found';
}
editor.scrollIntoView({block: 'center', inline: 'nearest'});
editor.focus();
if (editor.select) {
    editor.select();
}
const root = editor.getRootNode ? editor.getRootNode() : document;
return (document.activeElement === editor || (root && root.activeElement === editor)) ? 'focused' : 'focus_lost';
"""
)
EDITOR_DIAGNOSTIC_SCRIPT = (
    EDITOR_HELPERS_SCRIPT
    + """
const found = labelElements(elements);
return {
    matching_labels: found.length,
    label_tags: found.map(label => label.tagName + '.' + (label.className || '')).slice(0, 5),
    label_tops: found.map(label => Math.round(label.getBoundingClientRect().top)).slice(0, 5),
    visible_editors: editors.length,
    editor_tags: editors.map(editor => editor.tagName).slice(0, 60),
    editor_tops: editors.map(editor => Math.round(editor.getBoundingClientRect().top)).slice(0, 60),
    editor_labels: editors.map(editor => normalize(labelForCandidate(editor, elements))).slice(0, 15),
};
"""
)


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
    existing = str(existing_comment or "").rstrip()
    return f"{existing}\n{new_entry}" if existing else new_entry


def format_attempt(number: int, attempt: dict[str, str]) -> str:
    result = str(attempt.get("result") or "").strip()
    if not result:
        raise ValueError("El intento no tiene resultado para documentar.")
    return f"{number} INT\t{result}\t{attempt.get('date', '')}\t{attempt.get('time', '')}\t{attempt.get('call_id', '')}"


def compose_attempts(
    existing_comment: str,
    next_int: int,
    attempts: list[dict[str, str]],
) -> str:
    if next_int < 1:
        raise ValueError("El próximo INT debe ser mayor o igual a 1.")
    if not attempts:
        raise ValueError("El Lead no tiene intentos para documentar.")
    new_entries = "\n".join(format_attempt(next_int + index, attempt) for index, attempt in enumerate(attempts))
    existing = str(existing_comment or "").rstrip()
    return f"{existing}\n{new_entries}" if existing else new_entries


def find_element_in_any_frame(driver, script: str, labels: tuple = OTHER_INFORMATION_LABELS):
    """Devuelve un único control visible y deja el driver en su contexto."""
    switch_to = getattr(driver, "switch_to", None)
    if switch_to is None:
        return driver.execute_script(script, labels)

    switch_to.default_content()
    try:
        element = driver.execute_script(script, labels)
    except WebDriverException:
        element = None
    if element:
        return element
    frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
    for frame in frames:
        try:
            switch_to.frame(frame)
            element = driver.execute_script(script, labels)
            if element:
                return element
        except WebDriverException:
            pass
        switch_to.default_content()
    switch_to.default_content()
    return None


def find_edit_control(driver, labels: tuple = OTHER_INFORMATION_LABELS):
    edit_control = find_element_in_any_frame(driver, EDIT_CONTROL_SCRIPT, labels)
    if edit_control:
        return edit_control
    scroll_toward_other_information(driver, labels)
    return False


def find_editor_control(driver, labels: tuple = OTHER_INFORMATION_LABELS):
    return find_element_in_any_frame(driver, EDITOR_CONTROL_SCRIPT, labels)


def describe_editor_candidates(driver):
    return find_element_in_any_frame(driver, EDITOR_DIAGNOSTIC_SCRIPT)


def scroll_toward_other_information(driver, labels: tuple = OTHER_INFORMATION_LABELS) -> bool:
    switch_to = getattr(driver, "switch_to", None)
    if switch_to is None:
        result = driver.execute_script(FIELD_SCROLL_SCRIPT, labels)
        return bool(result.get("progressed"))

    results = []
    switch_to.default_content()
    try:
        results.append(driver.execute_script(FIELD_SCROLL_SCRIPT, labels))
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        for frame in frames:
            try:
                switch_to.frame(frame)
                results.append(driver.execute_script(FIELD_SCROLL_SCRIPT, labels))
            except WebDriverException:
                pass
            finally:
                switch_to.default_content()
    finally:
        switch_to.default_content()
    return any(result.get("progressed") for result in results)


CLICK_EDIT_CONTROL_SCRIPT = """
arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});
arguments[0].click();
"""

SAVE_BUTTON_FINDER_SCRIPT = (
    EDITOR_HELPERS_SCRIPT
    + """
function findSaveButton() {
    const saveLabels = ['guardar', 'save'];
    const candidates = elements.filter(element => isVisible(element)
        && element.matches('button')
        && saveLabels.includes(normalize(element.textContent)));
    const insideForm = element => {
        let current = element;
        for (let depth = 0; depth < 10 && current; depth++) {
            const root = current.getRootNode ? current.getRootNode() : null;
            current = current.parentElement || (root && root.host) || null;
            if (current && current.matches && current.matches(
                'footer, [class*="footer"], lightning-record-edit-form, records-record-edit-form'
            )) {
                return true;
            }
        }
        return false;
    };
    const preferred = candidates.filter(insideForm);
    return (preferred.length ? preferred : candidates)[0] || null;
}
"""
)
SAVE_BUTTON_SCRIPT = (
    SAVE_BUTTON_FINDER_SCRIPT
    + """
return findSaveButton();
"""
)
CLICK_SAVE_BUTTON_ATOMIC_SCRIPT = (
    SAVE_BUTTON_FINDER_SCRIPT
    + """
const saveButton = findSaveButton();
if (!saveButton) {
    return 'not_found';
}
saveButton.scrollIntoView({block: 'center', inline: 'nearest'});
saveButton.click();
return 'clicked';
"""
)


SAVE_SETTLE_SECONDS = 3.0


def save_edit_form(driver, timeout_seconds: int, settle_seconds: float = SAVE_SETTLE_SECONDS) -> None:
    """Pulsa Guardar del formulario de edición activo y espera a que se cierre.

    Salesforce cierra el editor antes de terminar de persistir; la pausa final
    evita que una navegación posterior aborte el guardado en curso.
    """
    WebDriverWait(driver, timeout_seconds).until(
        lambda current_driver: execute_in_any_frame(current_driver, CLICK_SAVE_BUTTON_ATOMIC_SCRIPT) == "clicked"
    )
    driver.switch_to.default_content()
    WebDriverWait(driver, timeout_seconds).until(
        lambda current_driver: (
            execute_in_any_frame(current_driver, EDITOR_PRESENT_ATOMIC_SCRIPT, list(OTHER_INFORMATION_LABELS))
            != "found"
        )
    )
    time.sleep(settle_seconds)


SET_EDITOR_VALUE_SCRIPT = """
const editor = arguments[0];
const text = arguments[1];
editor.scrollIntoView({block: 'center', inline: 'nearest'});
editor.focus();
editor.value = text;
editor.dispatchEvent(new Event('input', {bubbles: true}));
editor.dispatchEvent(new Event('change', {bubbles: true}));
// Lightning confirma el valor del campo al perder el foco (blur/focusout);
// el clic JS sobre Guardar no lo genera y sin esto el formulario persiste
// el valor anterior en silencio (bug verificado en leads reales).
editor.blur();
editor.dispatchEvent(new FocusEvent('blur', {bubbles: true}));
editor.dispatchEvent(new FocusEvent('focusout', {bubbles: true}));
"""


def replace_editor_value(driver, editor, prepared_comment: str) -> None:
    driver.execute_script(SET_EDITOR_VALUE_SCRIPT, editor, prepared_comment)


def verify_editor_value(editor, expected: str) -> bool:
    return editor.get_attribute("value") == expected


EDITOR_READY_SECONDS = 2.0
EDITOR_STABILITY_SECONDS = 0.8
# Teclado real (CDP): Lightning solo incorpora al borrador del formulario lo
# que llega por eventos de usuario confiables. Verificado en red: con
# `.value` + eventos sintéticos la petición de guardado viaja solo con {Id};
# con Input.insertText + Tab real el campo viaja y persiste.
TAB_KEY_EVENT = {"key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9}


def type_editor_value(driver, labels: tuple, text: str) -> str:
    """Escribe ``text`` en el editor del campo con teclado confiable.

    Enfoca y selecciona el editor en una evaluación atómica, inserta el texto
    con CDP (``Input.insertText``, reemplaza la selección) y confirma el campo
    con un Tab real (el ``blur()`` sintético no hace commit del borrador).
    Devuelve el valor leído del editor o ``"not_found"`` si no hay editor.
    """
    focus = execute_in_any_frame(driver, FOCUS_EDITOR_ATOMIC_SCRIPT, list(labels))
    if focus == "not_found":
        return "not_found"
    driver.execute_cdp_cmd("Input.insertText", {"text": text})
    for event_type in ("keyDown", "keyUp"):
        driver.execute_cdp_cmd("Input.dispatchKeyEvent", {"type": event_type, **TAB_KEY_EVENT})
    driver.switch_to.default_content()
    actual = execute_in_any_frame(driver, READ_EDITOR_VALUE_ATOMIC_SCRIPT, list(labels))
    return "not_found" if actual in (None, "not_found") else str(actual)


def _click_edit_control_atomic(driver, labels: tuple) -> bool:
    """Localiza y pulsa el lápiz del campo en una sola evaluación JS."""
    if execute_in_any_frame(driver, CLICK_EDIT_CONTROL_ATOMIC_SCRIPT, list(labels)) == "clicked":
        return True
    scroll_toward_other_information(driver, labels)
    return False


def prepare_other_information(
    driver,
    prepared_comment: str,
    timeout_seconds: int,
    labels: tuple = OTHER_INFORMATION_LABELS,
    display_name: str = "Otra información",
) -> None:
    WebDriverWait(driver, timeout_seconds).until(lambda current: _click_edit_control_atomic(current, labels))
    driver.switch_to.default_content()
    try:
        WebDriverWait(driver, timeout_seconds).until(
            lambda current: execute_in_any_frame(current, EDITOR_PRESENT_ATOMIC_SCRIPT, list(labels)) == "found"
        )
    except TimeoutException:
        diagnostic = describe_editor_candidates(driver)
        raise ValueError(f"No apareció el editor de '{display_name}'. Diagnóstico: {diagnostic}") from None
    try:
        # Lightning termina de inicializar el componente ~2s después de abrir el
        # editor; escribir antes de eso deja que el framework pise el valor.
        time.sleep(EDITOR_READY_SECONDS)
        for attempt in range(2):
            actual = type_editor_value(driver, labels, prepared_comment)
            if actual == prepared_comment:
                # Una segunda lectura confirma que el valor quedó estable y el
                # framework no lo restauró con el dato anterior del registro.
                time.sleep(EDITOR_STABILITY_SECONDS)
                actual = execute_in_any_frame(driver, READ_EDITOR_VALUE_ATOMIC_SCRIPT, list(labels))
                if actual == prepared_comment:
                    return
            if attempt == 0:
                time.sleep(0.5)
                continue
            observed = "" if actual == "not_found" else str(actual or "")
            raise ValueError(
                "El editor no quedó con el texto esperado "
                f"(esperado {len(prepared_comment)} caracteres, "
                f"real {len(observed)})."
            )
    finally:
        driver.switch_to.default_content()
