"""Contrato de navegador del laboratorio y adaptador Selenium.

El runner del laboratorio orquesta orden, persistencia y reglas; el adaptador
resuelve controles e iframes. El contrato es deliberadamente de negocio
("lee el campo", "escribe y guarda", "pulsa Send To Whatsapp") para que el
mismo flujo corra con Selenium hoy y con agent-browser mañana.
"""

from __future__ import annotations

import re
import time
from typing import Protocol

from selenium.common.exceptions import WebDriverException

from comment_reader import (
    field_result_if_found,
    find_field_value,
    text_without_field_label,
)
from comment_writer import (
    prepare_other_information,
    save_edit_form,
)
from lead_monitor import (
    CLOSURE_HELPERS_SCRIPT,
    SEND_WHATSAPP_CLICK_SCRIPT,
    WA_TOAST_CLOSE_SCRIPT,
    WA_TOAST_PRESENT_SCRIPT,
    WA_TOAST_WAIT_SECONDS,
    execute_in_any_frame,
    open_record,
)
from salesforce_session import is_authenticated, wait_for_lightning_ready

# ---------------------------------------------------------------------------
# Confirmación de WhatsApp con evidencia (compartida por ambos motores).
# Funciones con prefijo wa*/labWa: autocontenidas, no dependen de los helpers
# de cada adaptador. window.__labWaObs persiste entre evals de la MISMA
# pestaña/frame principal; una recarga la invalida y se rearma.
# ---------------------------------------------------------------------------

LAB_WA_CONFIRM_HELPERS = r"""
function waNorm(value) {
    return String(value || '')
        .toLocaleLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .trim()
        .replace(/\s+/g, ' ');
}
function waVis(el) {
    if (!el || !el.isConnected) return false;
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden'
        && style.opacity !== '0' && el.getClientRects().length > 0;
}
function waRoots() {
    const roots = [document];
    for (const frame of document.querySelectorAll('iframe, frame')) {
        try {
            if (frame.contentDocument) roots.push(frame.contentDocument);
        } catch (error) { /* cross-origin: queda explícito, sin cobertura */ }
    }
    return roots;
}
function waAll() {
    const out = [];
    const seen = new Set();
    const walk = scope => {
        if (!scope || seen.has(scope)) return;
        seen.add(scope);
        for (const el of scope.querySelectorAll('*')) {
            out.push(el);
            if (el.shadowRoot) walk(el.shadowRoot);
        }
    };
    for (const root of waRoots()) walk(root);
    return out;
}
function waShadowRoots() {
    // Los toasts reales de Lightning viven dentro de shadow roots
    // (lightning-toast-container): MutationObserver sobre document NO los ve.
    const roots = [];
    const seen = new Set();
    const walk = scope => {
        if (!scope || seen.has(scope)) return;
        seen.add(scope);
        for (const el of scope.querySelectorAll('*')) {
            if (el.shadowRoot) {
                roots.push(el.shadowRoot);
                walk(el.shadowRoot);
            }
        }
    };
    for (const root of waRoots()) walk(root);
    return roots;
}
const WA_TOAST_SELECTOR = '[class*="toast"], [role="status"], [role="alert"], '
    + '.slds-notify, [class*="notify"], lightning-toast-container';
function waToastText(el) { return waNorm(el.innerText || el.textContent || ''); }
function waToastCandidates() {
    return waAll().filter(el => el.matches && el.matches(WA_TOAST_SELECTOR));
}
function waClassifyText(norm) {
    // positive/negative/unrelated: verbo de envío específico, negación primero.
    if (!/whatsapp/.test(norm)) return 'unrelated';
    if (/error|no enviad|not sent|fail|unsuccess|unable|no se pudo|rechaz|cancel/.test(norm)) return 'negative';
    if (/sent to whatsapp|message sent|sending status|sent|enviad|entregad|delivered|en cola|queued|seguimiento del envio/.test(norm)) return 'positive';
    return 'unrelated';
}
function waArm() {
    const state = {
        baseline: new Set(), baselineEls: new Set(), seenEls: new Set(),
        events: [], observer: null, href: String(location.href || ''),
    };
    for (const el of waToastCandidates()) {
        if (waVis(el)) {
            state.baseline.add(waToastText(el));
            state.baselineEls.add(el);
        }
    }
    const observer = new MutationObserver(mutations => {
        for (const m of mutations) {
            if (m.type === 'characterData' || m.type === 'attributes') {
                const target = m.target && m.target.nodeType === 1
                    ? m.target
                    : (m.target && m.target.parentElement);
                const cand = target && target.closest ? target.closest(WA_TOAST_SELECTOR) : null;
                if (cand) {
                    state.events.push({
                        kind: 'changed',
                        norm: waToastText(cand),
                        stale: state.baselineEls.has(cand),
                        at: performance.now(),
                    });
                }
            }
            for (const node of m.addedNodes) {
                if (node.nodeType !== 1) continue;
                const cand = node.matches && node.matches(WA_TOAST_SELECTOR)
                    ? node
                    : (node.querySelector ? node.querySelector(WA_TOAST_SELECTOR) : null);
                if (cand) {
                    // Un nodo NUEVO no es stale aunque repita el texto de un
                    // toast previo: envíos consecutivos emiten el mismo texto.
                    state.seenEls.add(cand);
                    state.events.push({
                        kind: 'added',
                        norm: waToastText(cand),
                        stale: false,
                        at: performance.now(),
                    });
                }
            }
        }
        if (state.events.length > 500) state.events.splice(0, state.events.length - 500);
    });
    for (const root of [...waRoots(), ...waShadowRoots()]) {
        observer.observe(root, {
            subtree: true,
            childList: true,
            characterData: true,
            attributes: true,
            attributeFilter: ['class', 'style', 'aria-hidden'],
        });
    }
    state.observer = observer;
    window.__labWaObs = state;
    return { armed: true, baseline: [...state.baseline] };
}
function waDrain() {
    const state = window.__labWaObs;
    if (!state) return { events: [], baseline: [], armed: false };
    // Red de seguridad: toasts presentes que el observer no registró
    // (raíces shadow creadas después del armado o mutaciones fuera de
    // las raíces observadas). Un elemento que no estaba en baseline es
    // señal fresca aunque el observer lo haya perdido.
    for (const el of waToastCandidates()) {
        if (!state.baselineEls.has(el) && !state.seenEls.has(el)) {
            state.seenEls.add(el);
            state.events.push({
                kind: 'scan',
                norm: waToastText(el),
                stale: false,
                at: performance.now(),
            });
        }
    }
    return {
        events: state.events.splice(0, state.events.length),
        baseline: [...state.baseline],
        armed: true,
        href: state.href,
    };
}
function waEvidence(allEvents, baselineList) {
    // Stale por ELEMENTO (no por texto): un toast nuevo con texto idéntico
    // a uno previo es una señal legítima del envío actual.
    let positive = null;
    let negative = null;
    const relevant = [];
    for (const ev of allEvents || []) {
        if (!ev || !ev.norm || ev.stale) continue;
        const kind = waClassifyText(ev.norm);
        if (kind === 'unrelated') continue;
        relevant.push(ev);
        if (kind === 'positive' && !positive) positive = ev;
        if (kind === 'negative' && !negative) negative = ev;
    }
    const tail = relevant.slice(-20);
    if (positive && negative) {
        return { outcome: 'indeterminado', reason: 'senales_contradictorias', events: tail };
    }
    if (positive) return { outcome: 'confirmado', reason: 'toast_positivo', events: tail };
    if (negative) return { outcome: 'no_confirmado', reason: 'respuesta_negativa', events: tail };
    return { outcome: 'no_confirmado', reason: 'sin_senal', events: tail };
}
function waDispose() {
    const state = window.__labWaObs;
    if (state && state.observer) state.observer.disconnect();
    delete window.__labWaObs;
    return 'disposed';
}
function waSendButtons() {
    return waAll().filter(el => waVis(el)
        && el.matches('button, [role="button"], a')
        && /send to whatsapp|send whatsapp|enviar whatsapp/.test(waNorm(el.textContent)));
}
function waGuardedClick(expectedId) {
    const match = /\/r\/[^/]+\/([A-Za-z0-9]{15,18})\/view/.exec(String(location.href || ''));
    if (!match) return 'sin_id';
    if (match[1].slice(0, 15) !== String(expectedId || '').slice(0, 15)) return 'id_mismatch';
    const buttons = waSendButtons();
    if (!buttons.length) return 'sin_boton';
    const button = buttons[0];
    if (button.disabled || button.getAttribute('aria-disabled') === 'true') return 'deshabilitado';
    const rect = button.getBoundingClientRect();
    if (!(rect.width > 0 && rect.height > 0)) return 'no_accionable';
    // El botón real vive dentro de LIGHTNING-BUTTON (shadow root):
    // document.elementFromPoint no penetra shadow DOM y devuelve el
    // componente página como "cubierta" — falso positivo. Hay que evaluar
    // el punto en la raíz del propio botón.
    const root = button.getRootNode ? button.getRootNode() : document;
    const point = root && root.elementFromPoint ? root : document;
    const cover = point.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
    if (cover && cover !== button && !button.contains(cover)) return 'cubierto';
    button.click();
    return 'clicked';
}
"""

JS_WA_ARM = "return waArm();\n"
JS_WA_DRAIN = "return waDrain();\n"
JS_WA_DISPOSE = "return waDispose();\n"
JS_WA_EVIDENCE = "return waEvidence({events}, {baseline});\n"
JS_WA_GUARDED_CLICK = "return waGuardedClick({lead_id});\n"

RECORD_ID_IN_URL = re.compile(r"/r/[^/]+/([A-Za-z0-9]{15,18})/view")

# Presencia del botón Send To Whatsapp sin clic: reutiliza los helpers del
# monitor pero solo inspecciona — el recorrido de prueba nunca pulsa.
WHATSAPP_BUTTON_PRESENT_SCRIPT = (
    CLOSURE_HELPERS_SCRIPT
    + r"""
function whatsappSendButton() {
    const candidates = elements.filter(el => isVisible(el)
        && el.matches('button, [role="button"], a')
        && /whatsapp/.test(normalize(el.textContent)));
    return candidates.find(el => /send to whatsapp|send whatsapp|enviar whatsapp/.test(
        normalize(el.textContent))) || null;
}
return whatsappSendButton() ? 'found' : 'missing';
"""
)


class LabBrowser(Protocol):
    """Interfaz mínima de la ficha de Lead que necesita el laboratorio."""

    engine: str

    def open_record(self, lead_id: str) -> None: ...

    def is_authenticated(self) -> bool: ...

    def current_record_id(self) -> str: ...

    def field_text(self, labels: tuple[str, ...]) -> str | None:
        """Texto del campo en modo lectura; ``None`` si el campo no se
        renderizó (a distinguir de ``""``, campo presente y vacío)."""
        ...

    def write_and_save_field(
        self,
        labels: tuple[str, ...],
        display_name: str,
        prepared_text: str,
        timeout_seconds: int,
    ) -> None: ...

    def reload(self, timeout_seconds: int) -> None: ...

    def whatsapp_button_present(self) -> bool: ...

    def click_whatsapp(self) -> str:
        """'clicked' | 'sin_boton'. Un solo clic: la orquestación decide."""
        ...

    def whatsapp_toast(self, timeout_seconds: float) -> bool:
        """True si apareció el toast positivo de envío en la ventana dada."""
        ...

    def close_whatsapp_toast(self) -> None: ...

    def arm_whatsapp_observation(self) -> dict:
        """Instala el observador y devuelve ``{armed, baseline}``.

        El baseline captura los textos toast-like presentes ANTES del clic:
        cualquier señal posterior cuyo texto ya estaba visible cuenta como
        ``stale`` y no confirma el envío actual.
        """
        ...

    def guarded_click_whatsapp(self, expected_lead_id: str) -> str:
        """Revalida identidad/accionabilidad y hace UN solo clic.

        Devuelve 'clicked' o un motivo ('sin_boton', 'id_mismatch',
        'deshabilitado', 'no_accionable', 'cubierto', 'sin_id',
        'error:<Tipo>').
        """
        ...

    def collect_whatsapp_evidence(self, timeout_seconds: float) -> dict:
        """Drena el observador hasta el deadline y devuelve evidencia:
        ``{outcome: confirmado|no_confirmado|indeterminado, reason, events}``."""
        ...

    def dispose_whatsapp_observation(self) -> None: ...

    def release(self) -> None: ...


class SeleniumLabBrowser:
    """Adaptador del contrato sobre las primitivas ya probadas en producción."""

    engine = "selenium"

    def __init__(self, driver, config: dict):
        self.driver = driver
        self.config = config

    def open_record(self, lead_id: str) -> None:
        timeout = int(self.config.get("timeouts", {}).get("page_load_seconds", 30))
        open_record(self.driver, self.config, lead_id, timeout)

    def is_authenticated(self) -> bool:
        return is_authenticated(self.driver)

    def current_record_id(self) -> str:
        match = RECORD_ID_IN_URL.search(getattr(self.driver, "current_url", "") or "")
        return match.group(1) if match else ""

    def field_text(self, labels: tuple[str, ...]) -> str | None:
        result = field_result_if_found(self.driver, labels)
        if not result:
            return None
        return text_without_field_label(result["text"], labels)

    def wait_field_text(self, labels: tuple[str, ...], timeout_seconds: int) -> str | None:
        deadline = time.monotonic() + timeout_seconds
        while True:
            value = self.field_text(labels)
            if value is not None:
                return value
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.5)

    def write_and_save_field(
        self,
        labels: tuple[str, ...],
        display_name: str,
        prepared_text: str,
        timeout_seconds: int,
    ) -> None:
        prepare_other_information(self.driver, prepared_text, timeout_seconds, labels, display_name)
        save_edit_form(self.driver, timeout_seconds)

    def read_persisted_field(self, labels: tuple[str, ...], timeout_seconds: int) -> str:
        return find_field_value(self.driver, timeout_seconds, labels)

    def reload(self, timeout_seconds: int) -> None:
        self.driver.refresh()
        wait_for_lightning_ready(self.driver, timeout_seconds)

    def whatsapp_button_present(self) -> bool:
        try:
            return execute_in_any_frame(self.driver, WHATSAPP_BUTTON_PRESENT_SCRIPT) == "found"
        except WebDriverException:
            return False

    def click_whatsapp(self) -> str:
        try:
            return (
                "clicked" if execute_in_any_frame(self.driver, SEND_WHATSAPP_CLICK_SCRIPT) == "clicked" else "sin_boton"
            )
        except WebDriverException as error:
            return f"error:{type(error).__name__}"

    def whatsapp_toast(self, timeout_seconds: float = WA_TOAST_WAIT_SECONDS) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if execute_in_any_frame(self.driver, WA_TOAST_PRESENT_SCRIPT) == "found":
                return True
            time.sleep(0.5)
        return False

    def close_whatsapp_toast(self) -> None:
        try:
            execute_in_any_frame(self.driver, WA_TOAST_CLOSE_SCRIPT)
        except WebDriverException:
            pass

    def _wa_exec(self, body: str):
        """Evalúa los helpers WA en el documento principal.

        ``window.__labWaObs`` debe persistir entre llamadas: hay que usar el
        mismo contexto (el documento principal). ``execute_in_any_frame``
        puede dejar el driver dentro de un iframe tras el save — ahí el
        observer nunca vería el toast del documento principal.
        """
        try:
            self.driver.switch_to.default_content()
        except WebDriverException:
            pass
        return self.driver.execute_script(LAB_WA_CONFIRM_HELPERS + body)

    def arm_whatsapp_observation(self) -> dict:
        try:
            result = self._wa_exec(JS_WA_ARM)
        except WebDriverException:
            return {"armed": False, "baseline": []}
        return result if isinstance(result, dict) else {"armed": False, "baseline": []}

    def guarded_click_whatsapp(self, expected_lead_id: str) -> str:
        import json as _json

        try:
            result = self._wa_exec(
                JS_WA_GUARDED_CLICK.replace("{lead_id}", _json.dumps(expected_lead_id, ensure_ascii=True))
            )
        except WebDriverException as error:
            return f"error:{type(error).__name__}"
        return str(result or "sin_resultado")

    def collect_whatsapp_evidence(self, timeout_seconds: float = WA_TOAST_WAIT_SECONDS) -> dict:
        import json as _json

        deadline = time.monotonic() + timeout_seconds
        events: list = []
        baseline: list = []
        evidence = {"outcome": "no_confirmado", "reason": "sin_senal", "events": []}
        saw_unarmed = False
        while time.monotonic() < deadline:
            try:
                drain = self._wa_exec(JS_WA_DRAIN)
            except WebDriverException:
                drain = None
            if isinstance(drain, dict):
                if drain.get("armed") is False:
                    # __labWaObs no existe en esta ventana: el armado quedó en
                    # otro contexto y cualquier señal posterior es invisible.
                    saw_unarmed = True
                events.extend(drain.get("events") or [])
                if drain.get("baseline"):
                    baseline = drain["baseline"]
                try:
                    evidence = (
                        self._wa_exec(
                            JS_WA_EVIDENCE.replace("{events}", _json.dumps(events, ensure_ascii=True)).replace(
                                "{baseline}", _json.dumps(baseline, ensure_ascii=True)
                            )
                        )
                        or evidence
                    )
                except WebDriverException:
                    pass
                if evidence.get("outcome") == "confirmado":
                    break
            time.sleep(0.5)
        if saw_unarmed and evidence.get("reason") == "sin_senal":
            evidence["reason"] = "observador_perdido"
        return evidence

    def dispose_whatsapp_observation(self) -> None:
        try:
            self._wa_exec(JS_WA_DISPOSE)
        except WebDriverException:
            pass

    def release(self) -> None:
        from browser_factory import release_driver

        release_driver(self.driver)


def normalize_persisted_text(value: str) -> str:
    """Iguala diferencias de solo-forma (mismo criterio que run_document_queue)."""
    lines = str(value or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(" ".join(line.split()) for line in lines).rstrip()
