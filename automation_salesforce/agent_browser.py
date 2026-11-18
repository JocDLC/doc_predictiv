"""Adaptador del laboratorio sobre ``agent-browser`` (CLI nativa, CDP).

El transporte invoca el binario con ``--session`` propio del laboratorio,
adjunto al endpoint CDP del navegador dedicado del bot (el mismo que usa
Selenium). Cada comando es un ``subprocess`` con timeout; el contenido
sensible (texto del campo) viaja por stdin, nunca por argumentos ni logs.

Los scripts JS son adaptaciones de los de ``comment_reader``/
``comment_writer``/``lead_monitor``: el mismo recorrido de shadow DOM, más la
expansión de iframes same-origin dentro de un único ``eval`` (agent-browser
evalúa en el frame activo; los iframes accesibles se recorren por
``contentDocument``).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import unicodedata

from laboratory_browser import (
    JS_WA_ARM,
    JS_WA_DISPOSE,
    JS_WA_DRAIN,
    JS_WA_EVIDENCE,
    JS_WA_GUARDED_CLICK,
    LAB_WA_CONFIRM_HELPERS,
    normalize_persisted_text,
)

DEFAULT_SESSION = "laboratorio"
COMMAND_TIMEOUT_SECONDS = 45
READY_POLL_SECONDS = 0.5

# ---------------------------------------------------------------------------
# Transporte CLI
# ---------------------------------------------------------------------------


class AgentBrowserUnavailable(RuntimeError):
    """El binario no está instalado o no responde."""


def resolve_command(configured: str = "") -> list[str]:
    """Ejecutable de agent-browser: config explícita o PATH."""
    command = str(configured or "").strip()
    if not command:
        command = shutil.which("agent-browser") or ""
    if not command:
        raise AgentBrowserUnavailable(
            "agent-browser no está instalado. Instalá una versión fijada "
            "(npm i -g agent-browser@<versión>, requiere Node >=22) y, si hace "
            "falta, declarala en config.json como agent_browser.command."
        )
    return [command]


def command_available(configured: str = "") -> bool:
    try:
        return bool(resolve_command(configured))
    except AgentBrowserUnavailable:
        return False


class AgentBrowserTransport:
    """Invocación de la CLI con sesión aislada del laboratorio."""

    def __init__(
        self,
        command: list[str],
        debugger_address: str,
        session: str = DEFAULT_SESSION,
        tab_label: str = "lab",
    ):
        self.command = command
        self.session = session
        self.tab_label = tab_label
        port = str(debugger_address or "").rsplit(":", 1)[-1]
        self.cdp_port = port
        self.connected = False

    def _argv(self, *args: str) -> list[str]:
        # --pin-tab: la sesión queda atada a su pestaña 'lab'. Si el foco del
        # usuario cambia, los eval nunca se ejecutan en pestañas ajenas.
        return [*self.command, "--session", self.session, "--pin-tab", *args]

    def run(
        self,
        *args: str,
        input_text: str | None = None,
        timeout_seconds: float = COMMAND_TIMEOUT_SECONDS,
    ) -> str:
        """Ejecuta la CLI; devuelve stdout. Nunca loguea el input."""
        argv: list[str] | str = self._argv(*args)
        executable = str(argv[0]).lower()
        if os.name == "nt" and executable.endswith((".cmd", ".bat")):
            # Los shims de npm en Windows son .cmd: CreateProcess no los
            # ejecuta directo, hay que pasar por cmd.exe. La línea se arma
            # como string con quoting explícito: list2cmdline no entrecomilla
            # '&' y cmd cortaría la URL/argumentos ahí.
            quoted = " ".join('"' + a.replace('"', '""') + '"' for a in argv)
            argv = f'cmd /c "{quoted}"'
        try:
            completed = subprocess.run(
                argv,
                input=input_text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                shell=False,
            )
        except FileNotFoundError as error:
            raise AgentBrowserUnavailable(str(error)) from error
        except subprocess.TimeoutExpired as error:
            raise TimeoutError(f"agent-browser no respondió en {timeout_seconds:.0f}s: {' '.join(args[:2])}") from error
        if completed.returncode != 0:
            stderr = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(f"agent-browser falló ({' '.join(args[:2])}): {stderr[:300]}")
        return completed.stdout

    def connect(self, timeout_seconds: float = 15.0) -> None:
        self.run("connect", self.cdp_port, timeout_seconds=timeout_seconds)
        # Pestaña dedicada: sin esto la sesión se adosa a la pestaña activa
        # del usuario y cada navegación/eval la pisaría.
        try:
            self.run(
                "tab",
                "new",
                "--label",
                self.tab_label,
                "about:blank",
                timeout_seconds=timeout_seconds,
            )
        except RuntimeError:
            # El label ya existe (run anterior interrumpido): se reusa.
            self.run("tab", self.tab_label, timeout_seconds=timeout_seconds)
        self.connected = True

    def open_url(self, url: str, timeout_seconds: float = COMMAND_TIMEOUT_SECONDS) -> None:
        self.run("open", url, timeout_seconds=timeout_seconds)

    def reload(self, timeout_seconds: float = COMMAND_TIMEOUT_SECONDS) -> None:
        self.run("reload", timeout_seconds=timeout_seconds)

    def eval(self, script_body: str, timeout_seconds: float = COMMAND_TIMEOUT_SECONDS):
        """Evalúa ``script_body`` (debe terminar en ``return <valor>``)."""
        expression = "(function(){" + script_body + "})()"
        stdout = self.run("eval", "--stdin", "--json", input_text=expression, timeout_seconds=timeout_seconds)
        return parse_eval_output(stdout)

    def close_session(self) -> None:
        """Cierra la pestaña del laboratorio y libera la sesión.

        Nunca cierra el navegador ni las pestañas del usuario.
        """
        try:
            self.run("tab", "close", self.tab_label, timeout_seconds=10.0)
        except Exception:  # noqa: BLE001 — best-effort
            pass
        try:
            self.run("session", "stop", self.session, timeout_seconds=10.0)
        except Exception:  # noqa: BLE001 — best-effort; el navegador es del usuario
            pass
        self.connected = False


def parse_eval_output(stdout: str):
    """Extrae el valor de un ``eval --json``.

    La CLI envuelve el resultado en un objeto de respuesta; se desciende por
    las claves conocidas hasta el valor devuelto por el script.
    """
    text = str(stdout or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # stdout puede venir con ruido; intenta la última línea JSON.
        for line in reversed(text.splitlines()):
            try:
                parsed = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
        else:
            raise ValueError(f"Salida de agent-browser no es JSON: {text[:200]}")
    depth = 0
    while isinstance(parsed, dict) and depth < 5:
        for key in ("result", "value", "data", "output"):
            if key in parsed:
                parsed = parsed[key]
                depth += 1
                break
        else:
            return parsed
    return parsed


# ---------------------------------------------------------------------------
# Scripts DOM (evaluados en la página; recorren shadow DOM + iframes same-origin)
# ---------------------------------------------------------------------------

LAB_JS_HELPERS = r"""
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
        && style.opacity !== '0'
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
function allElements() {
    const scopes = [document];
    for (const frame of document.querySelectorAll('iframe, frame')) {
        try {
            if (frame.contentDocument) {
                scopes.push(frame.contentDocument);
            }
        } catch (error) { /* iframe cross-origin: se omite */ }
    }
    const elements = [];
    for (const scope of scopes) {
        collect(scope, new Set(), elements);
    }
    return elements;
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
function textAfterLabel(value, labels) {
    // Solo salta la línea del label (posición fija al inicio). El contenido
    // posterior se conserva literal: una línea "Modificar Otra información"
    // escrita por el usuario NO se filtra — los textos asistivos se excluyen
    // por posición DOM (insideEditTrigger), nunca por coincidencia semántica.
    const lines = String(value || '').split(/\r?\n/).map(line => line.trim());
    const labelIndex = lines.findIndex(line => labels.includes(normalize(line)));
    const body = labelIndex >= 0 ? lines.slice(labelIndex + 1) : lines;
    return body.filter(line => line).join('\n').trim();
}
function insideEditTrigger(element) {
    let current = element;
    while (current) {
        if (current.matches && current.matches(
            '.test-id__inline-edit-trigger, .slds-assistive-text, button'
        )) {
            return true;
        }
        const root = current.getRootNode ? current.getRootNode() : null;
        current = current.parentElement || (root && root.host) || null;
    }
    return false;
}
function valueFromField(container, labels, elements) {
    const descendants = [];
    collect(container, new Set(), descendants);
    const ownerNames = descendants.filter(element => element.matches
        && element.matches('.owner-name') && isVisible(element));
    for (const element of ownerNames) {
        const value = textAfterLabel(element.innerText || element.textContent || '', labels);
        if (value) {
            return value;
        }
    }
    // Área de valor dedicada: .test-id__field-value no contiene el lápiz ni
    // texto asistivo; se lee directa y literal. "--" es el placeholder de
    // campo vacío de Lightning, se trata como vacío.
    const fieldValues = descendants.filter(element => element.matches
        && element.matches('.test-id__field-value') && isVisible(element));
    for (const element of fieldValues) {
        if (insideEditTrigger(element)) {
            continue;
        }
        const raw = String(element.innerText || element.textContent || '').trim();
        if (raw === '--') {
            return '';
        }
        if (raw) {
            return textAfterLabel(raw, labels) || raw;
        }
    }
    const preferred = descendants.filter(element => element.matches && element.matches(
        'textarea, input:not([type="hidden"]), '
        + 'lightning-formatted-text, lightning-base-formatted-text, '
        + '.slds-form-element__static, [data-output-element-id]'
    ));
    for (const element of preferred) {
        if (insideEditTrigger(element)) {
            continue;
        }
        const isFormControl = element.matches('textarea, input, select');
        const rawValue = isFormControl
            ? element.value
            : element.innerText || element.textContent || '';
        const value = textAfterLabel(rawValue, labels);
        if (value) {
            return value;
        }
    }
    const leafValues = [];
    for (const element of descendants) {
        if (element.children.length || element.shadowRoot || element.matches('button, script, style')) {
            continue;
        }
        // El lápiz lleva texto asistivo "Modificar <label>": se excluye por
        // POSICIÓN DOM, no por texto. Así no se borra historial legítimo.
        if (insideEditTrigger(element)) {
            continue;
        }
        const value = textAfterLabel(element.value || element.innerText || element.textContent || '', labels);
        if (value && !labels.includes(normalize(value))) {
            leafValues.push(value);
        }
    }
    if (leafValues.length) {
        return leafValues.join('\n');
    }
    // Sin fallback a innerText del contenedor: incluiría el texto asistivo
    // del lápiz como valor. Si no hay área de valor ni hojas, el campo está
    // vacío (findField distingue found:true,text:'' de no encontrado).
    return '';
}
function findField(elements, labels) {
    for (const element of elements) {
        if (!isVisible(element) || !labels.includes(normalize(element.textContent))) {
            continue;
        }
        const containers = fieldContainers(element);
        for (const container of containers) {
            const value = valueFromField(container, labels, elements);
            if (value) {
                return { found: true, text: value };
            }
        }
        if (containers.length) {
            return { found: true, text: '' };
        }
    }
    return { found: false, text: '' };
}
function isEditable(candidate) {
    return isVisible(candidate)
        && candidate.matches('textarea, input:not([type="hidden"])')
        && !candidate.readOnly
        && !candidate.disabled;
}
function labelForCandidate(candidate, elements, labels) {
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
        const attrLabel = current.getAttribute('label') || current.getAttribute('field-label');
        if (attrLabel) {
            return attrLabel;
        }
        const descendants = [];
        collect(current, new Set(), descendants);
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
function labelElements(elements, labels) {
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
function findEditor(elements, labels) {
    const editors = elements.filter(isEditable);
    for (const editor of editors) {
        if (labels.includes(normalize(labelForCandidate(editor, elements, labels)))) {
            return editor;
        }
    }
    for (const label of labelElements(elements, labels)) {
        const editor = editorAlignedWithLabel(label, editors);
        if (editor) {
            return editor;
        }
    }
    return null;
}
function findEditControl(elements, labels) {
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
function whatsappSendButton(elements) {
    const candidates = elements.filter(el => isVisible(el)
        && el.matches('button, [role="button"], a')
        && /whatsapp/.test(normalize(el.textContent)));
    return candidates.find(el => /send to whatsapp|send whatsapp|enviar whatsapp/.test(
        normalize(el.textContent))) || null;
}
function confirmationToast(elements) {
    return elements.find(el => isVisible(el) && el.matches(
        '[class*="toast"], [role="status"], [role="alert"], .slds-notify, '
        + '[class*="notify"], lightning-toast-container')
        && /whatsapp/.test(normalize(el.textContent))
        && /sent|enviad|exit|status|seguimiento/.test(normalize(el.textContent))) || null;
}
"""

# Acciones (cuerpo de función; terminan en return). {labels} se inyecta con
# json.dumps: el contenido nunca viaja por argumentos de línea de comandos.
JS_FIELD_READ = """
const elements = allElements();
return findField(elements, {labels});
"""

JS_CLICK_EDIT = """
const elements = allElements();
const control = findEditControl(elements, {labels});
if (!control) { return 'sin_lapiz'; }
control.scrollIntoView({block: 'center', inline: 'nearest'});
control.click();
return 'clicked';
"""

JS_EDITOR_PRESENT = """
const elements = allElements();
return findEditor(elements, {labels}) ? 'found' : 'missing';
"""

JS_EDITOR_SET = """
const elements = allElements();
const editor = findEditor(elements, {labels});
if (!editor) { return 'sin_editor'; }
const text = {text};
editor.scrollIntoView({block: 'center', inline: 'nearest'});
editor.focus();
editor.value = text;
editor.dispatchEvent(new Event('input', {bubbles: true}));
editor.dispatchEvent(new Event('change', {bubbles: true}));
editor.blur();
editor.dispatchEvent(new FocusEvent('blur', {bubbles: true}));
editor.dispatchEvent(new FocusEvent('focusout', {bubbles: true}));
return 'ok';
"""

JS_EDITOR_VALUE = """
const elements = allElements();
const editor = findEditor(elements, {labels});
return editor ? String(editor.value || '') : null;
"""

JS_SAVE_CLICK = """
const elements = allElements();
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
const button = (preferred.length ? preferred : candidates)[0] || null;
if (!button) { return 'sin_boton'; }
button.click();
return 'clicked';
"""

JS_EDITOR_CLOSED = """
const elements = allElements();
return findEditor(elements, {labels}) ? 'open' : 'closed';
"""

JS_WA_BUTTON = """
const elements = allElements();
return whatsappSendButton(elements) ? 'found' : 'missing';
"""

JS_WA_CLICK = """
const elements = allElements();
const button = whatsappSendButton(elements);
if (!button) { return 'sin_boton'; }
button.click();
return 'clicked';
"""

JS_WA_TOAST = """
const elements = allElements();
return confirmationToast(elements) ? 'found' : 'missing';
"""

JS_WA_TOAST_CLOSE = """
const elements = allElements();
const toast = confirmationToast(elements);
if (!toast) { return 'sin_toast'; }
const closeButton = toast.querySelector(
    'button[title*="lose"], .slds-notify__close, button, [role="button"]');
if (closeButton) { closeButton.click(); }
return 'closed';
"""

JS_PAGE_STATE = """
return {
    url: String(location.href || ''),
    readyState: String(document.readyState || ''),
    title: String(document.title || ''),
};
"""

JS_NAVIGATE = """
window.location.assign({url});
return 'navigating';
"""

JS_RELOAD = """
location.reload();
return 'reloading';
"""

JS_SCROLL_DOWN = """
// Lightning monta los campos de la ficha por IntersectionObserver: hay que
// desplazar el scroller real (div.viewport / workspace) para que renderice.
const candidates = [
    document.querySelector('div.viewport'),
    document.scrollingElement,
    document.documentElement,
].filter(Boolean);
let moved = 'bottom';
for (const scroller of candidates) {
    const before = scroller.scrollTop;
    scroller.scrollTop = before + Math.max(320, scroller.clientHeight * 0.8);
    if (scroller.scrollTop > before) { moved = 'moved'; break; }
}
if (moved === 'bottom') {
    for (const el of document.querySelectorAll('div, section')) {
        if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 200) {
            const before = el.scrollTop;
            el.scrollTop = before + Math.max(320, el.clientHeight * 0.8);
            if (el.scrollTop > before) { moved = 'moved'; break; }
        }
    }
}
return moved;
"""


def _normalize_label(value: str) -> str:
    """Equivalente Python del normalize() JS: matchea "información"~"informacion"."""
    text = unicodedata.normalize("NFD", str(value or "").lower())
    return "".join(char for char in text if not unicodedata.combining(char)).strip()


def _labels_literal(labels: tuple[str, ...]) -> str:
    # ensure_ascii=True: el script viaja por stdin hacia la CLI, que decodifica
    # UTF-8. Un 'ó' crudo llega corrupto (cp1252 en Windows) y rompe el eval
    # con "SyntaxError: Unexpected end of input".
    # Los scripts comparan labels.includes(normalize(texto_del_dom)): hay que
    # incluir también la variante normalizada de cada label, si no "otra
    # información" nunca matchea el texto normalizado "otra informacion".
    expanded: list[str] = []
    for label in labels:
        for variant in (str(label), _normalize_label(label)):
            if variant not in expanded:
                expanded.append(variant)
    return json.dumps(expanded, ensure_ascii=True)


def _text_literal(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=True)


# ---------------------------------------------------------------------------
# Adaptador al contrato LabBrowser
# ---------------------------------------------------------------------------

RECORD_ID_IN_URL = re.compile(r"/r/[^/]+/([A-Za-z0-9]{15,18})/view")
LOGIN_URL_MARKERS = ("login", "auth", "secur/frontdoor")


class AgentLabBrowser:
    """El mismo contrato que SeleniumLabBrowser, ejecutado por la CLI."""

    engine = "agent_browser"

    def __init__(self, transport: AgentBrowserTransport, config: dict):
        self.transport = transport
        self.config = config
        self.timeout = int(config.get("timeouts", {}).get("page_load_seconds", 30))

    # --- helpers internos --------------------------------------------------

    def _eval(self, body: str):
        return self.transport.eval(LAB_JS_HELPERS + body)

    def _eval_labels(self, body: str, labels: tuple[str, ...]):
        return self._eval(body.replace("{labels}", _labels_literal(labels)))

    def _page_state(self) -> dict:
        result = self.transport.eval(JS_PAGE_STATE)
        return result if isinstance(result, dict) else {"url": "", "readyState": "", "title": ""}

    def _wait_ready(self, timeout_seconds: int) -> dict:
        deadline = time.monotonic() + timeout_seconds
        state = self._page_state()
        while state.get("readyState") != "complete" and time.monotonic() < deadline:
            time.sleep(READY_POLL_SECONDS)
            state = self._page_state()
        # Lightning repinta tras el loadEvent: esperar a que el DOM tenga
        # contenido propio del registro (la ficha tarda más que readyState).
        wait_deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < wait_deadline:
            state = self._page_state()
            if state.get("readyState") == "complete":
                return state
            time.sleep(READY_POLL_SECONDS)
        return state

    # --- contrato ----------------------------------------------------------

    def connect(self) -> None:
        if not self.transport.connected:
            self.transport.connect()

    def open_record(self, lead_id: str) -> None:
        salesforce_url = str(self.config["salesforce_url"]).rstrip("/")
        object_name = str(self.config.get("record_object_api_name", "Lead"))
        url = f"{salesforce_url}/lightning/r/{object_name}/{lead_id}/view"
        self.connect()
        self.transport.open_url(url)
        self._wait_ready(self.timeout)

    def is_authenticated(self) -> bool:
        try:
            state = self._page_state()
        except Exception:  # noqa: BLE001 — sin respuesta = no autenticable
            return False
        url = str(state.get("url") or "")
        if not url or any(marker in url.lower() for marker in LOGIN_URL_MARKERS):
            # localhost/file:// sirve para el fixture de pruebas de la CLI.
            return not any(marker in url.lower() for marker in LOGIN_URL_MARKERS) and bool(url)
        return "force.com" in url or "salesforce" in url

    def current_record_id(self) -> str:
        try:
            match = RECORD_ID_IN_URL.search(str(self._page_state().get("url") or ""))
        except Exception:  # noqa: BLE001
            return ""
        return match.group(1) if match else ""

    def field_text(self, labels: tuple[str, ...]) -> str | None:
        result = self._eval_labels(JS_FIELD_READ, labels)
        if not isinstance(result, dict) or not result.get("found"):
            return None
        text = str(result.get("text") or "")
        lines = text.splitlines()
        normalized_labels = {str(label).casefold() for label in labels}
        normalized_labels |= {_normalize_label(label) for label in labels}
        if lines and _normalize_label(lines[0]) in normalized_labels:
            text = "\n".join(lines[1:]).strip()
        return text

    def wait_field_text(self, labels: tuple[str, ...], timeout_seconds: int) -> str | None:
        deadline = time.monotonic() + timeout_seconds
        scroll_bottom = False
        while True:
            value = self.field_text(labels)
            if value is not None:
                return value
            if time.monotonic() >= deadline:
                return None
            # Si el campo aún no montó, desplaza el scroller de la ficha:
            # Lightning renderiza las secciones inferiores al hacer scroll.
            if not scroll_bottom:
                try:
                    scroll_bottom = self._eval(JS_SCROLL_DOWN) == "bottom"
                except Exception:  # noqa: BLE001 — el nudge es best-effort
                    scroll_bottom = True
            time.sleep(READY_POLL_SECONDS)

    def write_and_save_field(
        self,
        labels: tuple[str, ...],
        display_name: str,
        prepared_text: str,
        timeout_seconds: int,
    ) -> None:
        # Lápiz → editor → escribir con eventos → verificar → Guardar.
        # Misma secuencia que comment_writer.prepare_other_information, con
        # polling Python en vez de WebDriverWait (cada eval es una llamada).
        deadline = time.monotonic() + timeout_seconds
        clicked = "sin_lapiz"
        while time.monotonic() < deadline:
            clicked = self._eval_labels(JS_CLICK_EDIT, labels)
            if clicked == "clicked":
                break
            time.sleep(READY_POLL_SECONDS)
        if clicked != "clicked":
            raise ValueError(f"No apareció el lápiz de edición de '{display_name}'.")

        found = "missing"
        while time.monotonic() < deadline:
            found = self._eval_labels(JS_EDITOR_PRESENT, labels)
            if found == "found":
                break
            time.sleep(READY_POLL_SECONDS)
        if found != "found":
            raise ValueError(f"No apareció el editor de '{display_name}'.")

        # Lightning inicializa el componente tras abrir el editor; misma
        # estabilización que la versión Selenium antes de escribir.
        time.sleep(2.0)
        for attempt in range(2):
            result = self._eval_labels(JS_EDITOR_SET.replace("{text}", _text_literal(prepared_text)), labels)
            if result != "ok":
                raise ValueError(f"El editor de '{display_name}' desapareció al escribir.")
            value = self._eval_labels(JS_EDITOR_VALUE, labels)
            if normalize_persisted_text(value or "") == normalize_persisted_text(prepared_text):
                time.sleep(0.8)
                value = self._eval_labels(JS_EDITOR_VALUE, labels)
                if normalize_persisted_text(value or "") == normalize_persisted_text(prepared_text):
                    break
            if attempt == 0:
                time.sleep(0.5)
                continue
            raise ValueError(f"El editor no quedó con el texto esperado (esperado {len(prepared_text)} caracteres).")

        saved = "sin_boton"
        while time.monotonic() < deadline:
            saved = self._eval(JS_SAVE_CLICK)
            if saved == "clicked":
                break
            time.sleep(READY_POLL_SECONDS)
        if saved != "clicked":
            raise ValueError(f"No se encontró el botón Guardar de '{display_name}'.")

        closed_deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < closed_deadline:
            if self._eval_labels(JS_EDITOR_CLOSED, labels) == "closed":
                break
            time.sleep(READY_POLL_SECONDS)
        # Igual que Selenium: el editor cierra antes de persistir; la pausa
        # evita que la recarga de verificación aborte el guardado.
        time.sleep(3.0)

    def reload(self, timeout_seconds: int) -> None:
        self.transport.reload()
        self._wait_ready(timeout_seconds)

    def whatsapp_button_present(self) -> bool:
        try:
            return self._eval(JS_WA_BUTTON) == "found"
        except Exception:  # noqa: BLE001
            return False

    def click_whatsapp(self) -> str:
        try:
            return "clicked" if self._eval(JS_WA_CLICK) == "clicked" else "sin_boton"
        except Exception as error:  # noqa: BLE001
            return f"error:{type(error).__name__}"

    def whatsapp_toast(self, timeout_seconds: float = 15.0) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self._eval(JS_WA_TOAST) == "found":
                return True
            time.sleep(READY_POLL_SECONDS)
        return False

    def close_whatsapp_toast(self) -> None:
        try:
            self._eval(JS_WA_TOAST_CLOSE)
        except Exception:  # noqa: BLE001
            pass

    # --- confirmación con evidencia (helpers compartidos con Selenium) -----

    def _wa_eval(self, body: str):
        return self.transport.eval(LAB_WA_CONFIRM_HELPERS + body)

    def arm_whatsapp_observation(self) -> dict:
        try:
            result = self._wa_eval(JS_WA_ARM)
        except Exception:  # noqa: BLE001 — observador degradado: sin baseline
            return {"armed": False, "baseline": []}
        return result if isinstance(result, dict) else {"armed": False, "baseline": []}

    def guarded_click_whatsapp(self, expected_lead_id: str) -> str:
        try:
            result = self._wa_eval(JS_WA_GUARDED_CLICK.replace("{lead_id}", _text_literal(expected_lead_id)))
        except Exception as error:  # noqa: BLE001
            return f"error:{type(error).__name__}"
        return str(result or "sin_resultado")

    def collect_whatsapp_evidence(self, timeout_seconds: float = 15.0) -> dict:
        deadline = time.monotonic() + timeout_seconds
        events: list = []
        baseline: list = []
        evidence = {"outcome": "no_confirmado", "reason": "sin_senal", "events": []}
        while time.monotonic() < deadline:
            try:
                drain = self._wa_eval(JS_WA_DRAIN)
            except Exception:  # noqa: BLE001
                drain = None
            if isinstance(drain, dict):
                events.extend(drain.get("events") or [])
                if drain.get("baseline"):
                    baseline = drain["baseline"]
                try:
                    collected = self._wa_eval(
                        JS_WA_EVIDENCE.replace("{events}", json.dumps(events, ensure_ascii=True)).replace(
                            "{baseline}", json.dumps(baseline, ensure_ascii=True)
                        )
                    )
                    if isinstance(collected, dict):
                        evidence = collected
                except Exception:  # noqa: BLE001
                    pass
                if evidence.get("outcome") == "confirmado":
                    break
            time.sleep(READY_POLL_SECONDS)
        return evidence

    def dispose_whatsapp_observation(self) -> None:
        try:
            self._wa_eval(JS_WA_DISPOSE)
        except Exception:  # noqa: BLE001
            pass

    def release(self) -> None:
        self.transport.close_session()


def make_agent_browser(config: dict) -> AgentLabBrowser:
    """Factory: resuelve ejecutable, sesión y endpoint desde config.json."""
    lab_config = config.get("agent_browser") or {}
    command = resolve_command(str(lab_config.get("command") or ""))
    session = str(lab_config.get("session") or DEFAULT_SESSION)
    debugger_address = str(config.get("debugger_address", "127.0.0.1:9222"))
    return AgentLabBrowser(AgentBrowserTransport(command, debugger_address, session), config)
