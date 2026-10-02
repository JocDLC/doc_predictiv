"""Tests funcionales del estado de documentación en la UI (documentador_predictivo.html).

Ejecutan las funciones reales del HTML dentro de Node ``vm`` con stubs de
DOM/localStorage, reproduciendo el incidente de falsos ``guardado``: resultados
y snapshots históricos no deben cerrar llamadas nuevas del CSV actual.
"""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
UI_PAGE = REPOSITORY_ROOT / "documentador_predictivo.html"
FALLBACK_NODE = Path(r"C:\Users\ax24611\Downloads\_dev\tools\node-v24.21.0-win-x64\node.exe")


def node_executable() -> str | None:
    node = shutil.which("node")
    if node:
        return node
    return str(FALLBACK_NODE) if FALLBACK_NODE.is_file() else None


HARNESS_JS = r"""
const fs = require('fs');
const vm = require('vm');

const htmlPath = process.argv[2];
const script = fs.readFileSync(htmlPath, 'utf-8').match(/<script>([\s\S]*)<\/script>/)[1];

const elements = {};
function makeEl() {
  return {
    addEventListener() {},
    classList: { add() {}, remove() {}, toggle() {}, contains: () => true },
    innerHTML: '', textContent: '', value: '', checked: false, style: {},
    dataset: {}, appendChild() {}, append() {},
    querySelector() { return makeEl(); },
    querySelectorAll() { return []; },
    click() {}, focus() {},
  };
}

const storage = {};
const context = {
  document: {
    getElementById: id => (elements[id] ||= makeEl()),
    createElement: () => makeEl(),
    addEventListener() {},
  },
  localStorage: {
    getItem: key => (key in storage ? storage[key] : null),
    setItem: (key, value) => { storage[key] = String(value); },
    removeItem: key => { delete storage[key]; },
  },
  window: {},
  navigator: {},
  indexedDB: { open: () => ({}) },
  location: { hostname: '', port: '' },
  fetch: () => Promise.reject(new Error('sin red en tests')),
  setInterval: () => 0,
  clearInterval() {},
  setTimeout() {},
  alert() {},
  confirm: () => true,
  prompt: () => '',
  console,
  Blob: function () {},
  FileReader: function () {},
};
context.check = (name, condition) => {
  if (condition) console.log('PASS ' + name);
  else console.log('FAIL ' + name);
};
vm.createContext(context);

// El escenario va dentro del MISMO programa evaluado: las funciones y el
// estado de la app (leads, progress, etc.) viven en el scope léxico.
const scenario = fs.readFileSync(process.argv[3], 'utf-8');
vm.runInContext(script + '\n' + scenario, context);
"""

SCENARIO_JS = r"""
// Fixture ficticia: dos intentos NUEVOS del CSV actual (C/D) y evidencia
// histórica que solo cubre llamadas viejas (A/B).
const lead = {
  id: '00Q000000000001AAA', nombre: 'Test', agente: 't', tel: '',
  llamadas: '', resultadoReg: '', desc1: '',
  attempts: [
    { ts: '1', date: '29/09/2026', time: '14:14', result: 'ANSWER-MACHINE', tel: '', callId: '1790709220.356411' },
    { ts: '2', date: '30/09/2026', time: '13:41', result: 'NO-ANSWER', tel: '', callId: '1790793665.523415' },
  ],
};
leads = [lead];
progress = {};
fileKey = 'test_137';
fileName = 'test.csv';

// 1) Resultado legado "guardado" sin call_ids: no confirma el CSV actual.
let status = applyBotResult({ lead_id: lead.id, status: 'guardado', at: '2026-09-28T23:02:00Z' });
check('resultado legado queda historico', status === 'historico');
check('resultado legado no marca done', isDone(lead) === false);

// 2) Snapshot legado con otros call_ids: evidencia real pero no cubre C/D.
applySnapshot({
  lead_id: lead.id,
  field_value: '2 INT\tBuzon\t24/09/2026\t13:46\t1790275580.100812\n3 INT\tNo contesta\t25/09/2026\t08:36\t1790343380.158281',
  base_hash: 'x', read_at: 't',
});
check('snapshot viejo no cierra intentos nuevos', isDone(lead) === false);
check('pendientes siguen siendo los dos nuevos', pendingAttempts(lead).length === 2);

// 3) El lead sigue siendo elegible para la cola con los intentos nuevos.
let queue = buildBotQueue(new Set([lead.id]));
check('cola incluye el lead con intentos nuevos', queue.leads.length === 1);
check('cola lleva ambos call_id nuevos',
  queue.leads[0].attempts.map(a => a.call_id).join(',') === '1790709220.356411,1790793665.523415');

// 4) Resultado v2 parcial: documenta solo el primer call_id.
status = applyBotResult({
  lead_id: lead.id, status: 'parcial', run_id: 'run_x', at: 't',
  documented_call_ids: ['1790709220.356411'],
});
check('resultado parcial se reporta', status === 'parcial');
check('parcial no cierra el lead', isDone(lead) === false);
check('queda un solo pendiente', pendingAttempts(lead).map(a => a.callId)[0] === '1790793665.523415');

// 5) Resultado v2 completo: cierra el lead.
status = applyBotResult({
  lead_id: lead.id, status: 'guardado', run_id: 'run_x', at: 't', elapsed_seconds: 21.2,
  documented_call_ids: ['1790709220.356411', '1790793665.523415'],
});
check('guardado v2 marca done', isDone(lead) === true);
check('cola vacía tras documentar todo', buildBotQueue(new Set([lead.id])).leads.length === 0);

// 6) Una tanda posterior con llamada nueva reabre el lead.
lead.attempts.push({ ts: '3', date: '01/10/2026', time: '09:00', result: 'NO-ANSWER', tel: '', callId: '1790999999.000001' });
check('llamada nueva reabre el lead', isDone(lead) === false);
check('solo la llamada nueva queda pendiente', pendingAttempts(lead).length === 1);
queue = buildBotQueue(new Set([lead.id]));
check('cola exporta solo el intento nuevo', queue.leads[0].attempts.length === 1);

// 7) ya_documentado v2 confirma sin escritura.
applyBotResult({
  lead_id: lead.id, status: 'ya_documentado', run_id: 'run_y', at: 't',
  documented_call_ids: ['1790709220.356411', '1790793665.523415', '1790999999.000001'],
});
check('ya_documentado cierra el lead', isDone(lead) === true);

// 8) Resultado de un lead ajeno al CSV se ignora.
status = applyBotResult({ lead_id: '00Q999999999999ZZZ', status: 'guardado', documented_call_ids: ['1.1'] });
check('lead ajeno ignorado', status === 'ignorado');

// 9) Snapshot viejo + error reciente no convierte el lead a done.
const lead2 = {
  id: '00Q000000000002AAA', nombre: 'T2', agente: 't', tel: '',
  llamadas: '', resultadoReg: '', desc1: '',
  attempts: [{ ts: '1', date: '30/09/2026', time: '10:00', result: 'NO-ANSWER', tel: '', callId: '1790888888.000001' }],
};
leads.push(lead2);
applySnapshot({ lead_id: lead2.id, field_value: '1 INT\tViejo\t20/09/2026\t09:00\t1790000000.000001', base_hash: 'x', read_at: 't' });
applyBotResult({ lead_id: lead2.id, status: 'error', run_id: 'run_x', at: 't' });
check('error + snapshot viejo no marca done', isDone(lead2) === false);

// 10) Marca manual cubre los intentos visibles y no se hereda.
const lead3 = {
  id: '00Q000000000003AAA', nombre: 'T3', agente: 't', tel: '',
  llamadas: '', resultadoReg: '', desc1: '',
  attempts: [{ ts: '1', date: '30/09/2026', time: '10:00', result: 'NO-ANSWER', tel: '', callId: '1790777777.000001' }],
};
leads.push(lead3);
setDone(lead3, true);
check('marca manual documenta', isDone(lead3) === true);
lead3.attempts.push({ ts: '2', date: '01/10/2026', time: '10:00', result: 'NO-ANSWER', tel: '', callId: '1790777777.000002' });
check('marca manual no cubre intento nuevo', isDone(lead3) === false);

// 11) extractCallIdsFromText no confunde teléfonos ni fechas con call_ids.
const ids = extractCallIdsFromText('nota 2999999999\n4 INT texto 30/09/2026 13:41 1790793665.523415');
check('extrae solo el call_id', ids.size === 1 && ids.has('1790793665.523415'));
"""


class UiDocumentationStateTests(unittest.TestCase):
    def setUp(self):
        node = node_executable()
        if not node:
            self.skipTest("Node.js no disponible para ejecutar las funciones JS reales")
        self.node = node

    def run_ui_scenario(self) -> str:
        with TemporaryDirectory() as temporary_directory:
            harness_path = Path(temporary_directory) / "harness.js"
            scenario_path = Path(temporary_directory) / "scenario.js"
            harness_path.write_text(HARNESS_JS, encoding="utf-8")
            scenario_path.write_text(SCENARIO_JS, encoding="utf-8")
            completed = subprocess.run(
                [self.node, str(harness_path), str(UI_PAGE), str(scenario_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
        output = completed.stdout + completed.stderr
        if completed.returncode != 0:
            self.fail(f"El harness JS falló:\n{output}")
        return output

    def test_incident_scenarios_in_real_ui_functions(self):
        output = self.run_ui_scenario()
        for line in output.splitlines():
            if line.startswith("FAIL"):
                self.fail(f"Escenario JS falló: {line}\n\n{output}")
        passed = [line for line in output.splitlines() if line.startswith("PASS")]
        self.assertGreaterEqual(len(passed), 10, output)


if __name__ == "__main__":
    unittest.main()
