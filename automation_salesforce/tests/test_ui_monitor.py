"""Tests funcionales de la vista Monitor de Bandeja en documentador_predictivo.html.

Ejecutan el script real del HTML dentro de Node ``vm`` con stubs de DOM,
EventSource y fetch: verifican las columnas de la tabla, la validación de
franjas, el toggle, el canal SSE (banner + beep) y que no haya polling en reposo.
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
function makeEl(tag) {
  const el = {
    tagName: (tag || 'div').toUpperCase(),
    children: [],
    listeners: {},
    _classes: new Set(),
    dataset: {},
    style: {},
    _text: '',
    value: '',
    checked: false,
    colSpan: 0,
    type: '',
    className: '',
  };
  // Como el DOM real: pisar innerHTML descarta los hijos anteriores.
  Object.defineProperty(el, 'innerHTML', {
    get: () => '',
    set: () => { el.children = []; },
  });
  el.classList = {
    add: c => el._classes.add(c),
    remove: c => el._classes.delete(c),
    toggle: (c, force) => {
      const on = force === undefined ? !el._classes.has(c) : !!force;
      on ? el._classes.add(c) : el._classes.delete(c);
    },
    contains: c => el._classes.has(c),
  };
  Object.defineProperty(el, 'textContent', {
    get: () => el._text,
    set: v => { el._text = String(v); el.children = []; },
  });
  el._attrs = {};
  el.setAttribute = (k, v) => { el._attrs[k] = String(v); };
  el.getAttribute = k => (k in el._attrs ? el._attrs[k] : null);
  el.appendChild = child => { el.children.push(child); return child; };
  el.append = (...kids) => kids.forEach(k => el.children.push(k));
  el.addEventListener = (name, fn) => { el.listeners[name] = fn; };
  el.querySelector = () => makeEl();
  el.querySelectorAll = () => [];
  el.click = () => {};
  el.focus = () => {};
  return el;
}

const storage = {};
const fetchCalls = [];
const esInstances = [];

const context = {
  document: {
    getElementById: id => (elements[id] ||= makeEl()),
    createElement: tag => makeEl(tag),
    createTextNode: text => ({ textContent: String(text) }),
    addEventListener() {},
    querySelectorAll: () => [],
  },
  localStorage: {
    getItem: key => (key in storage ? storage[key] : null),
    setItem: (key, value) => { storage[key] = String(value); },
    removeItem: key => { delete storage[key]; },
  },
  window: {},
  navigator: {},
  indexedDB: { open: () => ({}) },
  location: { hostname: '127.0.0.1', port: '8765' },
  fetch: async (url, options) => {
    fetchCalls.push({ url: String(url), options });
    return {
      ok: true, status: 200,
      json: async () => context.__fetchPayload,
      text: async () => JSON.stringify(context.__fetchPayload),
    };
  },
  EventSource: class {
    constructor(url) { this.url = url; esInstances.push(this); }
    close() {}
  },
  setInterval: fn => { context.__intervals.push(fn); return context.__intervals.length; },
  clearInterval() {},
  setTimeout() {},
  alert() {},
  confirm: message => { context.__confirmMessages.push(String(message)); return true; },
  prompt: () => '',
  console,
  Blob: function () {},
  FileReader: function () {},
  URLSearchParams,
};
context.__intervals = [];
context.__confirmMessages = [];
context.__fetchPayload = { enabled: false, bandejas: [], schedule: [], results: [], running: false };
context.window.AudioContext = class {
  constructor() { context.__beeps = (context.__beeps || 0) + 1; this.currentTime = 0; }
  createOscillator() { return { frequency: {}, connect: x => x, start() {}, stop() {} }; }
  createGain() { return { gain: { setValueAtTime() {}, exponentialRampToValueAtTime() {} }, connect: x => x }; }
  get destination() { return {}; }
};
context.__elements = elements;
context.__fetchCalls = fetchCalls;
context.__esInstances = esInstances;
context.check = (name, condition) => {
  if (condition) console.log('PASS ' + name);
  else console.log('FAIL ' + name);
};
vm.createContext(context);

const scenario = fs.readFileSync(process.argv[3], 'utf-8');
vm.runInContext(script + '\n(async () => {\n' + scenario + '\n})().catch(e => console.log("FAIL exception " + e.message + "\\n" + e.stack));', context);
"""

SCENARIO_JS = r"""
// 1) La tabla del monitor tiene las 14 columnas pedidas, sin '#'; el
//    estado del candidato SÍ se muestra (se agregó para distinguir los
//    Nuevo de los En curso en modo prueba).
check('15 columnas de lead', MONITOR_COLUMNS.length === 15);
const columnKeys = MONITOR_COLUMNS.map(([k]) => k);
check('sin columna de orden #', !columnKeys.includes('#'));
check('estado de candidato presente', columnKeys.includes('estado_candidato'));
check('columna lead_id presente', columnKeys.includes('lead_id'));
check('otra informacion presente', columnKeys.includes('otra_informacion'));

// 2) Validación de franjas hh:mm en la UI. Las franjas solo aceptan
//    bandejas disponibles (habilitadas con link): AR y CO sí, MX no.
monitorState = { bandejas: [
  { code: 'AR', enabled: true, url: 'https://sf.example/r' },
  { code: 'CO', enabled: true, url: 'https://sf.example/r' },
  { code: 'MX', enabled: false, url: '' },
] };
check('sin franjas es válido', scheduleError([]) === '');
check('franja válida aceptada', scheduleError([{ start: '08:00', end: '20:00', bandejas: ['AR'] }]) === '');
check('franja sin bandeja rechazada', scheduleError([{ start: '08:00', end: '20:00' }]) !== '');
check('franja sin bandeja rechazada (lista vacía)', scheduleError([{ start: '08:00', end: '20:00', bandejas: [] }]) !== '');
check('formato inválido rechazado', scheduleError([{ start: '8am', end: '20:00', bandejas: ['AR'] }]) !== '');
check('hora fuera de rango rechazada', scheduleError([{ start: '25:00', end: '20:00', bandejas: ['AR'] }]) !== '');
check('inicio después del fin rechazado', scheduleError([{ start: '18:00', end: '09:00', bandejas: ['AR'] }]) !== '');
check('franjas solapadas rechazadas',
  scheduleError([{ start: '08:00', end: '12:00', bandejas: ['AR'] }, { start: '11:00', end: '14:00', bandejas: ['AR'] }]) !== '');
check('franjas contiguas aceptadas',
  scheduleError([{ start: '08:00', end: '12:00', bandejas: ['AR'] }, { start: '12:00', end: '14:00', bandejas: ['AR'] }]) === '');
// Solape por bandeja: distintas bandejas sí pueden cruzarse, la misma no;
// una franja sin bandejas (todas) pisa cualquier solape.
check('solape en misma bandeja rechazado',
  scheduleError([
    { start: '10:00', end: '12:00', bandejas: ['AR'] },
    { start: '11:00', end: '13:00', bandejas: ['AR'] },
  ]) !== '');
check('solape en bandejas distintas aceptado',
  scheduleError([
    { start: '10:00', end: '12:00', bandejas: ['AR'] },
    { start: '11:00', end: '13:00', bandejas: ['CO'] },
  ]) === '');
check('solape parcial por bandeja compartida rechazado',
  scheduleError([
    { start: '08:00', end: '13:00', bandejas: ['AR', 'CO'] },
    { start: '12:00', end: '18:00', bandejas: ['CO'] },
  ]) !== '');
check('franja en bandeja no disponible rechazada',
  scheduleError([{ start: '08:00', end: '12:00', bandejas: ['MX'] }]) !== '');

// 3) La tabla renderiza los leads del estado con sus columnas.
monitorState = {
  enabled: true, paused_reason: null, last_cycle_at: '2026-10-09T14:32:00+00:00',
  bandejas: [{ code: 'AR', enabled: true, url: 'https://sf.example/r', unassigned_owner: 'AR_LEAD_QUALIF', expected_status: 'Nuevo' }],
  schedule: [], results: [
    { lead_id: '00Q0000000000AAAAA', status: 'tomado', bandeja: 'AR',
      details: { nombre: 'Ana', apellido: 'Prueba', lead_id: '00Q0000000000AAAAA', estado_candidato: 'Nuevo' } },
    { lead_id: '00Q0000000000BBBBB', status: 'tomado_por_otro', bandeja: 'AR', details: {} },
  ],
};
monitorDraftSchedule = [];
renderMonitor();
const table = __elements['monitorTable'];
check('tabla tiene encabezado + 2 filas', table.children.length === 3);
// Orden visible por defecto: # + 15 columnas + ⏱ (hace) + resultado = 18.
// Cada celda lleva el contenido dentro de un div .cell.
const newestRow = table.children[1];
check('18 celdas por fila', newestRow.children.length === 18);
// La columna bandeja va primera tras el #: chip AR para el lead de AR.
check('chip bandeja AR', newestRow.children[1].children[0].children[0].textContent === 'AR'
  && newestRow.children[1].children[0].children[0].className.includes('bandeja-AR'));
// results se muestran del más nuevo al más viejo: BBBBB primero.
check('lead_id en su columna', newestRow.children[14].children[0].textContent === '00Q0000000000BBBBB');
check('columna ausente dice No disponible', newestRow.children[6].children[0].textContent === 'No disponible en bandeja');
check('resultado tomado_por_otro etiquetado', newestRow.children[17].children[0].children[0].textContent === 'tomado por otro');
const secondRow = table.children[2];
check('nombre del lead en la fila', secondRow.children[8].children[0].children[0].textContent === 'Ana');
check('estado del candidato visible', secondRow.children[3].children[0].textContent === 'Nuevo');

// 4) El switch refleja enabled y el semáforo clasifica el estado real.
check('switch aria-checked activo', __elements['monitorToggle'].getAttribute('aria-checked') === 'true');
check('switch etiqueta Encendido', __elements['monitorToggleLabel'].textContent === 'Encendido');
check('tarjeta en verde', __elements['monitorStateCard']._classes.has('state-ok'));
check('estado ok', monitorVisualState({ enabled: true, paused_reason: null }).level === 'ok');
check('espera fuera de horario', monitorVisualState({ enabled: true, paused_reason: 'fuera_de_horario' }).level === 'wait');
check('espera run activo', monitorVisualState({ enabled: true, paused_reason: 'run_activo' }).level === 'wait');
check('espera bot corriendo', monitorVisualState({ enabled: true, bot_running: true }).level === 'wait');
check('alerta sesión caída', monitorVisualState({ enabled: true, paused_reason: 'session_lost' }).level === 'alert');
check('alerta navegador trabado', monitorVisualState({ enabled: true, paused_reason: 'navegador_trabado' }).level === 'alert');
check('alerta sin bandejas', monitorVisualState({ enabled: true, paused_reason: 'sin_bandejas' }).level === 'alert');
check('alerta error de ciclo', monitorVisualState({ enabled: true, paused_reason: 'error:x' }).level === 'alert');
const offState = monitorVisualState({ enabled: false, paused_reason: 'fuera_de_horario' });
check('apagado en gris', offState.level === 'off');
check('motivo de apagado pasa al detalle', offState.details.some(d => d.includes('último ciclo')));
check('en espera no dice ACTIVO',
  !monitorVisualState({ enabled: true, paused_reason: 'fuera_de_horario' }).title.includes('ACTIVO'));

// 5) El estado desactivado apaga el switch y la tarjeta queda gris.
monitorState.enabled = false;
renderMonitor();
check('switch aria-checked apagado', __elements['monitorToggle'].getAttribute('aria-checked') === 'false');
check('switch etiqueta Apagado', __elements['monitorToggleLabel'].textContent === 'Apagado');
check('tarjeta apagada', __elements['monitorStateCard']._classes.has('state-off'));
monitorState.enabled = true;
monitorState.paused_reason = 'session_lost';
renderMonitor();
check('pausa por sesión visible', __elements['monitorStatus'].textContent.includes('sesión de Salesforce'));
check('tarjeta en rojo', __elements['monitorStateCard']._classes.has('state-alert'));
monitorState.paused_reason = 'fuera_de_horario';
renderMonitor();
check('tarjeta en ámbar', __elements['monitorStateCard']._classes.has('state-wait'));
monitorState.paused_reason = null;
monitorState.solo_listar = true;
monitorState.enviar_whatsapp = true;
renderMonitor();
const detailText = __elements['monitorStatusDetail'].textContent;
check('detalle modo prueba', detailText.includes('modo prueba'));
check('detalle whatsapp auto', detailText.includes('WhatsApp auto'));
check('detalle última revisión', detailText.includes('última revisión'));
monitorState.solo_listar = false;
monitorState.enviar_whatsapp = false;
renderMonitor();

// 5b) Lista vacía: la fila de aviso usa la clase monitor-empty (alto legible).
monitorState.results = [];
renderMonitorTable();
const emptyCell = __elements['monitorTable'].children[1].children[0];
check('aviso de lista vacía', emptyCell.textContent === 'Todavía no se detectaron leads.');
check('fila vacía con alto legible', emptyCell.className === 'monitor-empty');
monitorState.results = [
  { lead_id: '00Q0000000000AAAAA', status: 'tomado', bandeja: 'AR', details: {} },
];
renderMonitorTable();

// 5c) La casilla Notificar refleja el flag del servidor (el toast lo emite
// ui_server; la notificación gris del navegador se eliminó).
monitorState.notificar = false;
renderMonitor();
check('notificar apagado destilda la casilla', __elements['monitorNotify'].checked === false);
monitorState.notificar = true;
renderMonitor();
check('notificar encendido tilda la casilla', __elements['monitorNotify'].checked === true);

// 6) Bandejas renderizadas con defaults por país.
const bandejasEl = __elements['monitorBandejas'];
check('tres bandejas AR/CO/MX', bandejasEl.children.length === 3);
check('bandera argentina presente', bandejasEl.children[0].children[1].className.includes('flag-argentina'));
check('owner default colombia', bandejasEl.children[1].children[4].value === 'CO_LEAD_QUALIF');
check('url guardada se precarga', bandejasEl.children[0].children[3].value === 'https://sf.example/r');

// 7) SSE: conectar una vez, token por query, evento tomado → banner + beep.
await connectBotEvents();
check('EventSource creado', __esInstances.length === 1);
check('token va por query', __esInstances[0].url.includes('/api/events?token='));
const es = __esInstances[0];
const beepCount = () => (typeof __beeps === 'undefined' ? 0 : __beeps);
const beforeBeeps = beepCount();
es.onmessage({ data: JSON.stringify({ type: 'monitor', status: 'tomado', bandeja: 'AR' }) });
check('beep al asignar', beepCount() === beforeBeeps + 1);
check('banner visible al asignar',
  !__elements['monitorBanner']._classes.has('hidden') && __elements['monitorBanner'].textContent.includes('lead'));
es.onmessage({ data: JSON.stringify({ type: 'monitor', status: 'no_verificado', bandeja: 'AR' }) });
check('sin beep en no_verificado', beepCount() === beforeBeeps + 1);

// 8) Pérdida del canal: indicador visible y se recupera solo.
es.onerror();
check('conexión perdida visible', !__elements['connLost']._classes.has('hidden'));
es.onopen();
check('se recupera al reconectar', __elements['connLost']._classes.has('hidden'));

// 9b) Un refresco entrante no pisa una edición de bandejas en curso.
const urlInput = bandejasEl.children[0].children[3];
urlInput.value = 'https://sf.example/mi-reporte-sin-guardar';
bandejasDirty = true;
renderMonitor();
check('edición sin guardar sobrevive al refresco',
  urlInput.value === 'https://sf.example/mi-reporte-sin-guardar');
bandejasDirty = false;
renderMonitor();
check('sin edición vuelve al estado guardado',
  __elements['monitorBandejas'].children[0].children[3].value === 'https://sf.example/r');

// 9c) El banner del bot avisa mientras un ciclo del monitor ocupa el navegador.
updateQueueMonitorAlert();
check('sin ciclo el aviso queda oculto',
  document.getElementById('queueMonitorAlert')._classes.has('hidden'));
es.onmessage({ data: JSON.stringify({ type: 'monitor', status: 'cycle_start' }) });
check('cycle_start muestra el aviso en la vista del bot',
  !__elements['queueMonitorAlert']._classes.has('hidden'));
es.onmessage({ data: JSON.stringify({ type: 'monitor', status: 'cycle_end' }) });
await Promise.resolve();
check('cycle_end oculta el aviso', __elements['queueMonitorAlert']._classes.has('hidden'));

// 9d) El bloque de configuración se abre solo si falta configurar bandejas.
localStorage.removeItem('monitorConfigOpen');
const savedBandejas = monitorState.bandejas;
monitorState.bandejas = [];
syncMonitorConfigDetails();
check('config abierta sin bandeja configurada',
  document.getElementById('monitorConfig').open === true);
monitorState.bandejas = [{ code: 'AR', enabled: true, url: 'https://sf.example/r' }];
syncMonitorConfigDetails();
check('config cerrada con bandeja configurada',
  document.getElementById('monitorConfig').open === false);
localStorage.setItem('monitorConfigOpen', '1');
syncMonitorConfigDetails();
check('config respeta lo que dejó la persona',
  document.getElementById('monitorConfig').open === true);
localStorage.removeItem('monitorConfigOpen');
monitorState.bandejas = savedBandejas;

// 10) El fin de un run llega por evento, no por polling en reposo.
__fetchCalls.length = 0;
const intervalsBefore = __intervals.length;
startQueuePolling();
check('el intervalo queda registrado', __intervals.length > intervalsBefore);
await Promise.resolve();
const callsAfterStart = __fetchCalls.length;
__intervals[__intervals.length - 1]();
await Promise.resolve();
check('en reposo el intervalo no llama al servidor', __fetchCalls.length === callsAfterStart);
botRunInProgress = true;
__intervals[__intervals.length - 1]();
await Promise.resolve();
check('con run activo sí consulta', __fetchCalls.length > callsAfterStart);
botRunInProgress = false;

// 11) Limpiar lista confirma, llama al endpoint y refresca el estado vacío.
__fetchCalls.length = 0;
__fetchPayload = { ...monitorState, results: [] };
await clearMonitorResults();
check('limpiar confirma el alcance local',
  __confirmMessages.some(message => message.includes('Salesforce') && message.includes('volver a aparecer')));
check('limpiar usa el endpoint dedicado',
  __fetchCalls[0].url.includes('/api/monitor/clear-results') && __fetchCalls[0].options.method === 'POST');
check('limpiar refresca la tabla vacía', monitorState.results.length === 0);

// 12) Agregar una franja la persiste sola: sin esperar "Guardar horario"
//     (si quedaba solo en el borrador, un F5 la borraba). La franja
//     exige bandeja: sin checkbox tildado no entra al borrador ni hace PUT.
__fetchCalls.length = 0;
monitorDraftSchedule = [];
scheduleDirty = false;
// El servidor devolvería la franja ya persistida tras el PUT.
__fetchPayload = { ...__fetchPayload, schedule: [{ start: '08:00', end: '20:00', bandejas: ['AR'] }] };
document.getElementById('schedStart').value = '08:00';
document.getElementById('schedEnd').value = '20:00';
const qsaBackup = document.querySelectorAll;
document.querySelectorAll = sel =>
  sel.includes('sched-bandeja-cb:checked') ? [{ value: 'AR' }] : qsaBackup(sel);
document.getElementById('schedAdd').listeners['click']();
document.querySelectorAll = qsaBackup;
for (let i = 0; i < 20; i++) await Promise.resolve();
check('agregar franja hace PUT al schedule',
  __fetchCalls.some(c => c.url.includes('/api/monitor/schedule') && c.options.method === 'PUT'));
check('franja persistida queda visible', monitorDraftSchedule.length === 1);

// 12b) Sin bandeja tildada la franja no entra al borrador ni se envía.
__fetchCalls.length = 0;
monitorDraftSchedule = [];
document.getElementById('schedAdd').listeners['click']();
for (let i = 0; i < 20; i++) await Promise.resolve();
check('franja sin bandeja no hace PUT',
  !__fetchCalls.some(c => c.url.includes('/api/monitor/schedule') && c.options.method === 'PUT'));
check('franja sin bandeja no entra al borrador', monitorDraftSchedule.length === 0);

// 13) El resultado muestra a quién quedó asignado el lead.
monitorState.results = [{
  lead_id: '00Q0000000000AAAAA', status: 'tomado', bandeja: 'AR',
  asignado_a: 'Maria Perez', details: {},
}];
renderMonitorTable();
const assignedCell = __elements['monitorTable'].children[1].children[17];
check('asignado a visible en la tabla',
  assignedCell.children[0].children.some(td => td.textContent.includes('Maria Perez')));
"""


@unittest.skipUnless(node_executable(), "node no disponible para tests de UI")
class UiMonitorViewTests(unittest.TestCase):
    def test_header_brand_shows_gbs_rec(self):
        html = UI_PAGE.read_text(encoding="utf-8")
        self.assertIn("GBS REC", html)
        self.assertNotIn("LBS REC", html)

    def test_clear_button_is_present_in_markup(self):
        html = UI_PAGE.read_text(encoding="utf-8")
        self.assertIn('id="monitorClearResults"', html)
        self.assertIn("Limpiar lista", html)

    def test_monitor_view_scenario(self):
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
        self.assertFalse(failures, "Fallos en el escenario del monitor:\n" + output + result.stderr)
        self.assertIn("PASS", output)


if __name__ == "__main__":
    unittest.main()
