"""Diagnóstico local: JS real en Node, runner con fakes, SQLite en solo lectura.

No abre navegadores, no escribe Salesforce ni modifica el journal productivo.
Las sondas informan PASS/FAIL según el comportamiento deseado; FAIL es un
hallazgo pendiente de implementar, no un test aprobado.
"""

import json
import sqlite3
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "automation_salesforce"))
sys.path.insert(0, str(ROOT / "automation_salesforce" / "tests"))

import agent_browser as ab
import run_laboratory_queue as lab
from test_run_laboratory_queue import (
    CONFIG,
    LEAD,
    FakeBrowser,
    ar_fields,
    tmp_store,
)


def js_probe(expression):
    # DOM mínimo: ejecuta las funciones productivas, no replica su regex.
    script = ab.LAB_JS_HELPERS + r"""
global.window = {getComputedStyle: () => ({
    display: 'block', visibility: 'visible', opacity: '1'
})};
function element(text, visible=true) {
    return {textContent:text, isConnected:true,
        matches:()=>true, getClientRects:()=>visible ? [{}] : []};
}
""" + "\nconsole.log(JSON.stringify(" + expression + "));"
    completed = subprocess.run(
        ["node", "-"], input=script, text=True, encoding="utf-8",
        capture_output=True, check=True,
    )
    return json.loads(completed.stdout)


def main():
    findings = []

    def record(name, actual, expected):
        findings.append({
            "case": name, "actual": actual, "expected": expected,
            "status": "PASS" if actual == expected else "FAIL",
        })

    for name, text, expected in (
        ("positive_toast", "WhatsApp enviado exitosamente", True),
        ("negative_toast", "Error: WhatsApp no enviado", False),
        ("unrelated_status", "WhatsApp status actualizado", False),
    ):
        record(name, js_probe(
            "Boolean(confirmationToast([element(" + json.dumps(text) + ")]))"
        ), expected)
    record("hidden_success", js_probe(
        "Boolean(confirmationToast([element('WhatsApp enviado', false)]))"
    ), False)
    # Un elemento viejo es indistinguible para la API actual: no hay baseline.
    record("stale_toast", js_probe(
        "Boolean(confirmationToast([element('WhatsApp enviado exitosamente')]))"
    ), False)
    record("accent_normalization", js_probe(
        "normalize('  Otra INFORMACI\\u00d3N  ')"
    ), "otra informacion")
    record("preserve_literal_history", js_probe(
        "textAfterLabel('1 INT previo\\nModificar Otra información\\n2 INT previo', "
        "['otra informacion'])"
    ), "1 INT previo\nModificar Otra información\n2 INT previo")

    with tempfile.TemporaryDirectory() as temporary:
        store = tmp_store(temporary)
        browser = FakeBrowser(ar_fields(), toast=False)
        outcome = lab.send_for_lead(browser, LEAD, CONFIG, store, "campaign")
        record("no_toast_not_confirmed", outcome["status"], "documentado_wa_no_confirmado")
        record("same_campaign_blocks", store.is_blocked("campaign", LEAD["lead_id"])[0], True)
        record("new_campaign_blocks", store.is_blocked("new_campaign", LEAD["lead_id"])[0], True)

    class MissingIdentity(FakeBrowser):
        def current_record_id(self):
            return ""

    browser = MissingIdentity(ar_fields())
    record("missing_identity_blocks", lab.verify_lead(browser, LEAD, CONFIG)["status"], "bloqueado")

    class WrongIdentity(FakeBrowser):
        def current_record_id(self):
            return "00Q000000000002AAA"

    class ExpiredSession(FakeBrowser):
        def is_authenticated(self):
            return False

    for name, browser_type in (("wrong_identity", WrongIdentity), ("expired_session", ExpiredSession)):
        with tempfile.TemporaryDirectory() as temporary:
            browser = browser_type(ar_fields())
            outcome = lab.send_for_lead(browser, LEAD, CONFIG, tmp_store(temporary), "campaign")
            record(name + "_blocks_send", [outcome["status"], len(browser.writes), browser.wa_clicks],
                   ["bloqueado", 0, 0])

    browser = FakeBrowser(ar_fields())
    lab.verify_lead(browser, LEAD, CONFIG)
    record("verification_has_no_mutations", [len(browser.writes), browser.wa_clicks], [0, 0])

    db = ROOT / "automation_salesforce/ui_output/laboratorio/laboratorio.sqlite3"
    journal = {"available": db.exists()}
    if db.exists():
        with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            journal["operations"] = [dict(row) for row in conn.execute(
                "SELECT engine, doc_status, send_status, count(*) AS n "
                "FROM operations GROUP BY engine, doc_status, send_status"
            )]
            journal["evidence_present"] = conn.execute(
                "SELECT count(*) FROM operations WHERE evidence NOT IN ('{}', '', 'null')"
            ).fetchone()[0]
    results_path = ROOT / "automation_salesforce/queues/cola_laboratorio_activa.resultado.json"
    comparison = {}
    if results_path.exists():
        entries = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines()
                   if line.strip()]
        by_lead = {}
        for entry in entries:
            by_lead.setdefault((entry["run_id"], entry["lead_id"]), {})[entry["engine"]] = entry
        pairs = [pair for pair in by_lead.values() if "selenium" in pair and "agent_browser" in pair]
        successful = [pair for pair in pairs
                      if all(pair[engine]["status"] == "apto" for engine in ("selenium", "agent_browser"))]
        comparison = {
            "run_ids": sorted({entry["run_id"] for entry in entries}),
            "evaluations": len(entries), "unique_run_leads": len(by_lead),
            "paired_status_agreements": sum(
                pair["selenium"]["status"] == pair["agent_browser"]["status"] for pair in pairs),
            "pairs": len(pairs), "both_apto_pairs": len(successful),
            "paired_apto_medians": {
                engine: median(pair[engine]["elapsed_seconds"] for pair in successful)
                for engine in ("selenium", "agent_browser")
            } if successful else {},
            "disagreements": [
                {engine: {"status": pair[engine]["status"], "detail": pair[engine].get("detail", "")}
                 for engine in ("selenium", "agent_browser")}
                for pair in pairs if pair["selenium"]["status"] != pair["agent_browser"]["status"]
            ],
        }
    report = {
        "scope": "Node with minimal DOM and Python fakes; not a live Salesforce test",
        "counts": dict(Counter(row["status"] for row in findings)),
        "findings": findings,
        "journal_read_only": journal,
        "comparison_read_only": comparison,
    }
    output = Path(__file__).with_name("diagnostico-resultados.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 1 if any(row["status"] == "FAIL" for row in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
