import json
import sqlite3
import sys
import time

import run_laboratory_queue as rlq
from comment_reader import OTHER_INFORMATION_LABELS

sys.stdout.reconfigure(encoding="utf-8")

c = sqlite3.connect("ui_output/laboratorio/laboratorio.sqlite3")
c.row_factory = sqlite3.Row

# Muestra: 4 confirmados + 4 no_confirmado (los últimos)
confirmed = [dict(r) for r in c.execute(
    "SELECT lead_id, attempt_line, send_status FROM operations"
    " WHERE doc_status='confirmada' AND send_status='confirmado' LIMIT 4"
)]
unconfirmed = [dict(r) for r in c.execute(
    "SELECT lead_id, attempt_line, send_status FROM operations"
    " WHERE doc_status='confirmada' AND send_status='no_confirmado'"
    " ORDER BY updated_at DESC LIMIT 4"
)]
sample = confirmed + unconfirmed

config = json.loads(open("config.json", encoding="utf-8").read())
results = []

for engine in ("selenium", "agent_browser"):
    browser = rlq.make_browser(engine, config)
    try:
        for op in sample:
            entry = {
                "lead_id": op["lead_id"],
                "engine": engine,
                "send_status": op["send_status"],
                "attempt_line": op["attempt_line"],
            }
            started = time.monotonic()
            try:
                browser.open_record(op["lead_id"])
                value = browser.wait_field_text(OTHER_INFORMATION_LABELS, 15)
                entry["elapsed"] = round(time.monotonic() - started, 1)
                if value is None:
                    entry["read"] = "campo_ilegible"
                else:
                    entry["read"] = "persiste" if op["attempt_line"] in value else "FALTA"
                    entry["tail"] = value.strip().splitlines()[-1][:80] if value.strip() else "(vacío)"
            except Exception as e:  # noqa: BLE001
                entry["read"] = f"error:{type(e).__name__}"
                entry["elapsed"] = round(time.monotonic() - started, 1)
            results.append(entry)
            print(json.dumps(entry, ensure_ascii=False), flush=True)
    finally:
        try:
            browser.release()
        except Exception:
            pass

print("\n=== RESUMEN ===")
for engine in ("selenium", "agent_browser"):
    subset = [r for r in results if r["engine"] == engine]
    ok = sum(1 for r in subset if r.get("read") == "persiste")
    print(f"{engine}: {ok}/{len(subset)} líneas persistidas verificadas")
