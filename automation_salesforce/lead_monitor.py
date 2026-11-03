"""Ciclo del Monitor de Bandeja: detecta leads sin asignar y los toma con Pick Up.

El módulo expone funciones pequeñas sobre el driver para que los tests puedan
sustituirlas sin Selenium real. La política de tiempos y el loop viven en
``ui_server.py``; aquí está solo la lógica de un ciclo.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from selenium.common.exceptions import TimeoutException, WebDriverException

from comment_reader import (
    build_record_url,
    field_result_if_found,
    find_field_text,
    normalize_label,
    text_without_field_label,
)
from comment_writer import (
    OTHER_INFORMATION_LABELS,
    SAVE_SETTLE_SECONDS,
    prepare_other_information,
    save_edit_form,
    scroll_toward_other_information,
)
from lead_closure import (
    CLOSURE_HELPERS_SCRIPT,
    MODAL_CONFIRM_SCRIPT,
    OWNER_FIELD_LABELS,
    RECORD_ACTION_SCRIPT,
    execute_in_any_frame,
    normalized_key,
    normalized_value,
)
from monitor_store import (
    PAUSE_SESSION_LOST,
    STATUS_DETECTADO,
    STATUS_ERROR,
    STATUS_NO_VERIFICADO,
    STATUS_TOMADO,
    STATUS_TOMADO_POR_OTRO,
    record_result,
    should_process,
    within_schedule,
)
from report_reader import read_visible_unassigned_leads
from salesforce_session import is_authenticated, wait_for_lightning_ready

# El botón de la barra de acciones del registro; normalize() en el script
# ya baja a minúsculas y quita acentos.
PICK_UP_LABELS = ("pick up", "pickup", "recoger")
OWNER_FIELD_TIMEOUT_SECONDS = 10
OWNER_VERIFY_TIMEOUT_SECONDS = 15
OWNER_DIALOG_OPEN_WAIT_SECONDS = 8
POLL_SECONDS = 0.5

# Devolución a la cola: acción y confirmación del diálogo "Cambiar propietario",
# más el conmutador de tipo (Usuarios → Colas) y las etiquetas del menú de
# overflow donde puede esconderse la acción.
CHANGE_OWNER_ACTION_LABELS = ("cambiar propietario", "change owner")
CHANGE_OWNER_CONFIRM_LABELS = ("cambiar propietario", "change owner")
OWNER_SCOPE_QUEUE_LABELS = ("colas", "queues", "queue", "cola")
OVERFLOW_MENU_LABELS = ("mostrar mas acciones", "mas acciones", "show more actions", "more actions")
QUEUE_SEARCH_TIMEOUT_SECONDS = 15
# El lookup del modal tarda en quedar listo: escribir apenas aparece el
# input deja el texto pero NO dispara la búsqueda (como pegar enseguida a
# mano). Settle corto antes de tipear + un re-tipeo si no hay opciones.
OWNER_LOOKUP_SETTLE_SECONDS = 3

# Panel "Contact Client" que Lightning muestra tras el Pick Up: solo hay que
# pulsar su Save para que la toma quede firme (sin escribir en su sección).
# La marca del bot va únicamente en "Otra información".
BOT_TAKE_MARK = "Asignado"
PANEL_WAIT_SECONDS = 15
# Reintento corto tras escribir la marca: el panel puede renderizar tarde
# (bajo carga) y quedar abierto sin su Save si no se vuelve a mirar.
LATE_PANEL_WAIT_SECONDS = 4

# Primer contacto por WhatsApp (cambio envio-whatsapp-automatico): solo
# bandeja AR + toggle de UI + preferencia "vía whatsapp". El intento se
# documenta en "Otra información" con el formato de los auxiliares y en
# lugar de la marca Asignado, antes de pulsar el botón del encabezado.
WA_TOAST_WAIT_SECONDS = 15
# Línea documentada por humano o bot: ``N INT ...`` (1 INT Se envía WhatsApp,
# 1 INT Cliente contesta, ...). Si ya existe, el lead está gestionado y no
# se duplica ni marca ni intento.
_INTENT_LINE_RE = re.compile(r"\b\d+\s*int\b", re.IGNORECASE)
# Tras el Save del panel la zona de detalles se reconstruye (render lazy);
# sin esta espera el campo se lee como "" siendo "no renderizado", no "vacío".
FIELD_RENDER_WAIT_SECONDS = 8

_CONTACT_PANEL_HELPERS = (
    CLOSURE_HELPERS_SCRIPT
    + r"""
function scopeHasExactSave(scope) {
    const descendants = [];
    collect(scope, new Set(), descendants);
    return descendants.some(el => isVisible(el) && el.matches('button')
        && ['save', 'guardar'].includes(normalize(el.textContent)));
}
function scopeLooksLikeContactPanel(scope) {
    // Firma estructural: el panel real trae "Save & SendEmail" además del
    // Save pelado — o al menos un campo de comentarios junto al Save.
    const descendants = [];
    collect(scope, new Set(), descendants);
    const hasEmailButton = descendants.some(el => isVisible(el)
        && el.matches('button') && /email|correo/.test(normalize(el.textContent)));
    const hasTextarea = descendants.some(el => isVisible(el)
        && el.matches('textarea, [contenteditable="true"]'));
    return hasEmailButton || hasTextarea;
}
function isFloating(el) {
    // Paneles docked/composer/overlays propios: contenedor flotante aunque
    // no use las clases estándar de modal/panel.
    return el && getComputedStyle(el).position === 'fixed';
}
function contactPanel() {
    // 1) Por título conocido (Contact Client / Estatus de la llamada...).
    const anchors = elements.filter(el => isVisible(el) && el.children.length === 0
        && /contact client|contactar|estatus de la llamada|estado de la llamada/.test(
            normalize(el.textContent)));
    for (const anchor of anchors) {
        for (const scope of ancestors(anchor, 10)) {
            if (scopeHasExactSave(scope)) {
                return scope;
            }
        }
    }
    // 2) Por estructura: botón Save exacto dentro de un contenedor de panel
    //    (selectores conocidos O cualquier ancestro flotante — el panel
    //    real puede ser un docked composer / overlay con clases propias)
    //    que también tiene SendEmail o un textarea de comentarios.
    const saveButtons = elements.filter(el => isVisible(el) && el.matches('button')
        && ['save', 'guardar'].includes(normalize(el.textContent)));
    for (const button of saveButtons) {
        for (const scope of ancestors(button, 12)) {
            if (!scope.matches) {
                continue;
            }
            const knownContainer = scope.matches(
                '[role="dialog"], [role="alertdialog"], .slds-modal__container, '
                + '.slds-panel, .slds-docked-composer, section[class*="modal"], '
                + 'lightning-quick-action-panel, lightning-modal');
            if (!knownContainer && !isFloating(scope)) {
                continue;
            }
            if (scopeHasExactSave(scope) && scopeLooksLikeContactPanel(scope)) {
                return scope;
            }
        }
    }
    return null;
}
function panelSaveButton(panel) {
    const descendants = [];
    collect(panel, new Set(), descendants);
    // Coincidencia exacta: excluye "Save & SendEmail" y similares.
    return descendants.find(el => isVisible(el) && el.matches('button')
        && ['save', 'guardar'].includes(normalize(el.textContent))) || null;
}
// Diagnóstico cuando el panel no se detecta: encabezados de los
// diálogos/paneles visibles + cadena de ancestros de cada botón
// Save/SendEmail visible, para descubrir contenedores no conocidos.
function domChain(el) {
    const parts = [];
    let current = el;
    while (current && current !== document.body && parts.length < 8) {
        const tag = current.tagName ? current.tagName.toLowerCase() : '?';
        const cls = ((current.getAttribute && current.getAttribute('class')) || '')
            .split(/\s+/).filter(name => name).slice(0, 2).join('.');
        const role = current.getAttribute && current.getAttribute('role');
        const pos = current.ownerDocument ? getComputedStyle(current).position : '';
        parts.push(tag + (cls ? '.' + cls : '') + (role ? '[role=' + role + ']' : '')
            + (pos === 'fixed' ? '{fixed}' : ''));
        current = current.parentElement || (current.getRootNode && current.getRootNode().host);
    }
    return parts.join(' < ');
}
function panelDiagnostics() {
    const findings = [];
    for (const el of elements) {
        if (!isVisible(el) || !el.matches || !el.matches(
            '[role="dialog"], [role="alertdialog"], .slds-modal__container, '
            + '.slds-panel, .slds-docked-composer, section[class*="modal"], '
            + 'lightning-quick-action-panel, lightning-modal')) {
            continue;
        }
        const descendants = [];
        collect(el, new Set(), descendants);
        const heading = descendants.find(child => child.matches
            && child.matches('h1, h2, h3, [class*="title"], [class*="header"]')
            && child.textContent.trim());
        findings.push('panel:' + normalize((heading || el).textContent).slice(0, 60));
    }
    const buttons = elements.filter(el => isVisible(el) && el.matches('button')
        && (['save', 'guardar'].includes(normalize(el.textContent))
            || /email|correo/.test(normalize(el.textContent))));
    for (const button of buttons.slice(0, 4)) {
        findings.push('btn:' + normalize(button.textContent).slice(0, 20) + ' < ' + domChain(button));
    }
    return findings.slice(0, 8);
}
"""
)

PANEL_PRESENT_SCRIPT = _CONTACT_PANEL_HELPERS + "return contactPanel() ? 'found' : 'missing';"
PANEL_SAVE_CLICK_SCRIPT = (
    _CONTACT_PANEL_HELPERS + "const p = contactPanel(); if (!p) return 'no_panel'; "
    "const b = panelSaveButton(p); if (!b) return 'no_button'; b.click(); return 'clicked';"
)
# Qué diálogos/paneles hay visibles cuando el panel no se detectó (diagnóstico).
PANEL_DIAGNOSTIC_SCRIPT = _CONTACT_PANEL_HELPERS + "return panelDiagnostics();"

_SEND_WHATSAPP_HELPERS = (
    CLOSURE_HELPERS_SCRIPT
    + r"""
function whatsappSendButton() {
    // Botón del ribbon de acciones del registro ("Send To Whatsapp").
    const candidates = elements.filter(el => isVisible(el)
        && el.matches('button, [role="button"], a')
        && /whatsapp/.test(normalize(el.textContent)));
    return candidates.find(el => /send to whatsapp|send whatsapp|enviar whatsapp/.test(
        normalize(el.textContent))) || null;
}
function confirmationToast() {
    // Toast verde "Message sent to Whatsapp! Please follow the sending
    // status of this message." — puede vivir en contenedores del shell.
    return elements.find(el => isVisible(el) && el.matches(
        '[class*="toast"], [role="status"], [role="alert"], .slds-notify, '
        + '[class*="notify"], lightning-toast-container')
        && /whatsapp/.test(normalize(el.textContent))
        && /sent|enviad|exit|status|seguimiento/.test(normalize(el.textContent))) || null;
}
"""
)
SEND_WHATSAPP_CLICK_SCRIPT = (
    _SEND_WHATSAPP_HELPERS
    + "const b = whatsappSendButton(); if (!b) return 'sin_boton'; b.click(); return 'clicked';"
)
WA_TOAST_PRESENT_SCRIPT = _SEND_WHATSAPP_HELPERS + "return confirmationToast() ? 'found' : 'missing';"
WA_TOAST_CLOSE_SCRIPT = (
    _SEND_WHATSAPP_HELPERS
    + r"""
const t = confirmationToast(); if (!t) return 'sin_toast';
const descendants = []; collect(t, new Set(), descendants);
const close = descendants.find(el => isVisible(el) && el.matches('button, [role="button"]')
    && (/close|cerrar/.test(normalize((el.getAttribute('title') || '') + ' '
        + (el.getAttribute('aria-label') || '')))
        || el.matches('.slds-notify__close, [class*="close"]')));
if (!close) return 'sin_cierre';
close.click(); return 'closed';
"""
)

_OWNER_DIALOG_HELPERS = (
    CLOSURE_HELPERS_SCRIPT
    + r"""
function ownerDialog() {
    const dialogs = elements.filter(element => isVisible(element) && element.matches(
        '[role="dialog"], [role="alertdialog"], .slds-modal__container, section[class*="modal"], lightning-modal'));
    for (const dialog of dialogs) {
        const descendants = [];
        collect(dialog, new Set(), descendants);
        if (descendants.some(el => el.matches('h1, h2, h3, [class*="title"], .slds-modal__header')
            && /propietario|owner/i.test(normalize(el.textContent)))) {
            return dialog;
        }
    }
    return null;
}
function dialogDescendants(dialog) {
    const descendants = [];
    collect(dialog, new Set(), descendants);
    return descendants;
}
function ownerSearchInput(dialog) {
    return dialogDescendants(dialog).find(el => isVisible(el) && el.matches('input')
        && /buscar|search/.test(normalize(el.getAttribute('placeholder') || ''))) || null;
}
"""
)

# Lectura estricta del valor persistido de Otra información: solo los
# elementos de salida del campo (formatted-text / static / inputs) — excluye
# las hojas sueltas del contenedor donde vive la etiqueta accesible del
# lápiz ("Modificar Otra información"). Así se distingue el valor real
# guardado del ruido del DOM.
OTHER_INFO_VALUE_SCRIPT = (
    CLOSURE_HELPERS_SCRIPT
    + r"""
const labels = arguments[0];
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
for (const element of elements) {
    if (!isVisible(element) || !labels.includes(normalize(element.textContent))) {
        continue;
    }
    for (const container of fieldContainers(element)) {
        const descendants = [];
        collect(container, new Set(), descendants);
        const preferred = descendants.filter(child => child.matches && child.matches(
            'lightning-formatted-text, lightning-base-formatted-text, '
            + '.slds-form-element__static, [data-output-element-id], '
            + 'textarea, input:not([type="hidden"])'
        ));
        for (const child of preferred) {
            const isFormControl = child.matches('textarea, input, select');
            const raw = isFormControl ? child.value : (child.innerText || child.textContent || '');
            const lines = String(raw).split(/\r?\n/).map(line => line.trim());
            const labelIndex = lines.findIndex(line => labels.includes(normalize(line)));
            const value = labelIndex >= 0
                ? lines.slice(labelIndex + 1).filter(Boolean).join('\n').trim()
                : raw.trim();
            if (value) {
                return { found: true, text: value };
            }
        }
        if (preferred.length) {
            return { found: true, text: '' };
        }
    }
}
return { found: false, text: '' };
"""
)

# ¿Está abierto el diálogo "Cambiar propietario"?
OWNER_DIALOG_OPEN_SCRIPT = _OWNER_DIALOG_HELPERS + "return ownerDialog() ? 'open' : 'closed';"

# Abre el menú de overflow de la barra de acciones (donde puede vivir la acción).
OPEN_OVERFLOW_MENU_SCRIPT = (
    CLOSURE_HELPERS_SCRIPT
    + r"""
const labels = arguments[0];
const candidates = elements.filter(el => isVisible(el) && el.matches(
    'button, lightning-button-menu, lightning-button-icon')
    && labels.includes(normalize(
        el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent)));
if (candidates.length !== 1) return candidates.length ? 'ambiguous' : 'not_found';
candidates[0].click();
return 'clicked';
"""
)

# En el diálogo, clic en el conmutador de tipo de propietario (el botón que
# precede al input "Buscar …" dentro del mismo combobox agrupado).
OPEN_OWNER_SCOPE_SCRIPT = (
    _OWNER_DIALOG_HELPERS
    + r"""
const dialog = ownerDialog();
if (!dialog) return 'no_dialog';
const input = ownerSearchInput(dialog);
if (!input) return 'no_input';
for (const scope of ancestors(input, 8)) {
    const descendants = [];
    collect(scope, new Set(), descendants);
    const trigger = descendants.find(el => isVisible(el) && el !== input && el.matches(
        'button, [role="button"], [role="combobox"]'));
    if (trigger) {
        trigger.click();
        return 'clicked';
    }
}
return 'not_found';
"""
)

# Con el conmutador abierto, elige "Colas" entre las opciones visibles.
PICK_QUEUE_SCOPE_SCRIPT = (
    _OWNER_DIALOG_HELPERS
    + r"""
const wanted = arguments[0];
const options = elements.filter(el => isVisible(el) && el.matches(
    '[role="option"], lightning-base-combobox-item, [class*="slds-listbox__option"], li, a')
    && wanted.includes(normalize(el.textContent)));
if (!options.length) return 'not_found';
options[0].scrollIntoView({block: 'nearest', inline: 'nearest'});
options[0].click();
return 'clicked';
"""
)

# Devuelve el input de búsqueda del diálogo (para send_keys desde Python).
OWNER_SEARCH_INPUT_SCRIPT = (
    _OWNER_DIALOG_HELPERS
    + r"""
const dialog = ownerDialog();
return dialog ? ownerSearchInput(dialog) : null;
"""
)

# Con los resultados de búsqueda visibles, elige la opción cuyo texto contiene
# el nombre pedido. Las opciones "Buscar 'X'" / "Mostrar todos los resultados"
# también contienen el texto: abren la vista expandida del lookup y no
# seleccionan nada — se filtran. Si la vista expandida ya está abierta, se
# clica la fila del resultado.
PICK_QUEUE_RESULT_SCRIPT = (
    _OWNER_DIALOG_HELPERS
    + r"""
const wanted = normalize(arguments[0]);
const isAction = el => /buscar|mostrar|ver todos|show all|search/i.test(
    normalize(el.textContent).slice(0, 40));
const options = elements.filter(el => isVisible(el) && el.matches(
    '[role="option"], lightning-base-combobox-item, [class*="slds-listbox__option"], li')
    && normalize(el.textContent).includes(wanted));
const records = options.filter(el => !isAction(el));
const pick = records[0] || null;
if (pick) {
    pick.scrollIntoView({block: 'nearest', inline: 'nearest'});
    pick.click();
    return 'clicked';
}
// Vista expandida "Resultados": la fila del registro.
const rows = elements.filter(el => isVisible(el) && el.matches(
    'tr, [role="row"], records-record-picker-row')
    && normalize(el.textContent).includes(wanted));
if (!rows.length) return 'not_found';
const row = rows[rows.length - 1];
(row.querySelector('button, [role="button"], input[type="radio"]') || row).click();
return 'clicked';
"""
)


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def owner_is_unassigned(value: str, unassigned_owner: str) -> bool:
    return _compact(value) == _compact(unassigned_owner)


def status_is_expected(value: str, expected_status: str) -> bool:
    return normalized_value(value).casefold() == normalized_value(expected_status).casefold()


# --- Costuras de Selenium (los tests las sustituyen con unittest.mock) --------


def open_report(driver, bandeja: dict, timeout_seconds: int) -> None:
    driver.get(bandeja["url"])
    wait_for_lightning_ready(driver, timeout_seconds)


def report_session_lost(driver, timeout_seconds: int = 5) -> bool:
    """La sesión se cayó si la URL final no es Lightning autenticado."""
    return not is_authenticated(driver, timeout_seconds)


def read_bandeja_leads(
    driver,
    bandeja: dict,
    timeout_seconds: int,
    record_object_api_name: str,
    field_aliases: dict[str, list[str]],
    diagnostics: list | None = None,
):
    return read_visible_unassigned_leads(
        driver,
        timeout_seconds,
        record_object_api_name,
        field_aliases,
        diagnostics,
        unassigned_owner=bandeja["unassigned_owner"],
    )


def open_record(driver, config: dict, lead_id: str, timeout_seconds: int) -> None:
    driver.get(
        build_record_url(
            config["salesforce_url"],
            lead_id,
            config.get("record_object_api_name", "Lead"),
        )
    )
    wait_for_lightning_ready(driver, timeout_seconds)


_PREVIEW_TRAILER = re.compile(r"\s*(vista previa|preview)\s*$", re.IGNORECASE)


def _clean_owner_text(text: str) -> str:
    """El lookup de Propietario arrastra el enlace "Vista previa"; lo quita del
    nombre mostrado y de las comparaciones de propietario."""
    lines = [line for line in str(text or "").splitlines() if line.strip()]
    while lines and normalize_label(lines[-1]) in ("vista previa", "preview"):
        lines.pop()
    return _PREVIEW_TRAILER.sub("", "\n".join(lines)).rstrip()


def read_record_owner(driver) -> str:
    return _clean_owner_text(find_field_text(driver, OWNER_FIELD_LABELS))


def wait_record_owner(driver, timeout_seconds: int = OWNER_FIELD_TIMEOUT_SECONDS) -> str:
    deadline = time.monotonic() + timeout_seconds
    owner = ""
    while time.monotonic() < deadline:
        owner = read_record_owner(driver)
        if owner:
            return owner
        time.sleep(POLL_SECONDS)
    return owner


def press_pick_up(driver) -> str:
    """Clic en Pick Up; devuelve 'clicked' | 'not_found' | 'ambiguous'."""
    return execute_in_any_frame(driver, RECORD_ACTION_SCRIPT, list(PICK_UP_LABELS))


def wait_owner_changed(driver, unassigned_owner: str, timeout_seconds: int) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        owner = read_record_owner(driver)
        if owner and not owner_is_unassigned(owner, unassigned_owner):
            return True
        time.sleep(POLL_SECONDS)
    return False


def _reread_owner_after_refresh(driver, timeout_seconds: int) -> str:
    """Relee el propietario tras refrescar la ficha. El guardado del Pick
    Up puede tardar más que la ventana de verificación y dejar el campo
    viejo en el DOM — una sola recarga distingue un clic fallido de un
    guardado tardío."""
    try:
        driver.refresh()
        wait_for_lightning_ready(driver, timeout_seconds)
    except WebDriverException:
        pass
    return wait_record_owner(driver)


_EDIT_BUTTON_LABEL_VERBS = ("modificar", "editar", "edit")


def _strip_edit_button_label(text: str, labels: tuple[str, ...]) -> str:
    """Quita la etiqueta del lápiz ("Modificar Otra información") allá donde
    la lectura la arrastre: línea propia, pegada a un glifo de ícono o con
    sufijo accesible, y partida en dos líneas ("Modificar" + label).

    Antes solo se quitaba como primera línea exacta; en leads reales llegó
    con el ícono pegado y terminó persistida dentro del valor guardado.
    """
    label_set = {normalize_label(label) for label in labels}
    edit_labels = {f"{verb} {label}" for verb in _EDIT_BUTTON_LABEL_VERBS for label in label_set}
    kept = []
    lines = str(text or "").splitlines()
    index = 0
    while index < len(lines):
        normalized = normalize_label(lines[index]).rstrip(" .:")
        if any(label in normalized for label in edit_labels):
            index += 1
            continue
        if (
            normalized in _EDIT_BUTTON_LABEL_VERBS
            and index + 1 < len(lines)
            and normalize_label(lines[index + 1]) in label_set
        ):
            index += 2
            continue
        kept.append(lines[index])
        index += 1
    return "\n".join(kept).strip()


def _read_other_information(driver) -> str | None:
    """Lee ``Otra información`` esperando a que la ficha lo renderice.

    ``None`` = el campo no apareció (sección aún sin renderizar o ausente del
    layout); ``""`` = renderizado y vacío. ``find_field_text`` no distingue
    esos casos — y sobre "" se habría pisado el contenido real al escribir.
    """
    deadline = time.monotonic() + FIELD_RENDER_WAIT_SECONDS
    while True:
        result = field_result_if_found(driver, OTHER_INFORMATION_LABELS)
        if result:
            return _strip_edit_button_label(
                text_without_field_label(result["text"], OTHER_INFORMATION_LABELS),
                OTHER_INFORMATION_LABELS,
            )
        if time.monotonic() >= deadline:
            return None
        if not scroll_toward_other_information(driver, OTHER_INFORMATION_LABELS):
            time.sleep(POLL_SECONDS)


def _other_information_has_mark(text: str) -> bool:
    return normalized_value(BOT_TAKE_MARK).casefold() in normalized_value(text).casefold()


def _lead_documented(text: str) -> bool:
    """El campo ya registra la gestión: la marca ``Asignado`` o una línea de
    intento documentada (``N INT ...``) por humano o bot. Si existe, nunca
    se duplica ni se pisa — el lead ya fue gestionado."""
    return _other_information_has_mark(text) or bool(_INTENT_LINE_RE.search(text or ""))


def _strip_take_mark_lines(text: str) -> str:
    """Quita líneas cuyo contenido completo es ``Asignado``.

    Rama WhatsApp: el campo debe quedar solo con la línea de intento. El
    guardado del panel "Contact Client" (o la asignación misma) puede agregar
    ``Asignado`` al campo — para esos leads es contaminación, no marca.
    """
    lines = [line for line in str(text or "").splitlines() if normalize_label(line) != "asignado"]
    return "\n".join(lines).strip()


def _whatsapp_attempt_line(tz_offset: int = 0) -> str:
    """Documentación del primer contacto con el formato de los auxiliares.

    ``tz_offset`` es la diferencia horaria del país del lead respecto a la
    hora local donde corre el bot (Colombia): para AR (+2) las 9:00
    locales se documentan como 11:00.
    """
    moment = datetime.now() + timedelta(hours=tz_offset)
    return f"1 INT Se envía WhatsApp {moment:%d/%m/%Y %H:%M}"


def _wants_whatsapp_send(bandeja: dict, details: dict | None, enabled: bool) -> bool:
    """La rama de envío aplica solo a AR + toggle + preferencia whatsapp."""
    if not enabled or bandeja.get("code") != "AR":
        return False
    preference = normalize_label((details or {}).get("preferencia_contacto") or "")
    return "whatsapp" in preference


def _read_other_information_value(driver) -> str | None:
    """Lectura estricta del valor persistido — solo los elementos de salida
    del campo, sin la etiqueta accesible del lápiz ni hojas sueltas del
    contenedor. Es la verdad de lo que quedó guardado; ``None`` cuando el
    campo no se renderiza con elemento de salida propio."""
    result = execute_in_any_frame(driver, OTHER_INFO_VALUE_SCRIPT, list(OTHER_INFORMATION_LABELS))
    if isinstance(result, dict) and result.get("found"):
        return text_without_field_label(result["text"], OTHER_INFORMATION_LABELS)
    return None


def _ensure_take_mark(
    driver,
    timeout_seconds: int,
    mark_text: str = BOT_TAKE_MARK,
    drop_take_mark: bool = False,
) -> str:
    """Garantiza ``mark_text`` en ``Otra información`` — y saneado.

    ``mark_text`` es ``Asignado`` por defecto o la línea de intento
    ``1 INT Se envía WhatsApp ...`` cuando el lead pidió ese canal: en ambos
    casos es la evidencia de la toma/gestión. El Save del panel "Contact
    Client" recarga la ficha: una escritura bien hecha puede perderse en
    ese repintado, así que se relee y reintenta una vez. La lectura
    estricta verifica lo *persistido*: si el valor guardado trae la
    etiqueta del lápiz ("Modificar Otra información"), se reescribe limpio
    aunque la evidencia ya esté — repara valores contaminados de tomas
    anteriores.

    ``drop_take_mark`` (rama WhatsApp): además trata cualquier línea
    ``Asignado`` solitaria como contaminación — el estatuto del panel
    "Contact Client" puede inyectarla — y la elimina del valor persistido;
    el campo queda solo con la línea de intento.
    """
    wrote = False
    for _ in range(2):
        current = _read_other_information(driver)
        if current is None:
            # Sin campo visible no se escribe a ciegas: con "" la escritura
            # pisaría el contenido que la lectura ciega no vio.
            return "marca_no_confirmada" if wrote else "campo_ausente"
        persisted = _read_other_information_value(driver)
        basis = persisted if persisted is not None else current
        clean = _strip_edit_button_label(basis, OTHER_INFORMATION_LABELS)
        if drop_take_mark:
            clean = _strip_take_mark_lines(clean)
        documented = _lead_documented(clean)
        polluted = persisted is not None and clean != persisted.strip()
        if documented and not polluted:
            return "marca_ok" if wrote else "marca_presente"
        value = clean if documented else f"{clean.rstrip()}\n{mark_text}".strip()
        try:
            prepare_other_information(driver, value, timeout_seconds)
        except (TimeoutException, WebDriverException, ValueError) as error:
            return f"marca_error:editar:{type(error).__name__}"
        try:
            save_edit_form(driver, timeout_seconds)
        except (TimeoutException, WebDriverException, ValueError) as error:
            return f"marca_error:guardar:{type(error).__name__}"
        wrote = True
    persisted = _read_other_information_value(driver)
    if persisted is not None:
        clean = _strip_edit_button_label(persisted, OTHER_INFORMATION_LABELS)
        if drop_take_mark:
            clean = _strip_take_mark_lines(clean)
        if _lead_documented(clean) and clean == persisted.strip():
            return "marca_ok"
        return "marca_no_confirmada"
    final = _read_other_information(driver)
    if final is not None and _lead_documented(final):
        return "marca_ok"
    return "campo_ausente" if final is None else "marca_no_confirmada"


# --- Reasignación por turno -------------------------------------------------

# Texto del comentario para leads que se pasan a otra persona: la marca
# ``Asignado`` queda, seguida del método de contacto que pidió el lead en
# ``preferencia_contacto`` (así la encargada sabe qué hacer al gestionarlo).
# El intento WhatsApp automático NO aplica a estos leads (el envío saldría
# de la sesión del bot, no de la encargada).
def _reasignacion_mark(details: dict | None) -> str:
    preference = normalize_label((details or {}).get("preferencia_contacto") or "")
    if "whatsapp" in preference:
        metodo = "Enviar Whatsapp"
    elif "llamad" in preference or "telefon" in preference:
        metodo = "Llamarlo"
    else:
        metodo = "Gestionarlo"
    return f"Asignado - {metodo}"


def _encargada_activa(
    equipo: list[dict] | None,
    moment: datetime | None = None,
    bandeja: str | set[str] | None = None,
) -> dict | None:
    """Primera persona cuya franja cubre la hora actual — y la ``bandeja``
    cuando se pide. Una franja sin ``bandejas`` no cubre nada; varias
    bandejas (str o set) significan "cualquiera de estas".
    """
    if not equipo:
        return None
    wanted = None
    if bandeja is not None:
        wanted = {bandeja} if isinstance(bandeja, str) else set(bandeja)
    now = moment or datetime.now().astimezone()
    minutes = now.hour * 60 + now.minute
    for member in equipo:
        for slot in member.get("franjas") or []:
            if wanted is not None and not (set(slot.get("bandejas") or []) & wanted):
                continue
            try:
                start = int(str(slot["start"])[:2]) * 60 + int(str(slot["start"])[3:5])
                end = int(str(slot["end"])[:2]) * 60 + int(str(slot["end"])[3:5])
            except (KeyError, ValueError, IndexError):
                continue
            if start <= minutes <= end:
                return member
    return None


def _lead_entry_moment(details: dict | None) -> datetime | None:
    """Hora de ingreso del lead a la cola (Fecha de creación del reporte,
    formato ``dd/mm/aaaa hh:MM AM/PM``). None si falta o no parsea."""
    raw = ((details or {}).get("fecha_creacion") or "").strip()
    try:
        return datetime.strptime(raw, "%d/%m/%Y %I:%M %p")
    except ValueError:
        return None


def _usable_entry_moment(details: dict | None, now: datetime | None = None) -> datetime | None:
    """Hora de ingreso del lead a la cola, solo si es de HOY: una fecha de
    creación de un día anterior no dice quién cubre la bandeja ahora."""
    entry = _lead_entry_moment(details)
    if entry is None or entry.date() != (now or datetime.now()).date():
        return None
    return entry


def _equipo_para_lead(
    state: dict,
    bandeja_code: str,
    details: dict | None,
    now: datetime | None = None,
) -> list[dict] | None:
    """Equipo a pasar a ``take_lead`` para el lead, o None si queda con el
    usuario logueado.

    A la hora de INGRESO del lead (solo si es de hoy): si la franja
    propia cubría esa hora, el lead es propio; si la cubría alguien del
    equipo, va el equipo. Sin dato usable —o si nadie cubría el
    ingreso—, la regla de siempre: franja propia vigente ahora.
    """
    entry = _usable_entry_moment(details, now)
    if entry is not None:
        if state.get("schedule") and within_schedule(
            state["schedule"], moment=entry, bandeja=bandeja_code
        ):
            return None
        if _encargada_activa(state.get("equipo"), moment=entry, bandeja=bandeja_code):
            return state.get("equipo")
    if state.get("schedule") and within_schedule(
        state["schedule"], moment=now, bandeja=bandeja_code
    ):
        return None
    return state.get("equipo")


def _encargada_para_lead(
    equipo: list[dict] | None,
    owner: str,
    bandeja: str | None = None,
    details: dict | None = None,
    now: datetime | None = None,
) -> dict | None:
    """Encargada del lead si la franja activa NO es del usuario logueado.

    ``owner`` es el propietario post-pickup (siempre el usuario de la
    sesión): si coincide con el nombre de la encargada, la franja es del
    propio usuario y el flujo sigue normal. La ``bandeja`` restringe a la
    persona que cubre ESA bandeja en su franja activa. La franja se
    evalúa a la hora de INGRESO del lead a la cola (Fecha de creación,
    solo si es de hoy): el bot puede tardar minutos en tomarlo y caer en
    el turno siguiente; si el ingreso no da miembro —o no es usable—,
    cae a la hora actual como antes.
    """
    entry = _usable_entry_moment(details, now)
    member = _encargada_activa(equipo, moment=entry, bandeja=bandeja)
    member = member or _encargada_activa(equipo, moment=now, bandeja=bandeja)
    if not member:
        return None
    nombre = normalized_key(member.get("nombre") or "")
    actual = normalized_key(owner or "")
    if nombre and actual and (nombre in actual or actual in nombre):
        return None
    return member


def _dismiss_owner_dialog(driver) -> None:
    """Cancela el modal Cambiar propietario si quedó abierto tras un fallo."""
    try:
        execute_in_any_frame(driver, MODAL_CONFIRM_SCRIPT, ["cancelar", "cancel", "cerrar", "close"])
    except WebDriverException:
        pass


def _wait_owner_search_input(driver, timeout_seconds: float):
    """Espera el input "Buscar …" del modal: el contenedor abre antes que
    el lookup interno, y aún con el input presente el combobox necesita un
    settle para registrar la búsqueda."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        search_input = execute_in_any_frame(driver, OWNER_SEARCH_INPUT_SCRIPT)
        if search_input is not None:
            time.sleep(OWNER_LOOKUP_SETTLE_SECONDS)
            return search_input
        time.sleep(POLL_SECONDS)
    return None


OWNER_LOOKUP_DUMP_SCRIPT = _OWNER_DIALOG_HELPERS + r"""
const dialog = ownerDialog();
const input = ownerSearchInput(dialog);
const seen = [];
if (dialog) {
    for (const el of dialogDescendants(dialog)) {
        if (!isVisible(el)) continue;
        if (el.matches('[role="option"], lightning-base-combobox-item, [class*="slds-listbox__option"], li')
                || el.matches('tr, [role="row"], records-record-picker-row')) {
            const txt = normalize(el.textContent).slice(0, 60);
            if (txt && !seen.includes(txt)) seen.push(txt);
            if (seen.length >= 8) break;
        }
    }
}
return { inputValue: input ? input.value : null, options: seen };
"""


def _owner_lookup_snapshot(driver) -> dict:
    """Vuelca qué muestra el lookup del modal (texto tipeado + opciones
    visibles). Solo diagnóstico: se usa cuando la opción no apareció."""
    try:
        snapshot = execute_in_any_frame(driver, OWNER_LOOKUP_DUMP_SCRIPT)
    except WebDriverException:
        return {}
    return snapshot if isinstance(snapshot, dict) else {}


def _pick_owner_option(
    driver, search_input, wanted: str, timeout_seconds: float, diagnostics=None
) -> bool:
    """Tipea ``wanted`` en el lookup y elige la opción. Si el primer tipeo
    cayó antes de que el combobox quedara listo (texto escrito pero sin
    resultados), reescribe una vez más — reintenta el tipeo, nunca el clic
    de confirmar. El click previo le da foco al combobox: sin foco, los
    send_keys pueden caer en la nada. Con ``diagnostics`` (dict) vuelca lo
    que el desplegable mostraba al agotar los intentos."""
    deadline = time.monotonic() + timeout_seconds
    for attempt in range(2):
        try:
            search_input.click()
        except WebDriverException:
            pass
        search_input.clear()
        search_input.send_keys(wanted)
        attempt_deadline = time.monotonic() + (deadline - time.monotonic()) / (2 - attempt)
        while time.monotonic() < attempt_deadline:
            if execute_in_any_frame(driver, PICK_QUEUE_RESULT_SCRIPT, wanted) == "clicked":
                return True
            time.sleep(POLL_SECONDS)
    if diagnostics is not None:
        diagnostics.update(_owner_lookup_snapshot(driver))
    return False


def _confirm_owner_dialog(driver, timeout_seconds: float) -> bool:
    """Espera el botón "Cambiar propietario" tras elegir el registro: al
    seleccionar una opción (o una fila de la vista expandida) el modal
    re-renderiza el footer y el botón tarda un instante en volver."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if execute_in_any_frame(
            driver, MODAL_CONFIRM_SCRIPT, list(CHANGE_OWNER_CONFIRM_LABELS)
        ) == "clicked":
            return True
        time.sleep(POLL_SECONDS)
    return False


def _owner_matches(owner: str, nombre: str) -> bool:
    """True si el propietario releído corresponde a ``nombre``."""
    actual = normalized_key(owner or "")
    wanted = normalized_key(nombre)
    return bool(actual and wanted and (wanted in actual or actual in wanted))


def _reassign_attempt(driver, nombre: str, timeout_seconds: int) -> str:
    """Un intento completo de reasignación: modal → búsqueda → opción →
    confirmar → verificación por relectura del propietario."""
    if not open_change_owner_dialog(driver, timeout_seconds):
        return "reasignacion_error:modal"
    search_input = _wait_owner_search_input(driver, timeout_seconds)
    if search_input is None:
        _dismiss_owner_dialog(driver)
        return "reasignacion_error:busqueda"
    if not _pick_owner_option(driver, search_input, nombre, QUEUE_SEARCH_TIMEOUT_SECONDS):
        _dismiss_owner_dialog(driver)
        return "reasignacion_error:opcion"
    if not _confirm_owner_dialog(driver, QUEUE_SEARCH_TIMEOUT_SECONDS):
        _dismiss_owner_dialog(driver)
        return "reasignacion_error:confirmar"
    deadline = time.monotonic() + OWNER_VERIFY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        owner = read_record_owner(driver)
        if _owner_matches(owner, nombre):
            return "reasignado"
        time.sleep(POLL_SECONDS)
    return "reasignacion_error:verificacion"


def reassign_owner(driver, nombre: str, timeout_seconds: int) -> str:
    """Reasigna el lead a ``nombre`` vía el diálogo "Cambiar propietario".

    Flujo aprobado: (1) intento de reasignación; si no quedó ``reasignado``
    se relee el propietario tras un refresh — el modal pudo confirmar y la
    verificación fallar por timing del re-render—; si el nombre coincide se
    da por buena, y solo si el lead siguió sin cambiar de dueño se corre
    (2) un segundo intento completo. Reutiliza la maquinaria de devolución
    a cola (mismo modal): el scope por defecto ya es Usuarios, no hace
    falta conmutar a Colas. Devuelve ``reasignado`` solo si la relectura
    del propietario coincide; ante cualquier fallo el lead queda con el
    usuario del bot y el paso que falló queda en el outcome
    (``reasignacion_error:<paso>``).
    """
    outcome = _reassign_attempt(driver, nombre, timeout_seconds)
    if outcome == "reasignado":
        return outcome
    # Verificar a nombre de quién quedó antes de reintentar.
    owner = _reread_owner_after_refresh(driver, timeout_seconds)
    if _owner_matches(owner, nombre):
        return "reasignado"
    return _reassign_attempt(driver, nombre, timeout_seconds)


def verify_persona_option(driver, nombre: str, timeout_seconds: int, diagnostics=None) -> str:
    """Simula la reasignación a ``nombre`` y SIEMPRE cancela el modal.

    Recorre el mismo camino que ``_reassign_attempt`` —abrir el diálogo
    "Cambiar propietario", esperar el lookup y tipear el nombre— pero se
    detiene en la opción encontrada: NUNCA pulsa el botón de confirmar y
    cierra el modal con Cancelar en todas las salidas una vez abierto.
    Devuelve ``opcion_ok`` si el nombre aparece en el lookup, o
    ``reasignacion_error:modal|busqueda|opcion`` según el paso que falló.
    """
    if not open_change_owner_dialog(driver, timeout_seconds):
        return "reasignacion_error:modal"
    search_input = _wait_owner_search_input(driver, timeout_seconds)
    if search_input is None:
        _dismiss_owner_dialog(driver)
        return "reasignacion_error:busqueda"
    if not _pick_owner_option(driver, search_input, nombre, QUEUE_SEARCH_TIMEOUT_SECONDS, diagnostics):
        _dismiss_owner_dialog(driver)
        return "reasignacion_error:opcion"
    _dismiss_owner_dialog(driver)
    return "opcion_ok"


def send_whatsapp(driver) -> str:
    """Pulsa ``Send To Whatsapp`` y confirma el envío por el toast verde.

    Si el toast no aparece se reporta ``wa_no_confirmado`` y NUNCA se
    reintenta el clic: un segundo clic podría mandar el mensaje dos veces.
    """
    try:
        if execute_in_any_frame(driver, SEND_WHATSAPP_CLICK_SCRIPT) != "clicked":
            return "wa_sin_boton"
        deadline = time.monotonic() + WA_TOAST_WAIT_SECONDS
        while time.monotonic() < deadline:
            if execute_in_any_frame(driver, WA_TOAST_PRESENT_SCRIPT) == "found":
                try:
                    execute_in_any_frame(driver, WA_TOAST_CLOSE_SCRIPT)
                except WebDriverException:
                    pass  # el toast igual caduca solo; el envío ya está
                return "wa_ok"
            time.sleep(POLL_SECONDS)
        return "wa_no_confirmado"
    except WebDriverException as error:
        return f"wa_error:{type(error).__name__}"


def _save_panel_in_other_handles(driver) -> str | None:
    """Busca el panel en las demás pestañas/ventanas del navegador y lo guarda.

    ``execute_in_any_frame`` solo ve la pestaña activa; en Service Console el
    panel puede renderizar en otro handle (subtab de consola, ventana de
    utilidad). Devuelve el outcome o ``None`` si no estaba en ninguna.
    """
    try:
        current = driver.current_window_handle
        handles = [h for h in driver.window_handles if h != current]
    except (WebDriverException, AttributeError):
        return None
    for handle in handles:
        try:
            driver.switch_to.window(handle)
            if execute_in_any_frame(driver, PANEL_PRESENT_SCRIPT) != "found":
                continue
            clicked = execute_in_any_frame(driver, PANEL_SAVE_CLICK_SCRIPT)
            return "panel_otra_tab_guardado" if clicked == "clicked" else "panel_otra_tab_sin_save"
        except WebDriverException:
            continue
        finally:
            try:
                if driver.current_window_handle != current:
                    driver.switch_to.window(current)
            except (WebDriverException, AttributeError):
                pass
    return None


def _save_contact_panel_initial(driver, timeout_seconds: int) -> str:
    """Ventana inicial del panel "Contact Client": espera y pulsa su Save."""
    outcome = "sin_panel"
    try:
        deadline = time.monotonic() + PANEL_WAIT_SECONDS
        while time.monotonic() < deadline:
            if execute_in_any_frame(driver, PANEL_PRESENT_SCRIPT) == "found":
                outcome = "panel_sin_save"
                break
            time.sleep(POLL_SECONDS)
        if outcome == "panel_sin_save":
            if execute_in_any_frame(driver, PANEL_SAVE_CLICK_SCRIPT) == "clicked":
                outcome = "panel_guardado"
                time.sleep(SAVE_SETTLE_SECONDS)
                # El Save del panel recarga la ficha: sin este settle el
                # campo se lee/edita contra un DOM en plena reconstrucción.
                wait_for_lightning_ready(driver, timeout_seconds)
    except WebDriverException:
        outcome = "panel_error"
    return outcome


def _save_contact_panel_late(driver) -> str:
    """Chequeo tardío del panel + barrido por otros handles (subtabs de la
    consola): el barrido de frames solo cubre la pestaña activa."""
    outcome = "sin_panel"
    try:
        deadline = time.monotonic() + LATE_PANEL_WAIT_SECONDS
        while time.monotonic() < deadline:
            if execute_in_any_frame(driver, PANEL_PRESENT_SCRIPT) == "found":
                outcome = "panel_tardio_sin_save"
                if execute_in_any_frame(driver, PANEL_SAVE_CLICK_SCRIPT) == "clicked":
                    outcome = "panel_tardio_guardado"
                break
            time.sleep(POLL_SECONDS)
    except WebDriverException:
        pass
    if outcome == "sin_panel":
        cross = _save_panel_in_other_handles(driver)
        if cross:
            outcome = cross
    return outcome


def save_contact_panel_if_present(driver, timeout_seconds: int) -> str:
    """Espera el panel "Contact Client" post-Pick-Up y pulsa solo su Save.

    Cubre la ventana inicial, el chequeo tardío y los otros handles. No
    escribe nada en el registro — sirve para la toma del monitor y para la
    distribución por lote, que no documenta comentarios. Devuelve el
    outcome ``panel_*``/``sin_panel``/``panel_error``.
    """
    outcome = _save_contact_panel_initial(driver, timeout_seconds)
    if outcome == "sin_panel":
        outcome = _save_contact_panel_late(driver)
    return outcome


def finalize_pick_up(
    driver,
    timeout_seconds: int,
    diag_dir: Path | None = None,
    diag_label: str = "",
    whatsapp: bool = False,
    encargada: dict | None = None,
    details: dict | None = None,
    tz_offset: int = 0,
) -> tuple[str, str]:
    """Guarda el panel "Contact Client" que aparece tras el Pick Up.

    Solo pulsa su ``Save`` (la toma no queda firme en Salesforce hasta ese
    guardado) — no escribe nada en la sección. La marca ``Asignado`` se
    deja únicamente en ``Otra información`` para saber que lo tomó el bot.

    Best-effort: la asignación ya quedó verificada por el cambio de
    propietario — un panel ausente o un guardado fallido no degradan el
    ``tomado``. Devuelve ``(outcome, diagnostico)``: ``<panel>/<marca>``
    (p. ej. ``panel_guardado/marca_ok``; ``panel_tardio_*`` cuando el panel
    apareció pasada la ventana inicial; ``panel_otra_tab_*`` cuando estaba
    en otro handle) y, si nunca se detectó, los encabezados de diálogos
    visibles, la cadena DOM de los botones Save/SendEmail y el nombre del
    screenshot volcado en ``diag_dir`` para ajustar la detección.
    """
    outcome = _save_contact_panel_initial(driver, timeout_seconds)
    diagnostic = ""
    # La evidencia de la toma tiene que quedar en "Otra información" aunque
    # el panel no exista: `Asignado` o, en la rama WhatsApp, la línea de
    # intento `1 INT Se envía WhatsApp ...` — va ANTES del envío, como hacen
    # los auxiliares.
    # Lead reasignado: la encargada hace el contacto — el WhatsApp
    # automático queda apagado siempre. El comentario de asignación
    # (``_reasignacion_mark``) queda pendiente de definición: por ahora no
    # se escribe nada en Otra información.
    if encargada:
        whatsapp = False
        mark_text = None
    else:
        mark_text = _whatsapp_attempt_line(tz_offset) if whatsapp else BOT_TAKE_MARK
    if mark_text is None:
        mark = "sin_comentario"
    else:
        try:
            mark = _ensure_take_mark(driver, timeout_seconds, mark_text, drop_take_mark=whatsapp)
        except (TimeoutException, WebDriverException, ValueError) as error:
            mark = f"marca_error:{type(error).__name__}"
    # Chequeo tardío: el panel puede aparecer pasada la ventana inicial.
    if outcome == "sin_panel":
        outcome = _save_contact_panel_late(driver)
    if outcome == "sin_panel":
        try:
            findings = execute_in_any_frame(driver, PANEL_DIAGNOSTIC_SCRIPT)
            if isinstance(findings, list) and findings:
                diagnostic = "; ".join(str(item) for item in findings)
        except WebDriverException:
            pass
        if diag_dir is not None:
            # Screenshot de lo que el bot ve en el momento del fallo: la
            # forma decisiva de ubicar el panel si el DOM no lo delata.
            try:
                diag_dir.mkdir(parents=True, exist_ok=True)
                shot = diag_dir / f"sin_panel_{diag_label or 'lead'}_{int(time.time())}.png"
                driver.save_screenshot(str(shot))
                diagnostic = f"{diagnostic} | shot:{shot.name}" if diagnostic else f"shot:{shot.name}"
            except (OSError, WebDriverException):
                pass
    # El envío va último: documentado primero (aunque falle el envío queda
    # el intento registrado) y el clic jamás se reintenta si el toast no
    # confirma — un segundo clic podría duplicar el mensaje.
    if whatsapp:
        wa = send_whatsapp(driver)
        # El Save del panel "Contact Client" (estatuto de la llamada) o un
        # flow de Salesforce pueden escribir "Asignado" en Otra información
        # de forma asíncrona — pasada final para dejar solo la línea de
        # intento. Best-effort: el outcome real ya quedó registrado.
        try:
            _ensure_take_mark(driver, timeout_seconds, mark_text, drop_take_mark=True)
        except (TimeoutException, WebDriverException, ValueError):
            pass
        return f"{outcome}/{mark}/{wa}", diagnostic
    if encargada:
        # Reasignar va último: si el modal falla el lead queda con el
        # usuario del bot y el paso fallido queda explícito en el outcome.
        return f"{outcome}/{mark}/{reassign_owner(driver, encargada['nombre'], timeout_seconds)}", diagnostic
    return f"{outcome}/{mark}", diagnostic


# --- Lógica del ciclo ---------------------------------------------------------


def take_lead(
    driver,
    config: dict,
    bandeja: dict,
    lead_id: str,
    timeout_seconds: int,
    diag_dir: Path | None = None,
    details: dict | None = None,
    enviar_whatsapp: bool = False,
    equipo: list[dict] | None = None,
    bot_owner: str | None = None,
) -> tuple[str, str, str]:
    """Abre el registro, re-verifica el propietario y pulsa Pick Up.

    ``tomado`` exige observar el cambio de propietario; si la verificación no
    confirma, queda ``no_verificado`` y nunca se repite el clic a ciegas.
    Devuelve ``(status, propietario_observado, finalización, diagnóstico)`` —
    el nombre de la persona a la que quedó asignado y el resultado de
    ``finalize_pick_up`` (panel + marca ``Asignado``, más los paneles
    visibles si no se detectó el esperado), para la verificación en la
    tabla del monitor.
    """
    open_record(driver, config, lead_id, timeout_seconds)
    owner = wait_record_owner(driver)
    if not owner:
        return STATUS_ERROR, "", "", ""
    if not owner_is_unassigned(owner, bandeja["unassigned_owner"]):
        return STATUS_TOMADO_POR_OTRO, owner, "", ""
    if press_pick_up(driver) != "clicked":
        return STATUS_ERROR, owner, "", ""
    if not wait_owner_changed(driver, bandeja["unassigned_owner"], OWNER_VERIFY_TIMEOUT_SECONDS):
        owner = _reread_owner_after_refresh(driver, timeout_seconds)
        if not owner or owner_is_unassigned(owner, bandeja["unassigned_owner"]):
            return STATUS_NO_VERIFICADO, owner, "", ""
        # El propietario cambió tras la ventana: si se conoce el usuario
        # de la sesión y no coincide, la carrera la ganó otra persona —
        # no tocar su lead.
        if bot_owner:
            got = normalized_key(owner)
            wanted = normalized_key(bot_owner)
            if got and wanted and not (wanted in got or got in wanted):
                return STATUS_TOMADO_POR_OTRO, owner, "", ""
    new_owner = read_record_owner(driver) or owner
    encargada = _encargada_para_lead(equipo, new_owner, bandeja=bandeja.get("code"), details=details)
    diagnostic = f"encargada: {encargada['nombre']}" if encargada else ""
    finalize, diag = finalize_pick_up(
        driver,
        timeout_seconds,
        diag_dir=diag_dir,
        diag_label=lead_id[-6:],
        whatsapp=_wants_whatsapp_send(bandeja, details, enviar_whatsapp) and not encargada,
        encargada=encargada,
        details=details,
        tz_offset=bandeja.get("tz_offset") or 0,
    )
    diagnostic = f"{diagnostic} | {diag}".strip(" |") if diag else diagnostic
    # Si la reasignación salió, el propietario real ya es la encargada.
    if encargada and finalize.endswith("/reasignado"):
        new_owner = encargada["nombre"]
    return STATUS_TOMADO, new_owner, finalize, diagnostic


def open_change_owner_dialog(driver, timeout_seconds: int) -> bool:
    """Clic en la acción Cambiar propietario y espera a que el diálogo abra.

    El registro suele venir de un re-render (Save del panel Contact
    Client): el botón puede tardar un momento en aparecer, así que el
    intento de clic —acción directa y, si no está, menú de overflow— se
    repite hasta el deadline. Tras cada clic se espera el diálogo por un
    máximo de ``OWNER_DIALOG_OPEN_WAIT_SECONDS`` (o lo que quede del
    deadline); si no abrió se cancela el modal por si quedó a medio abrir
    y se permite un segundo clic (máximo 2 por llamada).
    """
    deadline = time.monotonic() + timeout_seconds
    clicks = 0
    while time.monotonic() < deadline and clicks < 2:
        outcome = execute_in_any_frame(
            driver, RECORD_ACTION_SCRIPT, list(CHANGE_OWNER_ACTION_LABELS)
        )
        if outcome != "clicked":
            if execute_in_any_frame(
                driver, OPEN_OVERFLOW_MENU_SCRIPT, list(OVERFLOW_MENU_LABELS)
            ) == "clicked":
                time.sleep(POLL_SECONDS)
                outcome = execute_in_any_frame(
                    driver, RECORD_ACTION_SCRIPT, list(CHANGE_OWNER_ACTION_LABELS)
                )
        if outcome != "clicked":
            time.sleep(POLL_SECONDS)
            continue
        clicks += 1
        open_deadline = min(deadline, time.monotonic() + OWNER_DIALOG_OPEN_WAIT_SECONDS)
        while time.monotonic() < open_deadline:
            if execute_in_any_frame(driver, OWNER_DIALOG_OPEN_SCRIPT) == "open":
                return True
            time.sleep(POLL_SECONDS)
        _dismiss_owner_dialog(driver)
    return False


def pick_queue_in_owner_dialog(driver, queue_label: str, timeout_seconds: int) -> bool:
    """Dentro del diálogo: conmutador Usuarios→Colas, búsqueda y selección."""
    if execute_in_any_frame(driver, OPEN_OWNER_SCOPE_SCRIPT) != "clicked":
        return False
    time.sleep(POLL_SECONDS)
    if execute_in_any_frame(driver, PICK_QUEUE_SCOPE_SCRIPT, list(OWNER_SCOPE_QUEUE_LABELS)) != "clicked":
        return False
    search_input = _wait_owner_search_input(driver, timeout_seconds)
    if search_input is None:
        return False
    return _pick_owner_option(driver, search_input, queue_label, timeout_seconds)


def return_lead_to_queue(driver, config: dict, lead_id: str, queue_label: str, timeout_seconds: int) -> str:
    """Devuelve el Lead a la cola ``queue_label`` vía el diálogo Cambiar
    propietario. ``devuelto`` exige releer la cola como propietario."""
    open_record(driver, config, lead_id, timeout_seconds)
    owner = wait_record_owner(driver)
    if not owner:
        return STATUS_ERROR
    if owner_is_unassigned(owner, queue_label):
        return "ya_en_cola"
    if not open_change_owner_dialog(driver, timeout_seconds):
        return STATUS_ERROR
    if not pick_queue_in_owner_dialog(driver, queue_label, QUEUE_SEARCH_TIMEOUT_SECONDS):
        return STATUS_ERROR
    if not _confirm_owner_dialog(driver, QUEUE_SEARCH_TIMEOUT_SECONDS):
        return STATUS_ERROR
    deadline = time.monotonic() + OWNER_VERIFY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        owner = read_record_owner(driver)
        if owner and owner_is_unassigned(owner, queue_label):
            return "devuelto"
        time.sleep(POLL_SECONDS)
    return STATUS_NO_VERIFICADO


def run_bandeja_cycle(
    driver,
    config: dict,
    bandeja: dict,
    state: dict,
    timeout_seconds: int,
    diag_dir: Path | None = None,
) -> list[dict]:
    """Un ciclo sobre una bandeja: refresca, detecta y toma los leads visibles."""
    open_report(driver, bandeja, timeout_seconds)
    if report_session_lost(driver):
        return [{"type": "session_lost", "bandeja": bandeja["code"]}]
    diagnostics: list[dict] = []
    visible_rows, leads = read_bandeja_leads(
        driver,
        bandeja,
        timeout_seconds,
        config.get("record_object_api_name", "Lead"),
        config.get("lead_list_fields", {}),
        diagnostics,
    )
    events = []
    # Scan visible: sin esta línea un reporte leído con 0 coincidencias del
    # propietario "sin asignar" es indistinguible de un reporte vacío —
    # fue el caso de "abre la bandeja pero no toma ni lista nada".
    owners_seen = next(
        (d.get("owners_seen") for d in diagnostics if d.get("owners_seen")), []
    )
    events.append(
        {
            "type": "bandeja_scan",
            "bandeja": bandeja["code"],
            "rows": visible_rows,
            "unassigned": len(leads),
            "unassigned_owner": bandeja["unassigned_owner"],
            "owners_seen": owners_seen,
        }
    )
    skipped_status = 0
    solo_listar = bool(state.get("solo_listar"))
    enviar_whatsapp = bool(state.get("enviar_whatsapp"))
    # La franja del monitor (del usuario logueado) tiene prioridad sobre el
    # equipo, pero solo para las bandejas que cubre: una franja propia
    # vigente de AR no impide que el equipo reciba los leads de MX.
    # Franja propia sin bandejas tildadas = cubre todas, como siempre.
    equipo = state.get("equipo")
    propio_activo = bool(state.get("schedule")) and within_schedule(
        state["schedule"], bandeja=bandeja["code"]
    )
    # Cobertura por bandeja: sin franja propia que cubra ESTA bandeja, solo
    # la persona del equipo cuya franja activa la cubre habilita la toma.
    # Un lead MX con franja AR vigente queda detectado "sin cobertura" —
    # nunca se le reasigna a alguien de otra bandeja.
    covered = propio_activo or _encargada_activa(equipo, bandeja=bandeja["code"]) is not None
    for lead in leads:
        if not lead.lead_id or not should_process(state, lead.lead_id):
            continue
        if not status_is_expected(lead.details.get("estado_candidato", ""), bandeja["expected_status"]):
            # El filtro de estado acota la TOMA real; en modo prueba se listan
            # todos los QUALIF visibles para revisar la bandeja completa.
            if not solo_listar:
                skipped_status += 1
                continue
        assigned_to = ""
        finalize = ""
        diagnostic = ""
        motivo = ""
        if solo_listar:
            # Modo prueba: solo listar los QUALIF detectados; no abrir el
            # registro ni tocar Pick Up. El estado `detectado` es reprocesable.
            status = STATUS_DETECTADO
        elif not covered:
            # La bandeja no tiene turno vigente que la cubra: el lead se
            # lista como detectado "sin cobertura" para reasignarlo a mano.
            status = STATUS_DETECTADO
            motivo = "sin_cobertura"
        else:
            try:
                status, assigned_to, finalize, diagnostic = take_lead(
                    driver,
                    config,
                    bandeja,
                    lead.lead_id,
                    timeout_seconds,
                    diag_dir=diag_dir,
                    details=lead.details,
                    enviar_whatsapp=enviar_whatsapp,
                    equipo=_equipo_para_lead(state, bandeja["code"], lead.details),
                    bot_owner=state.get("bot_owner"),
                )
            except (TimeoutException, WebDriverException, ValueError):
                status, assigned_to, finalize, diagnostic = STATUS_ERROR, "", "", ""
        if status == STATUS_TOMADO and assigned_to and not str(finalize).endswith("/reasignado"):
            # El propietario tras un tomado directo es el usuario de la
            # sesión: distingue "lo tomó el bot" de "lo tomó otra persona"
            # en la relectura tras refresh.
            state["bot_owner"] = assigned_to
        extra = {}
        if motivo:
            extra["motivo"] = motivo
        if assigned_to:
            extra["asignado_a"] = assigned_to
        if finalize:
            extra["finalizacion"] = finalize
        if diagnostic:
            extra["finalize_diag"] = diagnostic
        entry = record_result(
            state,
            lead.lead_id,
            bandeja["code"],
            status,
            lead.details,
            extra=extra or None,
        )
        events.append({"type": "lead_result", "bandeja": bandeja["code"], "status": status, "entry": entry})
    if skipped_status:
        events[0]["skipped_status"] = skipped_status
    return events


def run_cycle(
    driver,
    config: dict,
    state: dict,
    timeout_seconds: int,
    diag_dir: Path | None = None,
) -> list[dict]:
    """Itera las bandejas habilitadas; una caída no frena a las demás.

    Ante ``session_lost`` el ciclo termina de inmediato: la sesión es la misma
    para todas las bandejas, seguir solo repite el fallo.
    """
    events: list[dict] = []
    for bandeja in (b for b in state.get("bandejas", []) if b.get("enabled")):
        try:
            bandeja_events = run_bandeja_cycle(
                driver, config, bandeja, state, timeout_seconds, diag_dir=diag_dir
            )
        except Exception as error:  # noqa: BLE001 — una bandeja caída no frena a las demás
            events.append(
                {
                    "type": "bandeja_error",
                    "bandeja": bandeja["code"],
                    "error": type(error).__name__,
                }
            )
            continue
        events.extend(bandeja_events)
        if any(event["type"] == PAUSE_SESSION_LOST for event in bandeja_events):
            break
    return events
