"""Diagnóstico del lookup "Cambiar propietario" (solo lectura).

Abre un lead, abre el modal, tipea un nombre y vuelca cada ~2 s:
el valor del input, las opciones visibles y qué devuelve el script de
selección. NUNCA confirma ni guarda: termina cancelando el diálogo.

Uso: python debug_owner_lookup.py <lead_id> "<nombre destino>"
"""

from __future__ import annotations

import sys
import time

from lead_monitor import (
    _OWNER_DIALOG_HELPERS,
    _dismiss_owner_dialog,
    _wait_owner_search_input,
    execute_in_any_frame,
    open_change_owner_dialog,
    wait_record_owner,
    QUEUE_SEARCH_TIMEOUT_SECONDS,
)
from run_distribucion_queue import open_record
from salesforce_session import is_authenticated, load_config, local_path
from browser_factory import create_driver, detect_browser, release_driver

DUMP_SCRIPT = _OWNER_DIALOG_HELPERS + r"""
const dialog = ownerDialog();
const input = ownerSearchInput(dialog);
const seen = [];
if (dialog) {
    for (const el of dialogDescendants(dialog)) {
        if (!isVisible(el)) continue;
        if (el.matches('[role="option"], lightning-base-combobox-item, [class*="slds-listbox__option"], li')
                || el.matches('tr, [role="row"], records-record-picker-row')) {
            const txt = normalize(el.textContent).slice(0, 80);
            if (txt && !seen.includes(txt)) seen.push(txt);
            if (seen.length >= 12) break;
        }
    }
}
return {
    dialog: !!dialog,
    inputFound: !!input,
    inputValue: input ? input.value : null,
    options: seen,
};
"""


def main() -> int:
    lead_id = sys.argv[1] if len(sys.argv) > 1 else "00QbD00000wNoUCUA0"
    wanted = sys.argv[2] if len(sys.argv) > 2 else "ROGER FABIAN VELASCO CAMERO"
    config = load_config()
    browser, executable = detect_browser(config["browser"])
    driver = create_driver(
        browser,
        executable,
        local_path(config["profile_directory"]),
        config.get("debugger_address", "127.0.0.1:9222"),
    )
    try:
        driver.get(config["salesforce_url"])
        if not is_authenticated(driver):
            print("sin sesión")
            return 1
        open_record(driver, config, lead_id, config["timeouts"]["page_load_seconds"])
        print("owner:", wait_record_owner(driver))
        print("modal:", open_change_owner_dialog(driver, 10))
        search_input = _wait_owner_search_input(driver, 10)
        print("input:", search_input is not None)
        if search_input is None:
            return 1
        search_input.clear()
        search_input.send_keys(wanted)
        deadline = time.monotonic() + QUEUE_SEARCH_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            snap = execute_in_any_frame(driver, DUMP_SCRIPT)
            print(f"[{round(QUEUE_SEARCH_TIMEOUT_SECONDS - (deadline - time.monotonic()),1)}s]", snap)
            time.sleep(2)
        _dismiss_owner_dialog(driver)
        return 0
    finally:
        release_driver(driver)


if __name__ == "__main__":
    sys.exit(main())
