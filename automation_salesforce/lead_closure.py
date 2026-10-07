"""Contrato cerrado de motivos de cierre de Leads en Salesforce.

Valores exactos aprobados por el usuario — alimentan dashboards, no editar:

+-----------------+--------------+--------------------------+
| Campo           | ilocalizable | deja_de_interactuar      |
+-----------------+--------------+--------------------------+
| Comentario      | Ilocalizable | Cliente deja de          |
|                 |              | interactuar              |
| Cualificación   | Rechazo no   | Rechazo argumentado      |
|                 | argumentado  |                          |
| Sub-Cualificac. | Ilocalizable* | Interesado en precio o  |
|                 |              | condición                |
+-----------------+--------------+--------------------------+

* Si `Ilocalizable` no está disponible en Salesforce, la alternativa aprobada
  del mismo motivo es `Permanece ilocalizable`.

La decisión de cuándo cerrar es del auxiliar: no hay mínimo de intentos.
El éxito final exige ``Estado de candidato = Cerrado`` y
``Propietario del candidato = AR_LEAD_COLD`` tras ``Convert Lead → Yes``.
"""

from __future__ import annotations

FINAL_OWNER = "AR_LEAD_COLD"
CLOSED_STATE = "Cerrado"

CLOSURE_REASONS: dict[str, dict[str, object]] = {
    "ilocalizable": {
        "label": "Ilocalizable",
        "comentario": "Ilocalizable",
        "cualificacion": "Rechazo no argumentado",
        "subcualificacion": "Ilocalizable",
        "subcualificacion_alternativas": ("Permanece ilocalizable",),
    },
    "deja_de_interactuar": {
        "label": "Deja de interactuar",
        "comentario": "Cliente deja de interactuar",
        "cualificacion": "Rechazo argumentado",
        "subcualificacion": "Interesado en precio o condición",
    },
}

# Estados de resultado del runner de cierre. Separados de la documentación.
STATUS_VERIFIED = "cerrado_verificado"
STATUS_ALREADY_CLOSED = "ya_cerrado"
STATUS_CONVERSION_PENDING = "conversion_pendiente"
STATUS_CONVERSION_UNVERIFIED = "conversion_no_verificada"
STATUS_CONFLICT = "conflicto"
STATUS_REVIEW = "revision"
STATUS_ERROR = "error"


def reason_contract(reason: str) -> dict[str, object]:
    """Devuelve el contrato de valores del motivo o lanza ValueError."""
    contract = CLOSURE_REASONS.get(str(reason or "").strip())
    if contract is None:
        known = ", ".join(sorted(CLOSURE_REASONS))
        raise ValueError(f"Motivo de cierre desconocido: {reason!r} (válidos: {known}).")
    return contract


def contract_text(contract: dict[str, object], key: str) -> str:
    """Devuelve un valor textual del contrato."""
    return str(contract[key])


def subqualification_options(contract: dict[str, object]) -> tuple[str, ...]:
    """Etiquetas aprobadas de Sub-Cualificación, en orden de preferencia."""
    alternatives = contract.get("subcualificacion_alternativas", ())
    return (contract_text(contract, "subcualificacion"), *tuple(str(item) for item in alternatives))


# Etiquetas de los campos que participan del cierre (modo lectura y edición).
COMMENT_FIELD_LABELS = ("comentario",)
QUALIFICATION_FIELD_LABELS = ("cualificación", "cualificacion")
SUBQUALIFICATION_FIELD_LABELS = (
    "sub-cualificación", "sub-cualificacion", "subcualificación", "subcualificacion",
    "sub cualificación", "sub cualificacion",
)
STATE_FIELD_LABELS = ("estado de candidato", "estado del candidato")
OWNER_FIELD_LABELS = ("propietario del candidato",)
QUALIFICATION_SECTION_LABELS = ("cualificación", "cualificacion")

# Acciones de la página del Lead y del diálogo de confirmación.
CONVERT_ACTION_LABELS = ("convert lead", "convertir candidato", "convertir")
CONVERT_CONFIRM_LABELS = ("yes", "sí", "si")


# --------------------------------------------------------------------------
# Scripts DOM (recorren shadow DOM como los de comment_writer/comment_reader)
# --------------------------------------------------------------------------

CLOSURE_HELPERS_SCRIPT = r"""
function normalize(value) {
    return String(value || '')
        .toLocaleLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .trim()
        .replace(/\s+/g, ' ');
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

function ancestors(element, limit) {
    const list = [];
    let current = element;
    for (let depth = 0; depth < (limit || 12) && current; depth++) {
        list.push(current);
        const root = current.getRootNode ? current.getRootNode() : null;
        current = current.parentElement || (root && root.host) || null;
    }
    return list;
}

function fieldContainers(element) {
    return ancestors(element, 12).filter(current =>
        current.matches && current.matches(
            'records-record-layout-item, lightning-output-field, lightning-input-field, '
            + '.slds-form-element'
        ));
}

// Texto de la etiqueta asociada a un control editable dentro del formulario.
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
    for (const current of ancestors(candidate, 10)) {
        if (!current || !current.matches) {
            continue;
        }
        const attrLabel = current.getAttribute('label')
            || current.getAttribute('field-label');
        if (attrLabel) {
            return attrLabel;
        }
    }
    return '';
}

const elements = [];
collect(document, new Set(), elements);
"""

# Doble clic sobre el campo Comentario dentro de la sección Cualificación:
# Lightning abre el registro en edición en línea (equivalente al lápiz).
DBLCLICK_FIELD_SCRIPT = (
    CLOSURE_HELPERS_SCRIPT
    + r"""
const labels = arguments[0];
const sectionLabels = arguments[1];

function insideSection(element) {
    return ancestors(element, 14).some(current => {
        if (!current.matches || !current.matches(
            'section, article, .slds-card, [class*="section"], records-record-layout-section'
        )) {
            return false;
        }
        const descendants = [];
        collect(current, new Set(), descendants);
        return descendants.some(child =>
            child !== element && sectionLabels.includes(normalize(child.textContent))
            && !descendants.some(other => other !== child && child.contains(other)));
    });
}

const labelElements = elements.filter(element => isVisible(element)
    && labels.includes(normalize(element.textContent))
    && !elements.some(other => other !== element
        && element.contains(other)
        && labels.includes(normalize(other.textContent))));

const scoped = labelElements.filter(insideSection);
const targets = scoped.length ? scoped : labelElements;
if (!targets.length) {
    return 'not_found';
}
for (const label of targets) {
    const containers = fieldContainers(label);
    for (const container of containers) {
        // El valor del campo: la parte clicable para entrar en edición.
        const descendants = [];
        collect(container, new Set(), descendants);
        const valueTarget = descendants.find(element => element.matches
            && element.matches('lightning-formatted-text, .slds-form-element__static, '
                + '[data-output-element-id], slot, span'))
            || container;
        valueTarget.dispatchEvent(new MouseEvent('dblclick', {
            bubbles: true, cancelable: true, view: window,
        }));
        return 'clicked';
    }
}
return 'not_found';
"""
)

# Disparador del desplegable de un picklist identificado por su etiqueta.
PICKLIST_HELPERS_SCRIPT = (
    CLOSURE_HELPERS_SCRIPT
    + r"""
function visiblePicklistElement(element) {
    return isVisible(element) && !ancestors(element, 50).some(parent =>
        parent.getAttribute && (parent.getAttribute('aria-hidden') === 'true'
            || parent.getAttribute('hidden') !== null));
}

function picklistControl(labels) {
    const selector = 'input[role="combobox"], button[role="combobox"], '
        + 'input.slds-combobox__input, button.slds-combobox__input';
    const candidates = new Set();
    // Camino principal: lightning-base-combobox cuyo control interno lleva la
    // etiqueta del campo en aria-label (el <label> visible es hermano del host).
    const triggers = elements.filter(element => visiblePicklistElement(element)
        && element.matches(selector));
    for (const trigger of triggers) {
        if (labels.includes(normalize(labelForCandidate(trigger, elements)))) {
            candidates.add(trigger);
        }
    }
    // Respaldo: contenedor del campo con la etiqueta y un botón/input clicable.
    if (!candidates.size) {
        const labelElements = elements.filter(element => visiblePicklistElement(element)
            && labels.includes(normalize(element.textContent)));
        for (const label of labelElements) {
            const containers = fieldContainers(label);
            if (!containers.length) continue;
            const descendants = [];
            collect(containers[0], new Set(), descendants);
            descendants.filter(element => visiblePicklistElement(element)
                && element.matches(selector)).forEach(element => candidates.add(element));
        }
    }
    if (candidates.size > 1) {
        throw new Error('Campo de cualificación ambiguo: hay varios controles visibles.');
    }
    const control = [...candidates][0];
    return control && !control.disabled && control.getAttribute('aria-disabled') !== 'true'
        ? control : null;
}

function picklistListbox(labels) {
    const control = picklistControl(labels);
    if (!control || control.getAttribute('aria-expanded') !== 'true') return null;
    const ids = String(control.getAttribute('aria-controls') || '').split(/\s+/).filter(Boolean);
    const root = control.getRootNode();
    const listboxes = elements.filter(element => element.matches('[role="listbox"]')
        && ids.includes(element.id) && element.getRootNode() === root
        && visiblePicklistElement(element));
    if (listboxes.length > 1) throw new Error('Desplegable de cualificación ambiguo.');
    return listboxes[0] || null;
}

function picklistOptions(listbox) {
    if (!listbox) return [];
    const descendants = [];
    collect(listbox, new Set(), descendants);
    return descendants.filter(element => visiblePicklistElement(element)
        && element.matches('[role="option"], lightning-base-combobox-item'));
}
"""
)

PICKLIST_TRIGGER_SCRIPT = PICKLIST_HELPERS_SCRIPT + "return picklistControl(arguments[0]);"

# Opción del desplegable abierto, elegida por etiqueta exacta; si no está a la
# vista desplaza el listbox (la opción puede ser la última de una lista larga).
# Acepta una lista ordenada de etiquetas equivalentes: elige la primera
# disponible y sigue exigiendo coincidencia exacta.
PICK_OPTION_SCRIPT = (
    PICKLIST_HELPERS_SCRIPT
    + r"""
const requestedTexts = (Array.isArray(arguments[0]) ? arguments[0] : [arguments[0]]).map(normalize);
const control = picklistControl(arguments[1]);
const currentText = normalize(control ? (control.tagName === 'INPUT' ? control.value : control.textContent) : '');
const currentIndex = requestedTexts.indexOf(currentText);
if (currentIndex === 0) return 'selected';
const listbox = picklistListbox(arguments[1]);
if (!listbox) return 'not_found';
const options = picklistOptions(listbox);
// Textos candidatos de una opción: el host suele tener el valor API
// (p.ej. "Non argued refusal"); la etiqueta visible está dentro de su
// shadowRoot como <span title="...">, p.ej. "Rechazo no argumentado".
function textsForOption(option) {
    const texts = [
        option.textContent,
        option.getAttribute('title') || '',
        option.getAttribute('aria-label') || '',
    ];
    if (option.shadowRoot) {
        const inner = [];
        collect(option.shadowRoot, new Set(), inner);
        inner.forEach(child => {
            texts.push(child.textContent);
            texts.push(child.getAttribute('title') || '');
        });
    }
    return texts.map(normalize).filter(Boolean);
}
let selected = null;
for (const option of options) {
    const optionIndex = requestedTexts.findIndex(text => textsForOption(option).includes(text));
    if (optionIndex < 0) continue;
    if (selected && selected.index === optionIndex) return 'ambiguous';
    if (!selected || optionIndex < selected.index) {
        selected = {option, index: optionIndex};
    }
}
if (selected) {
    if (currentIndex >= 0 && selected.index >= currentIndex) return 'selected';
    selected.option.scrollIntoView({block: 'nearest', inline: 'nearest'});
    selected.option.click();
    return 'clicked';
}
if (listbox.scrollTop < listbox.scrollHeight - listbox.clientHeight - 1) {
    listbox.scrollTop += Math.max(listbox.clientHeight, 200);
    return 'scrolled';
}
return 'not_found';
"""
)

# Cantidad de opciones visibles en desplegables abiertos. Sirve para saber si
# un desplegable sigue abierto o un re-render de Lightning lo cerró.
OPEN_OPTIONS_COUNT_SCRIPT = PICKLIST_HELPERS_SCRIPT + "return picklistOptions(picklistListbox(arguments[0])).length;"

# Valor actualmente elegido de un combobox identificado por etiqueta:
# el botón/valor visible dentro de su shadowRoot.
PICKLIST_VALUE_SCRIPT = (
    PICKLIST_HELPERS_SCRIPT
    + r"""
// La etiqueta del campo está fuera del shadowRoot; el control interno la
// replica en aria-label (p.ej. aria-label="Cualificación").
const control = picklistControl(arguments[0]);
if (!control) return '';
// Con valor elegido el combobox renderiza <input readonly> (texto en
// `value`); sin elegir, un <button> con la etiqueta en textContent.
return normalize(control.tagName === 'INPUT' ? control.value : control.textContent);
"""
)


# Botón Convert Lead en la barra de acciones de la página del Lead.
RECORD_ACTION_SCRIPT = (
    CLOSURE_HELPERS_SCRIPT
    + r"""
const labels = arguments[0];
const candidates = elements.filter(element => isVisible(element) && element.matches(
    'button, a, lightning-button, lightning-button-item, li'
) && labels.includes(normalize(element.textContent)));
if (!candidates.length) {
    return 'not_found';
}
const inHeader = candidates.filter(element => ancestors(element, 12).some(current =>
    current.matches && current.matches(
        'records-highlights-item, .slds-page-header, [class*="highlights"], '
        + '[class*="actionsBar"], runtime_platform_actions-actions-bar'
    )));
const scoped = inHeader.length ? inHeader : candidates;
if (scoped.length !== 1) {
    return 'ambiguous';
}
const action = scoped[0];
action.scrollIntoView({block: 'center', inline: 'nearest'});
action.click();
return 'clicked';
"""
)

# Botón de confirmación (Yes) dentro del diálogo/modal de conversión visible.
MODAL_CONFIRM_SCRIPT = (
    CLOSURE_HELPERS_SCRIPT
    + r"""
const labels = arguments[0];
const dialogs = elements.filter(element => isVisible(element) && element.matches(
    '[role="dialog"], [role="alertdialog"], .slds-modal__container, .slds-modal, '
    + 'section[class*="modal"], lightning-modal'
));
for (const dialog of dialogs) {
    const descendants = [];
    collect(dialog, new Set(), descendants);
    const buttons = descendants.filter(element => isVisible(element) && element.matches(
        'button, lightning-button, a[role="button"], [role="button"]'
    ) && labels.includes(normalize(element.textContent)));
    if (buttons.length === 1) {
        buttons[0].click();
        return 'clicked';
    }
    if (buttons.length > 1) {
        return 'ambiguous';
    }
}
return 'not_found';
"""
)


# --------------------------------------------------------------------------
# Procedimientos Python
# --------------------------------------------------------------------------

import time  # noqa: E402
import unicodedata  # noqa: E402

from selenium.common.exceptions import TimeoutException, WebDriverException  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402

import comment_reader  # noqa: E402
from comment_writer import EDITOR_CONTROL_SCRIPT, SET_EDITOR_VALUE_SCRIPT, find_element_in_any_frame  # noqa: E402


def execute_in_any_frame(driver, script: str, *args):
    """Ejecuta el script en el documento principal y en iframes accesibles.

    Devuelve el primer resultado no vacío/no ``not_found`` de los frames.
    """
    switch_to = getattr(driver, "switch_to", None)
    if switch_to is None:
        return driver.execute_script(script, *args)

    results = []
    switch_to.default_content()
    try:
        results.append(driver.execute_script(script, *args))
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        for frame in frames:
            try:
                switch_to.frame(frame)
                results.append(driver.execute_script(script, *args))
            except WebDriverException:
                continue
            finally:
                switch_to.default_content()
    finally:
        switch_to.default_content()
    return next((r for r in results if r and r != "not_found"), results[0] if results else None)


def find_field_text(driver, labels: tuple[str, ...]) -> str:
    """Lee el valor de un campo en modo lectura; "" si el campo no está."""
    result = comment_reader.field_result_if_found(driver, labels)
    if not result:
        return ""
    return comment_reader.text_without_field_label(result["text"], labels)


def read_closure_state(driver, motive_labels: tuple[str, ...] = COMMENT_FIELD_LABELS) -> dict[str, str]:
    """Estado actual del Lead relevante para el cierre (sin datos sensibles).

    ``comentario`` siempre lee el campo Comentario (marca de duplicado); el
    campo del motivo depende del modo de país y queda en ``motivo``.
    """
    comentario = find_field_text(driver, COMMENT_FIELD_LABELS)
    return {
        "estado": find_field_text(driver, STATE_FIELD_LABELS),
        "propietario": find_field_text(driver, OWNER_FIELD_LABELS),
        "comentario": comentario,
        "motivo": comentario
        if motive_labels == COMMENT_FIELD_LABELS
        else find_field_text(driver, motive_labels),
    }


def open_qualification_edit(driver, timeout_seconds: int) -> None:
    """Doble clic en Comentario (sección Cualificación) para entrar en edición."""
    outcome = execute_in_any_frame(
        driver,
        DBLCLICK_FIELD_SCRIPT,
        list(COMMENT_FIELD_LABELS),
        list(QUALIFICATION_SECTION_LABELS),
    )
    if outcome == "ambiguous":
        raise ValueError("El campo Comentario es ambiguo para entrar en edición.")
    if outcome != "clicked":
        raise ValueError("No se encontró el campo Comentario en la sección Cualificación.")
    driver.switch_to.default_content()
    # La edición en línea tarda en renderizar los inputs del formulario.
    WebDriverWait(driver, timeout_seconds).until(
        lambda current: find_element_in_any_frame(current, EDITOR_CONTROL_SCRIPT, list(COMMENT_FIELD_LABELS))
    )


def set_comentario(driver, comentario: str, timeout_seconds: int) -> None:
    """Escribe el literal exacto del motivo en el input Comentario."""
    editor = find_element_in_any_frame(driver, EDITOR_CONTROL_SCRIPT, list(COMMENT_FIELD_LABELS))
    if not editor:
        raise ValueError("No se encontró el editor del campo Comentario.")
    driver.execute_script(SET_EDITOR_VALUE_SCRIPT, editor, comentario)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if str(editor.get_attribute("value") or "").strip() == comentario:
            return
        refreshed = find_element_in_any_frame(driver, EDITOR_CONTROL_SCRIPT, list(COMMENT_FIELD_LABELS))
        if refreshed:
            editor = refreshed
            driver.execute_script(SET_EDITOR_VALUE_SCRIPT, editor, comentario)
        time.sleep(0.3)
    raise ValueError("El campo Comentario no quedó con el literal del motivo.")


def _picklist_trigger(driver, labels: tuple[str, ...]):
    driver.switch_to.default_content()
    control = driver.execute_script(PICKLIST_TRIGGER_SCRIPT, list(labels))
    if control:
        return control
    for frame in driver.find_elements(By.CSS_SELECTOR, "iframe, frame"):
        if not frame.is_displayed():
            continue
        driver.switch_to.frame(frame)
        try:
            control = driver.execute_script(PICKLIST_TRIGGER_SCRIPT, list(labels))
            if control:
                return control
        except WebDriverException:
            driver.switch_to.default_content()
            raise
        driver.switch_to.default_content()
    return None


def _execute_picklist_script(driver, script: str, labels: tuple[str, ...], *args):
    try:
        if _picklist_trigger(driver, labels) is None:
            return None
        return driver.execute_script(script, *args, list(labels))
    finally:
        driver.switch_to.default_content()


def _open_options_count(driver, labels: tuple[str, ...]) -> int:
    count = _execute_picklist_script(driver, OPEN_OPTIONS_COUNT_SCRIPT, labels)
    return int(count) if isinstance(count, (int, float)) else 0


def _picklist_current_value(driver, labels: tuple[str, ...]) -> str:
    value = _execute_picklist_script(driver, PICKLIST_VALUE_SCRIPT, labels)
    return str(value or "").strip()


def select_picklist_option(
    driver,
    labels: tuple[str, ...],
    option_text: str | tuple[str, ...] | list[str],
    timeout_seconds: int,
) -> str:
    """Elige una etiqueta exacta y devuelve la variante que quedó seleccionada.

    ``option_text`` puede ser una lista ordenada de equivalentes aprobados. Si
    varias aparecen, gana la primera de la lista; si ninguna aparece, aborta.
    Lightning re-renderiza el formulario de forma asíncrona: si el desplegable
    se cierra solo, se vuelve a abrir antes de rendirse.
    """
    candidates = (option_text,) if isinstance(option_text, str) else tuple(option_text)
    if not candidates:
        raise ValueError("La lista de opciones del picklist no puede estar vacía.")
    # Misma normalización que el JS: minúsculas, sin acentos, espacios unificados.
    normalized_targets = [normalized_key(candidate) for candidate in candidates]
    current_value = normalized_key(_picklist_current_value(driver, labels))
    if current_value == normalized_targets[0]:
        return candidates[0]
    trigger = WebDriverWait(driver, timeout_seconds).until(lambda current: _picklist_trigger(current, labels))
    if trigger.get_attribute("aria-expanded") != "true":
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center', inline:'nearest'}); arguments[0].click();",
            trigger,
        )
    driver.switch_to.default_content()
    script_options = candidates[0] if len(candidates) == 1 else list(candidates)
    deadline = time.monotonic() + timeout_seconds
    empty_since = None
    reopened = 0
    while time.monotonic() < deadline:
        outcome = _execute_picklist_script(driver, PICK_OPTION_SCRIPT, labels, script_options)
        if outcome == "selected":
            current_value = normalized_key(_picklist_current_value(driver, labels))
            if current_value in normalized_targets:
                return candidates[normalized_targets.index(current_value)]
            empty_since = None
        elif outcome == "clicked":
            # Confirmar que la elección quedó visible en el combobox; un
            # re-render pudo descartar la selección apenas hecha.
            time.sleep(0.8)
            driver.switch_to.default_content()
            current_value = normalized_key(_picklist_current_value(driver, labels))
            if current_value in normalized_targets:
                return candidates[normalized_targets.index(current_value)]
            empty_since = None
        elif outcome == "ambiguous":
            raise ValueError(f"La opción '{option_text}' es ambigua en el desplegable.")
        else:
            current_value = normalized_key(_picklist_current_value(driver, labels))
            if current_value == normalized_targets[0]:
                return candidates[0]
            if _open_options_count(driver, labels) == 0:
                # Sin opciones visibles: el desplegable se cerró (re-render) o
                # el clic no abrió nada. Reintentar abrir unas pocas veces.
                if empty_since is None:
                    empty_since = time.monotonic()
                elif time.monotonic() - empty_since > 1.5 and reopened < 3:
                    refreshed = _picklist_trigger(driver, labels)
                    if refreshed and refreshed.get_attribute("aria-expanded") != "true":
                        driver.execute_script("arguments[0].click();", refreshed)
                        reopened += 1
                        empty_since = None
                    driver.switch_to.default_content()
            else:
                empty_since = None
        time.sleep(0.4)
    raise ValueError(f"No se pudo confirmar la opción exacta '{option_text}' en el desplegable del campo visible.")


def convert_lead(driver, timeout_seconds: int) -> None:
    """Pulsa Convert Lead en la barra de acciones del Lead."""
    outcome = execute_in_any_frame(driver, RECORD_ACTION_SCRIPT, list(CONVERT_ACTION_LABELS))
    if outcome == "ambiguous":
        raise ValueError("El botón Convert Lead es ambiguo en la página.")
    if outcome != "clicked":
        raise ValueError("No se encontró el botón Convert Lead en la página del Lead.")


def confirm_conversion(driver, timeout_seconds: int) -> None:
    """Confirma Yes únicamente dentro del diálogo de conversión visible."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        outcome = execute_in_any_frame(driver, MODAL_CONFIRM_SCRIPT, list(CONVERT_CONFIRM_LABELS))
        if outcome == "clicked":
            return
        if outcome == "ambiguous":
            raise ValueError("El botón Yes del diálogo de conversión es ambiguo.")
        time.sleep(0.5)
    raise TimeoutException("No apareció el diálogo de conversión con el botón Yes.")


def normalized_value(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def normalized_key(value: str) -> str:
    """Minúsculas + sin acentos + espacios unificados (paridad con el JS)."""
    return " ".join(
        "".join(
            char
            for char in unicodedata.normalize("NFD", str(value or "").lower())
            if unicodedata.category(char) != "Mn"
        ).split()
    )


def edit_form_matches(
    driver,
    contract: dict[str, object],
    field_labels: tuple[str, ...] = COMMENT_FIELD_LABELS,
    expected_value: str | None = None,
) -> bool:
    """El formulario de edición sigue mostrando los valores del motivo.

    ``field_labels``/``expected_value`` identifican el campo de texto visible
    en ese formulario: en Argentina es Comentario con el literal del motivo;
    en Colombia/México es Comentario conservando su texto previo (el motivo se
    escribe aparte en Otra información). Lightning re-renderiza el formulario
    en segundo plano y puede limpiar lo escrito: esto detecta la pérdida antes
    de pulsar Guardar."""
    expected = contract_text(contract, "comentario") if expected_value is None else expected_value
    editor = find_element_in_any_frame(driver, EDITOR_CONTROL_SCRIPT, list(field_labels))
    if editor is None:
        return False
    comentario = str(editor.get_attribute("value") or "").strip()
    if normalized_key(comentario) != normalized_key(expected):
        return False
    subqualification = normalized_key(_picklist_current_value(driver, SUBQUALIFICATION_FIELD_LABELS))
    return normalized_key(contract_text(contract, "cualificacion")) == normalized_key(
        _picklist_current_value(driver, QUALIFICATION_FIELD_LABELS)
    ) and subqualification in {normalized_key(option) for option in subqualification_options(contract)}


def motive_line_present(field_text: str, motive: str) -> bool:
    """El motivo aparece como línea propia dentro de un campo con texto previo."""
    target = normalized_key(motive)
    return any(normalized_key(line) == target for line in str(field_text or "").splitlines())


def verify_persisted_fields(
    driver,
    contract: dict[str, object],
    motive_labels: tuple[str, ...] = COMMENT_FIELD_LABELS,
    motive_check=None,
) -> bool:
    """El motivo y los picklists quedaron guardados con los literales exactos.

    ``motive_check`` personaliza cómo se acepta el campo del motivo: en
    Argentina se exige igualdad exacta (Comentario se reemplaza); en
    Colombia/México se exige que el literal siga presente al final de Otra
    información sin alterar el texto previo.
    """
    motive_text = find_field_text(driver, motive_labels)
    motive_ok = (
        motive_check(motive_text)
        if motive_check is not None
        else normalized_value(motive_text) == contract_text(contract, "comentario")
    )
    subqualification = normalized_value(find_field_text(driver, SUBQUALIFICATION_FIELD_LABELS))
    return (
        motive_ok
        and normalized_value(find_field_text(driver, QUALIFICATION_FIELD_LABELS))
        == contract_text(contract, "cualificacion")
        and subqualification in subqualification_options(contract)
    )


def is_final_closed(state: dict[str, str]) -> bool:
    """Éxito real del cierre: estado Cerrado y propietario AR_LEAD_COLD."""
    return (
        normalized_value(state.get("estado", "")) == CLOSED_STATE
        and normalized_value(state.get("propietario", "")) == FINAL_OWNER
    )


def already_closed(state: dict[str, str], contract: dict[str, object]) -> bool:
    """Resultado final ya presente y compatible con el motivo pedido."""
    return is_final_closed(state) and normalized_value(state.get("comentario", "")) == contract_text(
        contract, "comentario"
    )
