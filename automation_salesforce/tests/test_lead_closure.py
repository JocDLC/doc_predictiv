import itertools
import json
import subprocess
import unittest
from unittest.mock import Mock, patch

import comment_reader
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
}
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
            "const mexicoLabels = " + json.dumps(closure.SUBQUALIFICATION_FIELD_LABELS) + ";" + """
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
class PicklistDomTests(unittest.TestCase):
    def run_dom(self, scenario):
        scripts = {
            "trigger": closure.PICKLIST_TRIGGER_SCRIPT,
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
                    "const fieldLabel = " + json.dumps(label) + ";" + """
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
        editor = Mock()
        editor.get_attribute.return_value = "Ilocalizable"
        values = Mock(side_effect=["permanece ilocalizable", "rechazo no argumentado"])
        with (
            patch.object(closure, "find_element_in_any_frame", return_value=editor),
            patch.object(closure, "_picklist_current_value", values),
        ):
            self.assertTrue(closure.edit_form_matches(Mock(), contract))


class PicklistPollingTests(unittest.TestCase):
    def run_selection(self, values):
        driver = Mock()
        trigger = Mock()
        trigger.get_attribute.return_value = "false"
        clock = itertools.count(step=0.25)
        patches = {
            "_picklist_trigger": Mock(return_value=trigger),
            "_picklist_current_value": values,
            "_open_options_count": Mock(return_value=0),
            "_execute_picklist_script": Mock(return_value="clicked"),
        }
        with (
            patch.multiple(closure, **patches),
            patch.object(closure.time, "monotonic", side_effect=lambda: next(clock)),
            patch.object(closure.time, "sleep"),
        ):
            closure.select_picklist_option(driver, closure.QUALIFICATION_FIELD_LABELS, "Rechazo argumentado", 8)
        return driver, patches

    def test_already_selected_does_not_reopen_or_click(self):
        driver, patches = self.run_selection(Mock(return_value="rechazo argumentado"))
        driver.execute_script.assert_not_called()
        patches["_execute_picklist_script"].assert_not_called()

    def test_selection_returns_after_exact_value_is_observed(self):
        driver, patches = self.run_selection(Mock(side_effect=["--ninguno--", "rechazo argumentado"]))
        self.assertEqual(driver.execute_script.call_count, 1)
        patches["_execute_picklist_script"].assert_called_once_with(
            driver, closure.PICK_OPTION_SCRIPT, closure.QUALIFICATION_FIELD_LABELS, "Rechazo argumentado"
        )

    def test_partial_label_does_not_pass_verification(self):
        with self.assertRaises(ValueError):
            self.run_selection(Mock(return_value="rechazo argumentado extra"))

    def test_selected_fallback_returns_without_option_click(self):
        driver, trigger = Mock(), Mock()
        trigger.get_attribute.return_value = "true"
        clock = itertools.count(step=0.25)
        with (
            patch.object(closure, "_picklist_trigger", return_value=trigger),
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
        driver, trigger = Mock(), Mock()
        trigger.get_attribute.return_value = "false"
        clock = itertools.count(step=0.25)
        outcomes = itertools.cycle(["clicked", *(["not_found"] * 10)])
        with (
            patch.object(closure, "_picklist_trigger", return_value=trigger),
            patch.object(closure, "_picklist_current_value", return_value="--ninguno--"),
            patch.object(closure, "_open_options_count", return_value=0),
            patch.object(closure, "_execute_picklist_script", side_effect=lambda *args: next(outcomes)),
            patch.object(closure.time, "monotonic", side_effect=lambda: next(clock)),
            patch.object(closure.time, "sleep"),
        ):
            with self.assertRaisesRegex(ValueError, "confirmar la opción exacta"):
                closure.select_picklist_option(driver, closure.QUALIFICATION_FIELD_LABELS, "Rechazo argumentado", 30)
        self.assertEqual(driver.execute_script.call_count, 4)


class PicklistFrameTests(unittest.TestCase):
    def test_hidden_frame_is_skipped_and_selection_executes_once(self):
        driver = Mock()
        hidden, active, unrelated = Mock(), Mock(), Mock()
        hidden.is_displayed.return_value = False
        active.is_displayed.return_value = True
        driver.find_elements.return_value = [hidden, active, unrelated]
        driver.execute_script.side_effect = [None, Mock(), "clicked"]

        outcome = closure._execute_picklist_script(
            driver, closure.PICK_OPTION_SCRIPT, closure.QUALIFICATION_FIELD_LABELS, "Rechazo argumentado"
        )

        self.assertEqual(outcome, "clicked")
        driver.switch_to.frame.assert_called_once_with(active)
        self.assertEqual(driver.execute_script.call_count, 3)
        driver.execute_script.assert_called_with(
            closure.PICK_OPTION_SCRIPT, "Rechazo argumentado", list(closure.QUALIFICATION_FIELD_LABELS)
        )
        unrelated.is_displayed.assert_not_called()
        self.assertEqual(driver.switch_to.default_content.call_count, 2)

    def test_no_visible_control_never_runs_option_script(self):
        driver = Mock()
        driver.find_elements.return_value = []
        driver.execute_script.return_value = None
        self.assertIsNone(
            closure._execute_picklist_script(
                driver, closure.PICK_OPTION_SCRIPT, closure.QUALIFICATION_FIELD_LABELS, "Rechazo argumentado"
            )
        )
        driver.execute_script.assert_called_once_with(
            closure.PICKLIST_TRIGGER_SCRIPT, list(closure.QUALIFICATION_FIELD_LABELS)
        )


if __name__ == "__main__":
    unittest.main()
