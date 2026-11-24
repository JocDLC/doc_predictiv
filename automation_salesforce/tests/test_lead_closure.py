import inspect
import itertools
import json
import subprocess
import unittest
from unittest.mock import Mock, patch

from selenium.common.exceptions import WebDriverException

import comment_reader
import comment_writer
import lead_closure as closure
from tests.test_ui_closure import node_executable


DOM_HARNESS = r"""
const assert = require('node:assert/strict');
const payload = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
class Element {
    constructor(tag, attrs = {}, text = '') {
        this.tagName = tag.toUpperCase();
        this.attrs = attrs;
        this.text = text;
        this.children = [];
        this.parentElement = null;
        this.shadowRoot = null;
        this.isConnected = true;
        this.visible = true;
        this.value = '';
        this.clicks = 0;
        this.scrollTop = 0;
        this.scrollHeight = 500;
        this.clientHeight = 100;
    }
    get id() { return this.attrs.id || ''; }
    get disabled() { return !!this.attrs.disabled; }
    get textContent() { return this.text + this.children.map(c => c.textContent).join(''); }
    getAttribute(name) { return this.attrs[name] ?? null; }
    getRootNode() { return this.parentElement ? this.parentElement.getRootNode() : this; }
    append(child) { child.parentElement = this; this.children.push(child); return child; }
    attachShadow() {
        this.shadowRoot = new Element('root');
        this.shadowRoot.host = this;
        return this.shadowRoot;
    }
    matches(selector) {
        return selector.split(',').some(part => {
            part = part.trim();
            if (part === '*') return true;
            if (part.includes(' ') || part.includes(':')) return false;
            const tag = part.match(/^[\w-]+/);
            if (tag && this.tagName !== tag[0].toUpperCase()) return false;
            const attrs = [...part.matchAll(/\[([\w-]+)(?:([*~]?=)"([^"]*)")?\]/g)];
            if (!attrs.every(([, name, op, value]) => {
                const actual = this.getAttribute(name);
                return actual !== null && (!op || (op === '=' ? actual === value : actual.includes(value)));
            })) return false;
            const classes = [...part.matchAll(/\.([\w-]+)/g)];
            return classes.every(([, name]) => (this.attrs.class || '').split(' ').includes(name));
        });
    }
    querySelectorAll(selector) {
        return this.children.flatMap(child => [
            ...(child.matches(selector) ? [child] : []), ...child.querySelectorAll(selector),
        ]);
    }
    getClientRects() {
        let node = this;
        while (node) {
            if (!node.visible || node.attrs['aria-hidden'] === 'true') return [];
            node = node.parentElement || node.host;
        }
        return [{}];
    }
    scrollIntoView() {}
    click() { this.clicks++; if (this.onClick) this.onClick(); }
    focus() {}
    blur() {}
    dispatchEvent(event) { (this.events = this.events || []).push(event.type); return true; }
    closest(selector) {
        let current = this;
        while (current) {
            if (current.matches && current.matches(selector)) return current;
            const root = current.getRootNode ? current.getRootNode() : null;
            current = current.parentElement || (root && root.host) || null;
        }
        return null;
    }
}
globalThis.FocusEvent = globalThis.FocusEvent || class FocusEvent extends Event {};
global.document = new Element('document');
global.window = {getComputedStyle: element => ({
    display: element.visible ? 'block' : 'none', visibility: 'visible',
})};
let sequence = 0;
function field(label, selected, {visible = true, input = false, expanded = true} = {}) {
    const panel = document.append(new Element('section'));
    panel.visible = visible;
    const host = panel.append(new Element('lightning-base-combobox'));
    const root = host.attachShadow();
    const id = 'list-' + (++sequence);
    const control = root.append(new Element(input ? 'input' : 'button', {
        role: 'combobox', 'aria-label': label, 'aria-controls': id,
        'aria-expanded': String(expanded), class: 'slds-combobox__input',
    }, input ? '' : selected));
    if (input) control.value = selected;
    const list = root.append(new Element('div', {role: 'listbox', id}));
    list.visible = expanded;
    control.onClick = () => {
        list.visible = !list.visible;
        control.attrs['aria-expanded'] = String(list.visible);
    };
    function option(text, apiValue = 'API value') {
        const item = list.append(new Element('lightning-base-combobox-item', {
            role: 'option', 'data-value': apiValue,
        }));
        item.attachShadow().append(new Element('span', {title: text}, text));
        item.onClick = () => {
            if (input) control.value = text; else control.text = text;
            list.visible = false;
            control.attrs['aria-expanded'] = 'false';
        };
        return item;
    }
    return {panel, host, control, list, option};
}
const labels = ['cualificacion'];
const sublabels = ['sub-cualificacion'];
const call = (name, ...args) => new Function(payload.scripts[name])(...args);
eval(payload.scenario);
"""


@unittest.skipUnless(node_executable(), "Node requerido para scripts DOM")
class FieldTextDomTests(unittest.TestCase):
    def run_dom(self, scenario):
        result = subprocess.run(
            [node_executable(), "-e", DOM_HARNESS],
            input=json.dumps({"scripts": {"field": comment_reader.FIELD_TEXT_SCRIPT}, "scenario": scenario}),
            text=True,
            capture_output=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mexico_subqualification_read_uses_the_spaced_label(self):
        self.run_dom(
            "const mexicoLabels = "
            + json.dumps(closure.SUBQUALIFICATION_FIELD_LABELS)
            + ";"
            + """
            const other = document.append(new Element('records-record-layout-item'));
            other.append(new Element('span', {}, 'Cualificación'));
            other.append(new Element('lightning-formatted-text', {}, 'Rechazo no argumentado'));
            const item = document.append(new Element('records-record-layout-item'));
            item.append(new Element('span', {}, 'Sub cualificación'));
            item.append(new Element('lightning-formatted-text', {}, 'Ilocalizable'));
            assert.equal(call('field', mexicoLabels).text, 'Ilocalizable');
        """
        )

    def test_owner_lookup_reads_visible_name_not_internal_id(self):
        self.run_dom("""
            const item = document.append(new Element('records-record-layout-item'));
            item.append(new Element('span', {}, 'Propietario del candidato'));
            const owner = item.append(new Element('force-owner-lookup', {
                'data-output-element-id': 'owner',
            }));
            owner.value = '005XXXXXXXXXXXXXXX';
            owner.attachShadow().append(new Element('span', {class: 'owner-name'}, 'AR_LEAD_COLD'));
            assert.equal(call('field', ['propietario del candidato']).text, 'AR_LEAD_COLD');
        """)


@unittest.skipUnless(node_executable(), "Node requerido para scripts DOM")
class EditorDomTests(unittest.TestCase):
    """El textarea del comentario vive dentro de un lightning-textarea (LWC):
    el framework re-sincroniza el nodo interno desde la propiedad `value`
    del componente. Escribir solo el textarea interno deja el formulario
    vacío — el bug de "los valores no quedaron" del run eca47b."""

    def run_dom(self, scenario):
        result = subprocess.run(
            [node_executable(), "-e", DOM_HARNESS],
            input=json.dumps(
                {
                    "scripts": {
                        "set": comment_writer.SET_EDITOR_VALUE_ATOMIC_SCRIPT,
                        "read": comment_writer.READ_EDITOR_VALUE_ATOMIC_SCRIPT,
                    },
                    "scenario": scenario,
                }
            ),
            text=True,
            capture_output=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_lwc_host_overwrites_inner_textarea_value(self):
        self.run_dom("""
            const item = document.append(new Element('records-record-layout-item'));
            const host = item.append(new Element('lightning-textarea', {label: 'Comentario'}));
            const root = host.attachShadow();
            const textarea = root.append(new Element('textarea'));
            // Lightning re-sincroniza el textarea desde host.value en cada
            // commit del componente: lo leído en el editor es el modelo.
            Object.defineProperty(textarea, 'value', {
                get() { return host.value; },
                set(v) { this._shadow = v; },
            });
            // Sin write al host: el textarea queda vacío pese al set.
            const result = call('set', ['comentario'], 'Ilocalizable');
            assert.equal(host.value, 'Ilocalizable');
            assert.equal(call('read', ['comentario']), 'Ilocalizable');
            // El change también se despacha en el host para que el
            // formulario actualice su modelo (un commit posterior del
            // picklist borraba el valor si no llegaba).
            assert.ok((host.events || []).includes('change'));
        """)

    def test_plain_textarea_still_receives_the_value(self):
        self.run_dom("""
            const item = document.append(new Element('records-record-layout-item'));
            const textarea = item.append(new Element('textarea', {'aria-label': 'Comentario'}));
            const result = call('set', ['comentario'], 'Ilocalizable');
            assert.equal(result, 'Ilocalizable');
            assert.equal(textarea.value, 'Ilocalizable');
            assert.equal(call('read', ['comentario']), 'Ilocalizable');
        """)


@unittest.skipUnless(node_executable(), "Node requerido para scripts DOM")
class PicklistDomTests(unittest.TestCase):
    def run_dom(self, scenario):
        scripts = {
            "trigger": closure.PICKLIST_TRIGGER_SCRIPT,
            "atomic": closure.CLICK_PICKLIST_TRIGGER_ATOMIC_SCRIPT,
            "cancel": closure.CLICK_CANCEL_EDIT_ATOMIC_SCRIPT,
            "value": closure.PICKLIST_VALUE_SCRIPT,
            "pick": closure.PICK_OPTION_SCRIPT,
            "count": closure.OPEN_OPTIONS_COUNT_SCRIPT,
        }
        result = subprocess.run(
            [node_executable(), "-e", DOM_HARNESS],
            input=json.dumps({"scripts": scripts, "scenario": scenario}),
            text=True,
            capture_output=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_hidden_form_is_never_read_for_either_reason(self):
        self.run_dom("""
            const hidden = field('Cualificación', 'Rechazo no argumentado', {visible:false});
            const active = field('Cualificación', 'Rechazo argumentado');
            assert.equal(call('trigger', labels), active.control);
            assert.equal(call('value', labels), 'rechazo argumentado');
            hidden.control.text = 'Rechazo argumentado';
            active.control.text = 'Rechazo no argumentado';
            assert.equal(call('value', labels), 'rechazo no argumentado');
        """)

    def test_shadow_option_is_selected_only_in_its_own_listbox(self):
        self.run_dom("""
            const foreign = field('Otro campo', '--Ninguno--');
            const wrong = foreign.option('Rechazo argumentado');
            const active = field('Cualificación', '--Ninguno--');
            const right = active.option('Rechazo argumentado', 'Argued refusal');
            assert.equal(call('pick', 'Rechazo argumentado', labels), 'clicked');
            assert.equal(wrong.clicks, 0);
            assert.equal(right.clicks, 1);
            assert.equal(call('value', labels), 'rechazo argumentado');
        """)

    def test_atomic_trigger_clicks_closed_control_and_reports_expanded(self):
        self.run_dom("""
            const closed = field('Cualificación', '--Ninguno--', {expanded: false});
            assert.equal(call('atomic', labels), 'clicked');
            assert.equal(closed.control.clicks, 1);
            // Ya abierto: no vuelve a clicar (un segundo clic lo cerraría).
            assert.equal(call('atomic', labels), 'expanded');
            assert.equal(closed.control.clicks, 1);
        """)

    def test_atomic_trigger_reports_not_found_without_control(self):
        self.run_dom("""
            field('Otro campo', '--Ninguno--', {expanded: false});
            assert.equal(call('atomic', ['cualificacion inexistente']), 'not_found');
        """)

    def test_cancel_atomic_prefers_the_button_inside_the_form_footer(self):
        self.run_dom("""
            const footer = document.append(new Element('footer'));
            footer.append(new Element('button', {}, 'Guardar'));
            const cancel = footer.append(new Element('button', {}, 'Cancelar'));
            const stray = document.append(new Element('button', {}, 'Cancelar'));
            assert.equal(call('cancel', []), 'clicked');
            assert.equal(cancel.clicks, 1);
            assert.equal(stray.clicks, 0);
            assert.equal(call('cancel', []), 'clicked');
            assert.equal(cancel.clicks, 2);
        """)

    def test_cancel_atomic_reports_not_found_without_button(self):
        self.run_dom("""
            const footer = document.append(new Element('footer'));
            footer.append(new Element('button', {}, 'Guardar'));
            assert.equal(call('cancel', []), 'not_found');
        """)

    def test_selected_button_is_not_treated_as_an_option(self):
        self.run_dom("""
            const active = field('Cualificación', 'Rechazo argumentado', {expanded:false});
            active.control.attrs['data-value'] = 'Argued refusal';
            assert.equal(call('pick', 'Rechazo argumentado', labels), 'selected');
            assert.equal(active.control.clicks, 0);
        """)

    def test_options_count_and_scroll_do_not_use_other_dropdowns(self):
        self.run_dom("""
            const foreign = field('Otro campo', '--Ninguno--');
            foreign.option('Rechazo argumentado');
            field('Cualificación', '--Ninguno--', {expanded:false});
            assert.equal(call('count', labels), 0);
            assert.equal(call('pick', 'Rechazo argumentado', labels), 'not_found');
            assert.equal(foreign.list.scrollTop, 0);
        """)

    def test_both_subqualifications_support_input_values(self):
        self.run_dom("""
            field('Sub-Cualificación', 'Ilocalizable', {visible:false});
            const active = field('Sub-Cualificación', '--Ninguno--', {input:true});
            const right = active.option('Interesado en precio o condición');
            assert.equal(call('pick', 'Interesado en precio o condición', sublabels), 'clicked');
            assert.equal(right.clicks, 1);
            assert.equal(call('value', sublabels), 'interesado en precio o condicion');
            active.control.value = 'Ilocalizable';
            assert.equal(call('value', sublabels), 'ilocalizable');
        """)

    def test_ilocalizable_fallback_selects_permanece_when_primary_is_absent(self):
        self.run_dom("""
            const active = field('Sub-Cualificación', '--Ninguno--', {input:true});
            const fallback = active.option('Permanece ilocalizable');
            const other = active.option('Número falso');
            assert.equal(call('pick', ['Ilocalizable', 'Permanece ilocalizable'], sublabels), 'clicked');
            assert.equal(fallback.clicks, 1);
            assert.equal(other.clicks, 0);
            assert.equal(call('value', sublabels), 'permanece ilocalizable');
        """)

    def test_ilocalizable_primary_wins_when_both_options_exist(self):
        self.run_dom("""
            const active = field('Sub-Cualificación', '--Ninguno--', {input:true});
            const fallback = active.option('Permanece ilocalizable');
            const primary = active.option('Ilocalizable');
            assert.equal(call('pick', ['Ilocalizable', 'Permanece ilocalizable'], sublabels), 'clicked');
            assert.equal(primary.clicks, 1);
            assert.equal(fallback.clicks, 0);
            assert.equal(call('value', sublabels), 'ilocalizable');
        """)

    def test_ilocalizable_fallback_is_kept_only_without_primary(self):
        self.run_dom("""
            const active = field('Sub-Cualificación', 'Permanece ilocalizable', {input:true});
            const fallback = active.option('Permanece ilocalizable');
            assert.equal(call('pick', ['Ilocalizable', 'Permanece ilocalizable'], sublabels), 'selected');
            assert.equal(fallback.clicks, 0);
        """)

    def test_ilocalizable_primary_replaces_selected_fallback(self):
        self.run_dom("""
            const active = field('Sub-Cualificación', 'Permanece ilocalizable', {input:true});
            const fallback = active.option('Permanece ilocalizable');
            const primary = active.option('Ilocalizable');
            assert.equal(call('pick', ['Ilocalizable', 'Permanece ilocalizable'], sublabels), 'clicked');
            assert.equal(primary.clicks, 1);
            assert.equal(fallback.clicks, 0);
            assert.equal(call('value', sublabels), 'ilocalizable');
        """)

    def test_ilocalizable_missing_options_never_selects_approximate(self):
        self.run_dom("""
            const active = field('Sub-Cualificación', '--Ninguno--', {input:true});
            active.list.scrollHeight = 100;
            const other = active.option('Número falso');
            assert.equal(call('pick', ['Ilocalizable', 'Permanece ilocalizable'], sublabels), 'not_found');
            assert.equal(other.clicks, 0);
        """)

    def test_duplicate_visible_fields_fail_without_clicking(self):
        self.run_dom("""
            const first = field('Cualificación', '--Ninguno--');
            const second = field('Cualificación', '--Ninguno--');
            const one = first.option('Rechazo argumentado');
            const two = second.option('Rechazo argumentado');
            assert.throws(() => call('trigger', labels), /ambigu/i);
            assert.throws(() => call('value', labels), /ambigu/i);
            assert.throws(() => call('pick', 'Rechazo argumentado', labels), /ambigu/i);
            assert.equal(one.clicks + two.clicks, 0);
        """)

    def test_mexico_spaced_subqualification_uses_its_own_control(self):
        for label in ("Sub cualificación", "Sub cualificacion", "Sub-Cualificación"):
            with self.subTest(label=label):
                self.run_dom(
                    "const mexicoLabels = " + json.dumps(closure.SUBQUALIFICATION_FIELD_LABELS) + ";"
                    "const fieldLabel = "
                    + json.dumps(label)
                    + ";"
                    + """
                    const qualification = field('Cualificación', 'Rechazo no argumentado');
                    const wrong = qualification.option('Ilocalizable');
                    const active = field(fieldLabel, '--Ninguno--', {input:true});
                    const right = active.option('Ilocalizable');
                    assert.equal(call('trigger', mexicoLabels), active.control);
                    assert.equal(call('pick', ['Ilocalizable', 'Permanece ilocalizable'], mexicoLabels), 'clicked');
                    assert.equal(right.clicks, 1);
                    assert.equal(wrong.clicks, 0);
                    assert.equal(call('value', mexicoLabels), 'ilocalizable');
                    assert.equal(call('pick', ['Ilocalizable', 'Permanece ilocalizable'], mexicoLabels), 'selected');
                    assert.equal(right.clicks, 1);
                """
                )

    def test_disabled_control_is_not_clicked(self):
        self.run_dom("""
            const active = field('Cualificación', '--Ninguno--');
            active.control.attrs['aria-disabled'] = 'true';
            assert.equal(call('trigger', labels), null);
        """)

    def test_duplicate_options_fail_without_clicking(self):
        self.run_dom("""
            const active = field('Cualificación', '--Ninguno--');
            const one = active.option('Rechazo argumentado');
            const two = active.option('Rechazo argumentado');
            assert.equal(call('pick', 'Rechazo argumentado', labels), 'ambiguous');
            assert.equal(one.clicks + two.clicks, 0);
        """)

    def test_missing_owned_listbox_never_falls_back_to_another(self):
        self.run_dom("""
            const foreign = field('Otro campo', '--Ninguno--');
            const wrong = foreign.option('Rechazo argumentado');
            const active = field('Cualificación', '--Ninguno--');
            active.control.attrs['aria-controls'] = 'missing';
            assert.equal(call('pick', 'Rechazo argumentado', labels), 'not_found');
            assert.equal(wrong.clicks, 0);
        """)


class SubqualificationContractTests(unittest.TestCase):
    def test_persisted_fields_accept_approved_fallback(self):
        contract = closure.reason_contract("ilocalizable")

        def read_field(driver, labels):
            if labels == closure.SUBQUALIFICATION_FIELD_LABELS:
                return "Permanece ilocalizable"
            if labels == closure.COMMENT_FIELD_LABELS:
                return "Ilocalizable"
            if labels == closure.QUALIFICATION_FIELD_LABELS:
                return "Rechazo no argumentado"
            return ""

        with patch.object(closure, "find_field_text", side_effect=read_field):
            self.assertTrue(closure.verify_persisted_fields(Mock(), contract))

    def test_persisted_fields_reject_unapproved_subqualification(self):
        contract = closure.reason_contract("ilocalizable")

        def read_field(driver, labels):
            if labels == closure.SUBQUALIFICATION_FIELD_LABELS:
                return "Número falso"
            if labels == closure.COMMENT_FIELD_LABELS:
                return "Ilocalizable"
            if labels == closure.QUALIFICATION_FIELD_LABELS:
                return "Rechazo no argumentado"
            return ""

        with patch.object(closure, "find_field_text", side_effect=read_field):
            self.assertFalse(closure.verify_persisted_fields(Mock(), contract))

    def test_edit_form_accepts_approved_fallback(self):
        contract = closure.reason_contract("ilocalizable")
        values = Mock(side_effect=["permanece ilocalizable", "rechazo no argumentado"])
        with (
            patch.object(closure, "execute_in_any_frame", return_value="Ilocalizable"),
            patch.object(closure, "_picklist_current_value", values),
        ):
            self.assertTrue(closure.edit_form_matches(Mock(), contract))


class PicklistPollingTests(unittest.TestCase):
    def run_selection(self, values, atomic="clicked"):
        driver = Mock()
        clock = itertools.count(step=0.25)
        patches = {
            "execute_in_any_frame": Mock(return_value=atomic),
            "_picklist_current_value": values,
            "_open_options_count": Mock(return_value=0),
            "_execute_picklist_script": Mock(return_value="clicked"),
        }
        with (
            patch.multiple(closure, **patches),
            patch.object(closure.time, "monotonic", side_effect=lambda: next(clock)),
            patch.object(closure.time, "sleep"),
        ):
            selected = closure.select_picklist_option(
                driver, closure.QUALIFICATION_FIELD_LABELS, "Rechazo argumentado", 8
            )
        return driver, patches, selected

    def test_already_selected_does_not_reopen_or_click(self):
        driver, patches, _ = self.run_selection(Mock(return_value="rechazo argumentado"))
        driver.execute_script.assert_not_called()
        patches["execute_in_any_frame"].assert_not_called()
        patches["_execute_picklist_script"].assert_not_called()

    def test_selection_returns_after_exact_value_is_observed(self):
        driver, patches, _ = self.run_selection(Mock(side_effect=["--ninguno--", "rechazo argumentado"]))
        driver.execute_script.assert_not_called()
        patches["execute_in_any_frame"].assert_called_once_with(
            driver, closure.CLICK_PICKLIST_TRIGGER_ATOMIC_SCRIPT, list(closure.QUALIFICATION_FIELD_LABELS)
        )
        patches["_execute_picklist_script"].assert_called_once_with(
            driver, closure.PICK_OPTION_SCRIPT, closure.QUALIFICATION_FIELD_LABELS, "Rechazo argumentado"
        )

    def test_partial_label_does_not_pass_verification(self):
        with self.assertRaises(ValueError):
            self.run_selection(Mock(return_value="rechazo argumentado extra"))

    def test_selected_fallback_returns_without_option_click(self):
        driver = Mock()
        clock = itertools.count(step=0.25)
        with (
            patch.object(closure, "execute_in_any_frame", Mock(return_value="expanded")),
            patch.object(
                closure,
                "_picklist_current_value",
                Mock(side_effect=["permanece ilocalizable", "permanece ilocalizable"]),
            ),
            patch.object(closure, "_execute_picklist_script", Mock(return_value="selected")),
            patch.object(closure.time, "monotonic", side_effect=lambda: next(clock)),
            patch.object(closure.time, "sleep"),
        ):
            selected = closure.select_picklist_option(
                driver,
                closure.SUBQUALIFICATION_FIELD_LABELS,
                ("Ilocalizable", "Permanece ilocalizable"),
                8,
            )

        self.assertEqual(selected, "Permanece ilocalizable")
        driver.execute_script.assert_not_called()


class PicklistRetryTests(unittest.TestCase):
    def test_reopening_is_bounded_even_after_unverified_option_clicks(self):
        driver = Mock()
        clock = itertools.count(step=0.25)
        outcomes = itertools.cycle(["clicked", *(["not_found"] * 10)])
        atomic = Mock(return_value="clicked")
        with (
            patch.object(closure, "execute_in_any_frame", atomic),
            patch.object(closure, "_picklist_current_value", return_value="--ninguno--"),
            patch.object(closure, "_open_options_count", return_value=0),
            patch.object(closure, "_execute_picklist_script", side_effect=lambda *args: next(outcomes)),
            patch.object(closure.time, "monotonic", side_effect=lambda: next(clock)),
            patch.object(closure.time, "sleep"),
        ):
            with self.assertRaisesRegex(ValueError, "confirmar la opción exacta"):
                closure.select_picklist_option(driver, closure.QUALIFICATION_FIELD_LABELS, "Rechazo argumentado", 30)
        # Un clic del trigger al abrir + a lo sumo 3 reaperturas acotadas.
        self.assertEqual(atomic.call_count, 4)


class PicklistFrameTests(unittest.TestCase):
    """Los scripts del picklist delegan en el executor tolerante a frames:
    cada evaluación reubica el control dentro de su contexto, así ningún
    WebElement cruza evaluaciones ni frames (Edge 158 los invalida)."""

    def test_delegates_to_frame_tolerant_executor(self):
        driver = Mock()
        with patch.object(closure, "execute_in_any_frame", return_value="clicked") as run:
            outcome = closure._execute_picklist_script(
                driver, closure.PICK_OPTION_SCRIPT, closure.QUALIFICATION_FIELD_LABELS, "Rechazo argumentado"
            )

        self.assertEqual(outcome, "clicked")
        run.assert_called_once_with(
            driver, closure.PICK_OPTION_SCRIPT, "Rechazo argumentado", list(closure.QUALIFICATION_FIELD_LABELS)
        )

    def test_missing_control_returns_executor_result(self):
        driver = Mock()
        with patch.object(closure, "execute_in_any_frame", return_value="not_found") as run:
            outcome = closure._execute_picklist_script(
                driver, closure.PICK_OPTION_SCRIPT, closure.QUALIFICATION_FIELD_LABELS, "Rechazo argumentado"
            )

        self.assertEqual(outcome, "not_found")
        run.assert_called_once_with(
            driver, closure.PICK_OPTION_SCRIPT, "Rechazo argumentado", list(closure.QUALIFICATION_FIELD_LABELS)
        )


class SetComentarioTests(unittest.TestCase):
    """El Comentario se escribe con teclado confiable tras dejar que el
    formulario termine de inicializar: lo tipeado antes queda en pantalla
    pero fuera del borrador y Guardar no lo manda (verificado en red)."""

    def test_waits_for_form_settle_then_types_with_trusted_keyboard(self):
        driver = Mock()
        sleeps = []
        with (
            patch.object(closure, "type_editor_value", return_value="Ilocalizable") as typed,
            patch.object(closure.time, "sleep", side_effect=sleeps.append),
        ):
            closure.set_comentario(driver, "Ilocalizable", 10, settle_seconds=3.0)
        typed.assert_called_once_with(driver, closure.COMMENT_FIELD_LABELS, "Ilocalizable")
        self.assertEqual(sleeps[0], 3.0)

    def test_retries_typing_until_the_editor_shows_the_literal(self):
        driver = Mock()
        outcomes = iter(["", "Iloca", "Ilocalizable"])
        clock = itertools.count(step=0.1)
        with (
            patch.object(closure, "type_editor_value", side_effect=lambda *_a: next(outcomes)) as typed,
            patch.object(closure.time, "monotonic", side_effect=lambda: next(clock)),
            patch.object(closure.time, "sleep"),
        ):
            closure.set_comentario(driver, "Ilocalizable", 10, settle_seconds=0)
        self.assertEqual(typed.call_count, 3)

    def test_missing_editor_raises_specific_error(self):
        driver = Mock()
        clock = itertools.count(step=1.0)
        with (
            patch.object(closure, "type_editor_value", return_value="not_found"),
            patch.object(closure.time, "monotonic", side_effect=lambda: next(clock)),
            patch.object(closure.time, "sleep"),
            self.assertRaisesRegex(ValueError, "No se encontró el editor"),
        ):
            closure.set_comentario(driver, "Ilocalizable", 3, settle_seconds=0)

    def test_never_uses_the_synthetic_setter(self):
        self.assertNotIn("SET_EDITOR_VALUE_ATOMIC_SCRIPT", inspect.getsource(closure.set_comentario))


class OpenQualificationEditTests(unittest.TestCase):
    """La sección Cualificación renderiza después del panel de estado: el
    doble clic sondea hasta el timeout en vez de fallar al primer intento."""

    def run_open(self, outcomes, timeout=8):
        driver = Mock()
        clock = itertools.count(step=0.25)
        with (
            patch.object(closure, "execute_in_any_frame", side_effect=lambda *args: next(outcomes)),
            patch.object(closure.time, "monotonic", side_effect=lambda: next(clock)),
            patch.object(closure.time, "sleep"),
        ):
            return closure.open_qualification_edit(driver, timeout)

    def test_retries_dblclick_until_the_field_renders(self):
        outcomes = iter(["not_found", "not_found", "clicked", "found"])
        self.run_open(outcomes)  # el último 'found' cierra la espera del editor

    def test_gives_up_when_the_field_never_appears(self):
        outcomes = itertools.repeat("not_found")
        with self.assertRaisesRegex(ValueError, "No se encontró el campo Comentario"):
            self.run_open(outcomes, timeout=8)

    def test_ambiguous_still_raises_immediately(self):
        outcomes = iter(["ambiguous"])
        with self.assertRaisesRegex(ValueError, "ambiguo"):
            self.run_open(outcomes)


class DiscardEditFormTests(unittest.TestCase):
    def test_clicks_cancel_and_restores_default_content(self):
        driver = Mock()
        with (
            patch.object(closure, "execute_in_any_frame", return_value="clicked") as run,
            patch.object(closure.time, "sleep") as sleep,
        ):
            closure.discard_open_edit_form(driver)

        run.assert_called_once_with(driver, closure.CLICK_CANCEL_EDIT_ATOMIC_SCRIPT)
        sleep.assert_called_once()
        driver.switch_to.default_content.assert_called()

    def test_missing_cancel_button_is_a_noop(self):
        driver = Mock()
        with (
            patch.object(closure, "execute_in_any_frame", return_value="not_found"),
            patch.object(closure.time, "sleep") as sleep,
        ):
            closure.discard_open_edit_form(driver)

        sleep.assert_not_called()
        driver.switch_to.default_content.assert_called()

    def test_driver_errors_are_swallowed(self):
        driver = Mock()
        driver.switch_to.default_content.side_effect = WebDriverException("frame dead")
        with patch.object(closure, "execute_in_any_frame", side_effect=WebDriverException("dead")):
            closure.discard_open_edit_form(driver)


if __name__ == "__main__":
    unittest.main()
