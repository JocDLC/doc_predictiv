"""Diagnóstico in situ de la marca/WhatsApp contra el Edge dedicado real.

Abre un lead ya procesado en una pestaña NUEVA del navegador del bot y
ejercita la ruta exacta de ``prepare_other_information`` (lapiz -> editor ->
escribir -> verificar) pero CANCELA en vez de guardar — no escribe nada en
Salesforce (y escribe el MISMO texto leído, por si acaso). Mide en qué paso
aparece StaleElementReferenceException y sondea el botón "Send To
Whatsapp" + el toast sin pulsar nada.

Uso: python debug_insitu_mark.py [lead_id] [intentos]
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from selenium.common.exceptions import TimeoutException, WebDriverException

from browser_factory import create_driver, detect_browser
from comment_writer import prepare_other_information
from browser_factory import release_driver
from lead_closure import CLOSURE_HELPERS_SCRIPT, execute_in_any_frame
from salesforce_session import wait_for_lightning_ready
from lead_monitor import _read_other_information_value

ROOT = Path(__file__).parent
DEBUGGER = "127.0.0.1:9222"

WA_PROBE_SCRIPT = (
    CLOSURE_HELPERS_SCRIPT
    + r"""
function whatsappSendButton() {
    const candidates = elements.filter(el => isVisible(el)
        && el.matches('button, [role="button"], a')
        && /whatsapp/.test(normalize(el.textContent)));
    return candidates.find(el => /send to whatsapp|send whatsapp|enviar whatsapp/.test(
        normalize(el.textContent))) || null;
}
function confirmationToast() {
    return elements.find(el => isVisible(el) && el.matches(
        '[class*="toast"], [role="status"], [role="alert"], .slds-notify, '
        + '[class*="notify"], lightning-toast-container')
        && /whatsapp/.test(normalize(el.textContent))) || null;
}
const b = whatsappSendButton();
const t = confirmationToast();
return {
    boton: b ? b.textContent.trim().slice(0, 40) : null,
    toast: t ? t.textContent.trim().slice(0, 120) : null,
};
"""
)

CANCEL_CLICK_ATOMIC_SCRIPT = (
    CLOSURE_HELPERS_SCRIPT
    + r"""
const labels = ['cancelar', 'cancel'];
const cands = elements.filter(el => isVisible(el) && el.matches('button')
    && labels.includes(normalize(el.textContent)));
const target = cands[0] || null;
if (!target) {
    return 'not_found';
}
target.click();
return 'clicked';
"""
)


def load_config() -> dict:
    with (ROOT / "config.json").open(encoding="utf-8") as file:
        return json.load(file)


def probe_editor_cycle(driver, attempt: int) -> dict:
    """Un ciclo de la ruta REAL prepare->cancelar. Devuelve paso y error."""
    result = {"attempt": attempt, "step": "prepare", "error": None, "stale": False}
    try:
        base = _read_other_information_value(driver) or "diagnostico"
        prepare_other_information(driver, base[:80], 20)
        result["verificado"] = True
        result["step"] = "cancelar"
        if execute_in_any_frame(driver, CANCEL_CLICK_ATOMIC_SCRIPT) != "clicked":
            result["sin_cancelar"] = True
        time.sleep(1.0)
        result["step"] = "ok"
    except WebDriverException as error:
        result["error"] = type(error).__name__
        result["stale"] = type(error).__name__ == "StaleElementReferenceException"
    except (TimeoutException, ValueError) as error:
        result["error"] = type(error).__name__
    finally:
        try:
            driver.switch_to.default_content()
        except WebDriverException:
            pass
    return result


def main() -> int:
    lead_id = sys.argv[1] if len(sys.argv) > 1 else "00QbD00000xiijQUAQ"
    attempts = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    config = load_config()
    browser, executable = detect_browser(config["browser"])
    profile = Path(os.path.expandvars(config["profile_directory"])).expanduser()
    driver = create_driver(browser, executable, profile, DEBUGGER)
    try:
        url = f"{config['salesforce_url'].rstrip('/')}/lightning/r/Lead/{lead_id}/view"
        driver.execute_script(f"window.open('{url}', '_blank');")
        time.sleep(2)
        driver.switch_to.window(driver.window_handles[-1])
        wait_for_lightning_ready(driver, 30)
        time.sleep(2)

        print("== Sonda WA (sin pulsar) ==")
        print(json.dumps(execute_in_any_frame(driver, WA_PROBE_SCRIPT), ensure_ascii=False))
        print("== Otra información persistida ==")
        print(repr(_read_other_information_value(driver)))

        if "--post-refresh" in sys.argv:
            # Réplica del caso panel_tras_reload: la marca corre apenas
            # wait_for_lightning_ready suelta, con la ficha aún re-renderizando.
            driver.refresh()
            wait_for_lightning_ready(driver, 30)
            print("(post-refresh: ciclos apenas suelta el 'ready')")

        print(f"== {attempts} ciclos lapiz->editor->escribir->cancelar ==")
        stats = {}
        for i in range(attempts):
            r = probe_editor_cycle(driver, i + 1)
            stats[r["step"]] = stats.get(r["step"], 0) + 1
            print(f"  #{r['attempt']}: step={r['step']} error={r['error']} verificado={r.get('verificado')}")
            time.sleep(1.5)
        print("resumen:", stats)
    finally:
        release_driver(driver)
    return 0


if __name__ == "__main__":
    sys.exit(main())
