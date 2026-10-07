"""Tests funcionales de la selección de cierre en documentador_predictivo.html.

Ejecutan las funciones reales del HTML dentro de Node ``vm`` con stubs de
DOM/localStorage, verificando que el cierre es una selección independiente de
la documentación, con motivo explícito por Lead y cola cerrada.
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

const scenario = fs.readFileSync(process.argv[3], 'utf-8');
vm.runInContext(script + '\n' + scenario, context);
"""

SCENARIO_JS = r"""
const lead1 = {
  id: '00Q000000000001AAA', nombre: 'Uno', agente: 't', tel: '',
  llamadas: '', resultadoReg: '', desc1: '',
  attempts: [{ ts: '1', date: '01/10/2026', time: '10:00', result: 'NO-ANSWER', tel: '', callId: '1' }],
};
const lead2 = {
  id: '00Q000000000002AAA', nombre: 'Dos', agente: 't', tel: '',
  llamadas: '', resultadoReg: '', desc1: '',
  attempts: [],
};
const lead3 = {
  id: '00Q000000000003AAA', nombre: 'Tres', agente: 't', tel: '',
  llamadas: '', resultadoReg: '', desc1: '',
  attempts: [{ ts: '1', date: '01/10/2026', time: '11:00', result: 'NO-ANSWER', tel: '', callId: '2' }],
};
leads = [lead1, lead2, lead3];
progress = {};
fileKey = 'test_cierre_1';
fileName = 'test.csv';
selectedIds.clear();
selectedIds.add(lead1.id);
selectedIds.add(lead2.id);
selectedIds.add(lead3.id);
closureSelection = {};

// 1) Marcar cierre sin motivo: preparado pero no listo.
closureSelection[lead1.id] = '';
check('incluido sin motivo no está listo', closureReadyLeads().length === 0);
check('sin motivo se reporta como faltante', closureMissingReason().map(l => l.id)[0] === lead1.id);

// 2) Asignar motivo lo deja listo; lead sin checkbox no entra al lote.
closureSelection[lead1.id] = 'ilocalizable';
check('con motivo queda listo', closureReadyLeads().map(l => l.id)[0] === lead1.id);
let queue = buildCloseQueue();
check('cola de cierre lleva operation close_leads', queue.operation === 'close_leads');
check('cola lleva solo el lead preparado', queue.leads.length === 1);
check('el lead lleva su motivo', queue.leads[0].reason === 'ilocalizable' && queue.leads[0].lead_id === lead1.id);

// 3) Lote mixto: cada lead con su propio motivo.
closureSelection[lead2.id] = 'deja_de_interactuar';
queue = buildCloseQueue();
check('lote mixto lleva dos leads', queue.leads.length === 2);
check('motivos por lead correctos',
  queue.leads[1].reason === 'deja_de_interactuar' && queue.leads[1].lead_id === lead2.id);

// 4) El cierre no depende de la documentación: lead sin intentos pendientes
//    puede incluirse igual (decisión del auxiliar).
check('lead sin intentos entra al cierre', queue.leads.some(l => l.lead_id === lead2.id));

// 5) Desmarcar el checkbox lo saca del lote aunque tenga motivo guardado.
delete closureSelection[lead2.id];
check('sin checkbox sale del lote', closureReadyLeads().map(l => l.id).join(',') === lead1.id);

// 6) Motivo desconocido no genera lead listo (defensa ante JSON manipulado).
closureSelection[lead3.id] = 'motivo_inventado';
check('motivo inválido no produce lead listo', !closureReadyLeads().some(l => l.id === lead3.id));
check('motivo inválido queda como faltante', closureMissingReason().map(l => l.id)[0] === lead3.id);
delete closureSelection[lead3.id];

// 7) La selección de cierre no afecta la cola de documentación.
const docQueue = buildBotQueue(selectedIds);
check('documentación independiente del cierre', docQueue.leads.every(l => l.lead_id !== undefined));

// 8) Leads fuera de la vista de cola no entran al cierre.
closureSelection['00Q999999999999ZZZ'] = 'ilocalizable';
check('lead fuera de la cola no entra al cierre', !closureReadyLeads().some(l => l.id === '00Q999999999999ZZZ'));

// 9) Un Lead verificado como cerrado sale solo de la selección de cierre.
applyCloseResult({ lead_id: lead1.id, status: 'cerrado_verificado', run_id: 'run_c1' }, new Set(leads.map(l => l.id)));
check('cerrado verificado se desmarca del cierre', closureSelection[lead1.id] === undefined);
check('badge de cierre queda registrado', lastClosureStatus[lead1.id] === 'cerrado_verificado');

// 10) Un resultado parcial (conversión pendiente) NO desmarca: sigue elegible
//     para reanudar, pero con la marca visible para revisión.
closureSelection[lead2.id] = 'deja_de_interactuar';
applyCloseResult({ lead_id: lead2.id, status: 'conversion_pendiente', run_id: 'run_c1' }, new Set(leads.map(l => l.id)));
check('conversión pendiente sigue seleccionado', closureSelection[lead2.id] === 'deja_de_interactuar');

// 11) Resultado de un Lead ajeno al CSV se ignora.
check('resultado ajeno ignorado',
  applyCloseResult({ lead_id: '00Q999999999999ZZZ', status: 'cerrado_verificado', run_id: 'run_c1' }, new Set(['00Q000000000001AAA'])) === 'ignorado');

// 12) El país de la base se detecta por TEL1 sobre TODAS las filas.
check('lote argentino detectado',
  detectBatchCountry([{ TEL1: '915491234567890' }, { TEL1: '915491234567891' }]).country === 'argentina');
check('lote colombiano detectado',
  detectBatchCountry([{ TEL1: '9571234567890' }]).country === 'colombia');
check('lote mexicano detectado',
  detectBatchCountry([{ TEL1: '93521234567890' }]).country === 'mexico');
check('base mezclada bloqueada',
  detectBatchCountry([{ TEL1: '915491234567890' }, { TEL1: '9571234567890' }]).status === 'mixed');
check('colombia+mexico bloqueado aunque compartan campos',
  detectBatchCountry([{ TEL1: '9571234567890' }, { TEL1: '93521234567890' }]).status === 'mixed');
check('prefijo desconocido bloqueado',
  detectBatchCountry([{ TEL1: '99991234567890' }]).status === 'invalid');
check('telefono vacio bloqueado',
  detectBatchCountry([{ TEL1: '' }]).status === 'invalid');
check('base vacia detectada', detectBatchCountry([]).status === 'empty');

// 13) El gate compara la base detectada con el selector y ofrece el cambio.
batchInfo = detectBatchCountry([{ TEL1: '9571234567890' }]);
queueCountryMode = 'argentina';
const gateMismatch = countryGate();
check('selector distinto bloquea y propone cambio',
  !gateMismatch.ok && gateMismatch.fixMode === 'colombia_mexico');
check('mensaje de discrepancia no expone telefonos', !/9\d{6}/.test(gateMismatch.message));
queueCountryMode = 'colombia_mexico';
check('mismo modo pasa el gate', countryGate().ok);
batchInfo = { status: 'mixed', country: '', counts: { argentina: 1, colombia: 1 } };
const gateMixed = countryGate();
check('lote mixto no pasa el gate', !gateMixed.ok);
check('mensaje de mezcla sin telefonos', !/9\d{6}/.test(gateMixed.message));

// 14) Las colas congelan el modo de país elegido.
queueCountryMode = 'colombia_mexico';
check('cola de documentación lleva country', buildBotQueue(selectedIds).country === 'colombia_mexico');
check('cola de cierre lleva country', buildCloseQueue().country === 'colombia_mexico');
check('campo de intentos Colombia/México es Comentario', attemptsFieldKey() === 'comentario');
queueCountryMode = 'argentina';
check('campo de intentos Argentina es Otra información', attemptsFieldKey() === 'otra_informacion');
check('cola vuelve a argentina', buildBotQueue(selectedIds).country === 'argentina');
"""


@unittest.skipUnless(node_executable(), "node no disponible para tests de UI")
class UiClosureSelectionTests(unittest.TestCase):
    def test_closure_selection_scenario(self):
        with TemporaryDirectory() as temporary_directory:
            harness_path = Path(temporary_directory) / "harness.js"
            scenario_path = Path(temporary_directory) / "scenario.js"
            harness_path.write_text(HARNESS_JS, encoding="utf-8")
            scenario_path.write_text(SCENARIO_JS, encoding="utf-8")
            result = subprocess.run(
                [node_executable(), str(harness_path), str(UI_PAGE), str(scenario_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )

        output = result.stdout
        failures = [line for line in output.splitlines() if line.startswith("FAIL")]
        self.assertFalse(failures, "Fallos en el escenario de cierre:\n" + output + result.stderr)
        self.assertIn("PASS", output)


if __name__ == "__main__":
    unittest.main()
