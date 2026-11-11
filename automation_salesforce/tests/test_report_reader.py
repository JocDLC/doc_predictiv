import unittest

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from report_reader import (
    HEADER_FALLBACK_SELECTOR,
    REPORT_CANDIDATE_SELECTOR,
    ReportEmptyError,
    VisibleLead,
    aligned_values,
    clean_header_text,
    column_offset,
    deduplicate_visible_leads,
    extract_created_at,
    extract_lead_id,
    extract_row_details,
    find_header_index,
    find_owner_header_index,
    find_report_rows,
    find_report_table,
    header_labels,
    is_unassigned_owner,
    is_visible_element,
    merge_visible_leads,
    read_full_report,
    read_report_horizontal,
    read_visible_unassigned_leads,
    report_accessibility_summary,
    report_structure_summary,
    resolve_field_indexes,
    row_diagnostics,
    row_has_unassigned_owner,
    row_values,
    select_report_table,
)


class FakeCell:
    def __init__(self, text: str):
        self.text = text


class FakeTable:
    tag_name = "table"

    def __init__(self, headers, row_count, role="grid"):
        self.headers = [FakeCell(header) for header in headers]
        self.rows = [FakeRow() for _ in range(row_count)]
        self.role_rows = self.rows
        self.role = role

    def find_elements(self, by, selector):
        if selector == "thead th, [role='columnheader']":
            return self.headers
        if selector == "tbody tr, [role='row']":
            return self.rows
        if selector == "tbody tr":
            return self.rows
        if selector == "[role='row']":
            return self.role_rows
        return []

    def get_attribute(self, name):
        return self.role if name == "role" else ""


class FakeDriver:
    def __init__(self, tables):
        self.tables = tables

    def find_elements(self, by, selector):
        if selector == REPORT_CANDIDATE_SELECTOR:
            return self.tables
        return []


class FakeFrame:
    def __init__(self, index):
        self.index = index


class FakeSwitchTo:
    def __init__(self, driver):
        self.driver = driver

    def default_content(self):
        self.driver.context = "main"

    def frame(self, frame):
        self.driver.context = frame.index


class FakeFrameDriver:
    def __init__(self, main_tables, frame_tables):
        self.main_tables = main_tables
        self.frame_tables = frame_tables
        self.frames = [FakeFrame(index) for index in range(len(frame_tables))]
        self.context = "main"
        self.switch_to = FakeSwitchTo(self)
        self.document_headers = []

    def find_elements(self, by, selector):
        if selector == "iframe, frame":
            return self.frames if self.context == "main" else []
        if selector == REPORT_CANDIDATE_SELECTOR:
            if self.context == "main":
                return self.main_tables
            return self.frame_tables[self.context]
        if selector == "thead th, [role='columnheader']":
            return self.document_headers if self.context != "main" else []
        return []


class FakeHorizontalTable:
    tag_name = "table"

    def __init__(self, driver, passes):
        self.driver = driver
        self.passes = passes

    def find_elements(self, by, selector):
        current = self.passes[self.driver.horizontal_pass]
        if selector in {"thead th, [role='columnheader']", "tr:first-of-type th, tr:first-child th"}:
            return [FakeCell(header) for header in current["headers"]]
        if selector in {"tbody tr, [role='row']", "tbody tr", "[role='row']"}:
            return current["rows"]
        return []

    def get_attribute(self, name):
        return "grid" if name == "role" else ""


class FakeHorizontalDriver:
    def __init__(self, passes):
        self.horizontal_pass = 0
        self.passes = passes
        self.table = FakeHorizontalTable(self, passes)
        self.switch_to = FakeSwitchTo(self)
        self.context = "main"

    def find_elements(self, by, selector):
        if selector == "iframe, frame":
            return []
        if selector == REPORT_CANDIDATE_SELECTOR:
            return [self.table]
        return []

    def execute_script(self, script, *args):
        if len(args) == 2 and isinstance(args[1], bool):
            reset = args[1]
            if reset:
                self.horizontal_pass = 0
                return {"moved": False}
            if self.horizontal_pass + 1 < len(self.passes):
                self.horizontal_pass += 1
                return {"moved": True}
            return {"moved": False}
        if len(args) == 2 and isinstance(args[1], str):
            root, selector = args
            return (root or self).find_elements(By.CSS_SELECTOR, selector)
        return {"moved": False}


class FakeLink:
    def __init__(self, href: str):
        self.href = href

    def get_attribute(self, name: str) -> str:
        if name != "href":
            return ""
        return self.href


class FakeAttributeElement:
    def __init__(self, attributes=None):
        self.attributes = attributes or {}

    def get_attribute(self, name: str) -> str:
        return self.attributes.get(name, "")


class FakeRow:
    def __init__(self, cells=None, links=None, displayed=True, attributes=None, descendants=None):
        self.cells = cells or []
        self.links = links or []
        self.displayed = displayed
        self.attributes = attributes or {}
        self.descendants = descendants or []
        self.text = "\n".join(cell.text for cell in self.cells)
        self.requests = []

    def is_displayed(self):
        return self.displayed

    def find_elements(self, by, selector):
        self.requests.append((by, selector))
        if selector == "th[scope='row'], td, [role='gridcell']":
            return self.cells
        if selector == "a[href]":
            return self.links
        if "data-recordid" in selector:
            return self.descendants
        return []

    def get_attribute(self, name):
        return self.attributes.get(name, "")


class ReportReaderTests(unittest.TestCase):
    def test_find_header_index_normalizes_headers_and_expected_label(self):
        headers = ["Fecha de creación", "  PROPIETARIO   DEL CANDIDATO  "]

        index = find_header_index(headers, "Propietario del Candidato")

        self.assertEqual(index, 1)
        self.assertIsNone(find_header_index(headers, "Lead ID"))

    def test_owner_header_accepts_short_lightning_label(self):
        self.assertEqual(find_owner_header_index(["Propietario"]), 0)

    def test_is_unassigned_owner_requires_exact_value_after_trimming(self):
        self.assertTrue(is_unassigned_owner("AR_LEAD_QUALIF"))
        self.assertTrue(is_unassigned_owner("  AR_LEAD_QUALIF  "))
        self.assertFalse(is_unassigned_owner("AR_LEAD_QUALIF_2"))

    def test_is_unassigned_owner_accepts_lightning_line_wrapping_only(self):
        self.assertTrue(is_unassigned_owner("AR_LEAD_QU\nALIF"))
        self.assertFalse(is_unassigned_owner("AR_LEAD_QU\nALIF_2"))

    def test_hidden_dom_row_is_not_considered_visible(self):
        self.assertTrue(is_visible_element(FakeRow(displayed=True)))
        self.assertFalse(is_visible_element(FakeRow(displayed=False)))

    def test_row_owner_fallback_requires_an_exact_line(self):
        self.assertTrue(row_has_unassigned_owner([], "Lead\nAR_LEAD_QUALIF\nHoy"))
        self.assertFalse(row_has_unassigned_owner([], "Lead\nAR_LEAD_QUALIF_2\nHoy"))

    def test_select_report_table_uses_largest_grid_without_headers(self):
        small_table = FakeTable([], row_count=1)
        report_table = FakeTable([], row_count=29)
        driver = FakeDriver([small_table, report_table])

        selected = select_report_table(driver, require_owner_header=False)

        self.assertIs(selected, report_table)

    def test_select_report_table_prefers_data_grid_over_index_grid_on_row_tie(self):
        # La bandeja real de Lightning dibuja dos grillas con la misma cantidad
        # de filas: una solo con la columna "#" y otra con las 15+ celdas de
        # datos. Empatadas en filas, gana la más densa.
        index_table = FakeTable([], row_count=0)
        index_table.rows = [FakeRow(cells=[FakeCell(str(i))]) for i in range(18)]
        index_table.role_rows = index_table.rows
        data_table = FakeTable([], row_count=0)
        data_table.rows = [FakeRow(cells=[FakeCell("x") for _ in range(15)]) for _ in range(18)]
        data_table.role_rows = data_table.rows
        driver = FakeDriver([index_table, data_table])

        selected = select_report_table(driver, require_owner_header=False)

        self.assertIs(selected, data_table)

    def test_header_labels_fallback_selector_and_menu_text_cleanup(self):
        # Lightning pone los th en la primera fila (sin thead) y concatena el
        # rótulo del menú "Acciones de columna" al texto del encabezado.
        headers = [FakeCell("CampañaAcciones de columna"), FakeCell("Propietario del candidatoAcciones de columna")]
        table = FakeTable([], row_count=0)
        table.find_elements = lambda _by, selector: headers if selector == HEADER_FALLBACK_SELECTOR else []

        self.assertEqual(header_labels(table), ["Campaña", "Propietario del candidato"])

    def test_clean_header_text_keeps_plain_labels(self):
        self.assertEqual(clean_header_text("Lead IDAcciones de columna"), "Lead ID")
        self.assertEqual(clean_header_text("Lead ID"), "Lead ID")
        self.assertEqual(clean_header_text("Contexto  Acciones de col"), "Contexto")

    def test_find_header_index_accepts_lightning_prefix_labels(self):
        headers = ["Fecha de creación por el cliente", "Nombre corto de la Concesionaria"]

        self.assertEqual(find_header_index(headers, "Fecha de creación"), 0)
        self.assertEqual(find_header_index(headers, "Nombre corto"), 1)
        self.assertIsNone(find_header_index(headers, "Campaña"))

    def test_find_header_index_prefix_needs_minimum_length(self):
        self.assertIsNone(find_header_index(["Estado de candidato"], "Es"))
        self.assertIsNone(find_header_index(["Nombre"], "Nombre corto concesionario"))

    def test_find_report_rows_prefers_html_rows_over_aria_containers(self):
        first_row = FakeRow()
        second_row = FakeRow()
        table = FakeTable([], row_count=0)
        table.rows = [first_row, second_row]
        table.role_rows = [FakeRow(), first_row, second_row]
        driver = FakeDriver([table])

        rows = find_report_rows(driver, table)

        self.assertEqual(rows, [first_row, second_row])

    def test_find_report_table_switches_to_frame_and_selects_largest_grid(self):
        empty_main_table = FakeTable([], row_count=0, role="treegrid")
        auxiliary_grid = FakeTable([], row_count=1)
        report_grid = FakeTable([], row_count=29)
        driver = FakeFrameDriver(
            main_tables=[empty_main_table],
            frame_tables=[[auxiliary_grid, report_grid]],
        )

        selected = find_report_table(driver, timeout_seconds=1)

        self.assertIs(selected, report_grid)
        self.assertEqual(driver.context, 0)

    def test_row_values_reads_td_and_gridcell_selector(self):
        row = FakeRow(cells=[FakeCell("  Lead  "), FakeCell(" AR_LEAD_QUALIF ")])

        values = row_values(row)

        self.assertEqual(values, ["Lead", "AR_LEAD_QUALIF"])
        self.assertEqual(
            row.requests,
            [(By.CSS_SELECTOR, "th[scope='row'], td, [role='gridcell']")],
        )

    def test_extract_created_at_uses_header_then_visible_date_value(self):
        values = ["Nombre", "07/09/2026 10:30", "AR_LEAD_QUALIF"]

        self.assertEqual(extract_created_at(values, date_index=1), "07/09/2026 10:30")
        self.assertEqual(extract_created_at(values, date_index=None), "07/09/2026")
        self.assertEqual(extract_created_at(["Nombre", "Sin fecha"], date_index=None), "")

    def test_extract_lead_id_handles_valid_invalid_and_missing_links(self):
        valid_row = FakeRow(
            links=[
                FakeLink("https://example.invalid/lightning/r/Group/00G000000000001AAA/view"),
                FakeLink("https://example.invalid/lightning/r/Lead/a1B000000000001AAA/view"),
            ]
        )
        invalid_row = FakeRow(links=[FakeLink("https://example.invalid/lightning/r/Lead/not-a-salesforce-id/view")])
        no_link_row = FakeRow()
        data_attribute_row = FakeRow(attributes={"data-recordid": "a1B000000000002AAA"})

        self.assertEqual(extract_lead_id(valid_row), "a1B000000000001AAA")
        self.assertEqual(extract_lead_id(invalid_row), "")
        self.assertEqual(extract_lead_id(no_link_row), "")
        self.assertEqual(extract_lead_id(data_attribute_row), "a1B000000000002AAA")

    def test_extract_lead_id_supports_configurable_salesforce_object(self):
        row = FakeRow(links=[FakeLink("https://example.invalid/lightning/r/Prospecto__c/a1B000000000003AAA/view")])

        lead_id = extract_lead_id(row, record_object_api_name="Prospecto__c")

        self.assertEqual(lead_id, "a1B000000000003AAA")

    def test_extract_lead_id_reads_descendant_record_attributes(self):
        other_object = FakeAttributeElement(
            {
                "href": "https://example.invalid/lightning/r/Group/00G000000000001AAA/view",
                "data-recordid": "00G000000000001AAA",
            }
        )
        lead = FakeAttributeElement({"data-record-id": "00Q000000000004AAA"})

        self.assertEqual(
            extract_lead_id(FakeRow(descendants=[other_object, lead])),
            "00Q000000000004AAA",
        )
        self.assertEqual(extract_lead_id(FakeRow(descendants=[other_object])), "")

    def test_deduplicate_visible_leads_uses_salesforce_lead_id(self):
        first_lead = VisibleLead("00Q000000000001AAA", "2026-09-09")
        duplicate_dom_row = VisibleLead("00Q000000000001AAA", "2026-09-09")
        second_lead = VisibleLead("00Q000000000002AAA", "2026-09-09")

        unique_leads = deduplicate_visible_leads([first_lead, duplicate_dom_row, second_lead])

        self.assertEqual(unique_leads, [first_lead, second_lead])

    def test_reader_includes_date_position_and_status_in_local_report_data(self):
        other_owner_row = FakeRow(cells=[FakeCell("2026-09-01"), FakeCell("OTRO_PROPIETARIO")])
        qualifying_row = FakeRow(
            cells=[FakeCell("2026-09-02"), FakeCell("AR_LEAD_QUALIF")],
            links=[FakeLink("https://example.invalid/lightning/r/Lead/00Q000000000001AAA/view")],
        )
        report_table = FakeTable(["Fecha de creación", "Propietario"], row_count=0)
        report_table.rows = [other_owner_row, qualifying_row]
        report_table.role_rows = report_table.rows
        driver = FakeFrameDriver(main_tables=[], frame_tables=[[report_table]])

        visible_row_count, leads = read_visible_unassigned_leads(driver, timeout_seconds=1)

        self.assertEqual(visible_row_count, 2)
        self.assertEqual(
            leads,
            [
                VisibleLead(
                    lead_id="00Q000000000001AAA",
                    created_at="2026-09-02",
                    grid_position=2,
                    status="SIN_GESTION",
                )
            ],
        )

    def test_reader_finds_owner_when_lightning_cells_are_not_header_aligned(self):
        qualifying_row = FakeRow(
            cells=[FakeCell("2026-09-02"), FakeCell("AR_LEAD_QUALIF")],
            links=[FakeLink("https://example.invalid/lightning/r/Lead/00Q000000000003AAA/view")],
        )
        report_table = FakeTable(["Propietario", "Fecha de creación"], row_count=0)
        report_table.rows = [qualifying_row]
        report_table.role_rows = report_table.rows
        driver = FakeFrameDriver(main_tables=[], frame_tables=[[report_table]])

        _, leads = read_visible_unassigned_leads(driver, timeout_seconds=1)

        self.assertEqual([lead.lead_id for lead in leads], ["00Q000000000003AAA"])

    def test_reader_uses_lead_id_column_when_row_has_no_record_link(self):
        qualifying_row = FakeRow(cells=[FakeCell("AR_LEAD_QU\nALIF"), FakeCell("00QbD00000000004AA")])
        report_table = FakeTable(["Propietario del candidato", "Lead ID"], row_count=0)
        report_table.rows = [qualifying_row]
        report_table.role_rows = report_table.rows
        driver = FakeFrameDriver(main_tables=[], frame_tables=[[report_table]])

        _, leads = read_visible_unassigned_leads(driver, timeout_seconds=1, field_aliases={"lead_id": ["Lead ID"]})

        self.assertEqual([lead.lead_id for lead in leads], ["00QbD00000000004AA"])

    def test_row_diagnostics_contain_only_structural_metadata(self):
        row = FakeRow(cells=[FakeCell("AR_LEAD_QUALIF"), FakeCell("Dato personal")])

        diagnostics = row_diagnostics(row, owner_found=True, lead_id_found=False)

        self.assertEqual(
            diagnostics,
            {"cell_count": 2, "text_length": 28, "owner_found": True, "lead_id_found": False},
        )
        self.assertNotIn("Dato personal", str(diagnostics))

    def test_column_offset_aligns_values_using_owner_cell_position(self):
        headers = ["Fecha de creación", "Campaña", "Propietario del candidato", "Nombre"]
        values = ["1", "15/09/2026", "Campaña X", "AR_LEAD_QUALIF", "Ana"]

        self.assertEqual(column_offset(headers, values), 1)
        self.assertEqual(
            aligned_values(values, column_offset(headers, values), len(headers)),
            ["15/09/2026", "Campaña X", "AR_LEAD_QUALIF", "Ana"],
        )

    def test_reader_extracts_details_when_headers_live_outside_the_grid(self):
        row = FakeRow(
            cells=[
                FakeCell("1"),
                FakeCell("15/09/2026"),
                FakeCell("Campaña X"),
                FakeCell("AR_LEAD_QU\nALIF"),
                FakeCell("Ana"),
                FakeCell("00QbD00000000004AA"),
            ]
        )
        table = FakeTable([], row_count=0)
        table.rows = [row]
        table.role_rows = table.rows
        driver = FakeFrameDriver(main_tables=[], frame_tables=[[table]])
        driver.document_headers = [
            FakeCell("Fecha de creación"),
            FakeCell("Campaña"),
            FakeCell("Propietario del candidato"),
            FakeCell("Nombre"),
            FakeCell("Lead ID"),
        ]

        _, leads = read_visible_unassigned_leads(
            driver,
            timeout_seconds=1,
            field_aliases={"campana": ["Campaña"], "nombre": ["Nombre"], "lead_id": ["Lead ID"]},
        )

        self.assertEqual(leads[0].details["campana"], "Campaña X")
        self.assertEqual(leads[0].details["nombre"], "Ana")
        self.assertEqual(leads[0].lead_id, "00QbD00000000004AA")
        self.assertEqual(leads[0].details["col:Fecha de creación"], "15/09/2026")
        self.assertNotIn("col:Campaña", leads[0].details)

    def test_merge_visible_leads_combines_columns_from_horizontal_passes(self):
        leads = merge_visible_leads(
            [
                VisibleLead("00Q000000000001AAA", "15/09/2026", details={"campana": "A"}),
                VisibleLead("00Q000000000001AAA", "15/09/2026", details={"email": "a@example.invalid"}),
            ]
        )

        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0].details, {"campana": "A", "email": "a@example.invalid"})

    def test_horizontal_scan_merges_stable_row_fragments(self):
        row_key = {"aria-rowindex": "2"}
        driver = FakeHorizontalDriver(
            [
                {
                    "headers": ["Propietario del candidato"],
                    "rows": [FakeRow(cells=[FakeCell("AR_LEAD_QUALIF")], attributes=row_key)],
                },
                {
                    "headers": ["Lead ID"],
                    "rows": [FakeRow(cells=[FakeCell("00Q000000000005AAA")], attributes=row_key)],
                },
            ]
        )

        visible_rows, leads = read_full_report(
            driver,
            timeout_seconds=1,
            record_object_api_name="Lead",
            field_aliases={"lead_id": ["Lead ID"]},
            diagnostics=[],
            max_vertical_passes=1,
        )

        self.assertEqual(visible_rows, 1)
        self.assertEqual([lead.lead_id for lead in leads], ["00Q000000000005AAA"])

    def test_horizontal_reader_merges_fragments_and_restores_scroll(self):
        """El barrido del Monitor une propietario e ID de pasadas distintas
        con la misma clave y deja la grilla de vuelta a la izquierda."""
        row_key = {"aria-rowindex": "2"}
        driver = FakeHorizontalDriver(
            [
                {
                    "headers": ["Propietario del candidato"],
                    "rows": [FakeRow(cells=[FakeCell("AR_LEAD_QUALIF")], attributes=row_key)],
                },
                {
                    "headers": ["Lead ID"],
                    "rows": [FakeRow(cells=[FakeCell("00Q000000000005AAA")], attributes=row_key)],
                },
            ]
        )
        diagnostics = []

        visible_rows, leads = read_report_horizontal(
            driver,
            timeout_seconds=1,
            record_object_api_name="Lead",
            field_aliases={"lead_id": ["Lead ID"]},
            diagnostics=diagnostics,
        )

        self.assertEqual(visible_rows, 1)
        self.assertEqual([lead.lead_id for lead in leads], ["00Q000000000005AAA"])
        self.assertEqual(driver.horizontal_pass, 0)
        summary = diagnostics[-1]
        self.assertEqual(summary["horizontal_passes"], 2)
        self.assertEqual(summary["owner_without_id"], 0)
        self.assertEqual(summary["unstable_or_ambiguous_rows"], 0)

    def test_horizontal_reader_counts_qualif_without_id(self):
        """Una fila QUALIF sin identidad resoluble no produce Lead y queda
        contada para el log — el caso '0 sin asignar con QUALIF a la vista'."""
        driver = FakeHorizontalDriver(
            [
                {
                    "headers": ["Propietario del candidato"],
                    "rows": [FakeRow(cells=[FakeCell("AR_LEAD_QUALIF")])],
                },
            ]
        )
        diagnostics = []

        _, leads = read_report_horizontal(
            driver,
            timeout_seconds=1,
            record_object_api_name="Lead",
            field_aliases={"lead_id": ["Lead ID"]},
            diagnostics=diagnostics,
        )

        self.assertEqual(leads, [])
        self.assertEqual(diagnostics[-1]["owner_without_id"], 1)
        self.assertEqual(diagnostics[-1]["horizontal_passes"], 1)

    def test_horizontal_scan_rejects_fragments_without_stable_key(self):
        driver = FakeHorizontalDriver(
            [
                {
                    "headers": ["Propietario del candidato"],
                    "rows": [FakeRow(cells=[FakeCell("AR_LEAD_QUALIF")])],
                },
                {
                    "headers": ["Lead ID"],
                    "rows": [FakeRow(cells=[FakeCell("00Q000000000006AAA")])],
                },
            ]
        )
        diagnostics = []

        _, leads = read_full_report(
            driver,
            timeout_seconds=1,
            record_object_api_name="Lead",
            field_aliases={"lead_id": ["Lead ID"]},
            diagnostics=diagnostics,
            max_vertical_passes=1,
        )

        self.assertEqual(leads, [])
        self.assertGreater(sum(item.get("unstable_or_ambiguous_rows", 0) for item in diagnostics), 0)

    def test_horizontal_scan_rejects_duplicate_row_keys(self):
        duplicate_key = {"aria-rowindex": "2"}
        driver = FakeHorizontalDriver(
            [
                {
                    "headers": ["Propietario del candidato"],
                    "rows": [
                        FakeRow(cells=[FakeCell("AR_LEAD_QUALIF")], attributes=duplicate_key),
                        FakeRow(cells=[FakeCell("AR_LEAD_QUALIF")], attributes=duplicate_key),
                    ],
                },
                {
                    "headers": ["Lead ID"],
                    "rows": [
                        FakeRow(cells=[FakeCell("00Q000000000007AAA")], attributes=duplicate_key),
                        FakeRow(cells=[FakeCell("00Q000000000008AAA")], attributes=duplicate_key),
                    ],
                },
            ]
        )
        diagnostics = []

        _, leads = read_full_report(
            driver,
            timeout_seconds=1,
            record_object_api_name="Lead",
            field_aliases={"lead_id": ["Lead ID"]},
            diagnostics=diagnostics,
            max_vertical_passes=1,
        )

        self.assertEqual(leads, [])
        self.assertGreaterEqual(sum(item.get("unstable_or_ambiguous_rows", 0) for item in diagnostics), 2)

    def test_horizontal_scan_rejects_changed_row_sequence(self):
        row_2 = {"aria-rowindex": "2"}
        row_3 = {"aria-rowindex": "3"}
        driver = FakeHorizontalDriver(
            [
                {
                    "headers": ["Propietario del candidato"],
                    "rows": [
                        FakeRow(cells=[FakeCell("AR_LEAD_QUALIF")], attributes=row_2),
                        FakeRow(cells=[FakeCell("AR_LEAD_QUALIF")], attributes=row_3),
                    ],
                },
                {
                    "headers": ["Lead ID"],
                    "rows": [
                        FakeRow(cells=[FakeCell("00Q000000000009AAA")], attributes=row_3),
                        FakeRow(cells=[FakeCell("00Q000000000010AAA")], attributes=row_2),
                    ],
                },
            ]
        )
        diagnostics = []

        _, leads = read_full_report(
            driver,
            timeout_seconds=1,
            record_object_api_name="Lead",
            field_aliases={"lead_id": ["Lead ID"]},
            diagnostics=diagnostics,
            max_vertical_passes=1,
        )

        self.assertEqual(leads, [])
        self.assertGreaterEqual(sum(item.get("unstable_or_ambiguous_rows", 0) for item in diagnostics), 2)

    def test_report_structure_summary_excludes_header_text_and_row_values(self):
        driver = FakeDriver([FakeTable(["Propietario", "Dato interno"], row_count=4)])

        summary = report_structure_summary(driver)

        self.assertEqual(
            summary,
            [
                {
                    "tag": "table",
                    "role": "grid",
                    "header_count": 2,
                    "owner_header_found": True,
                    "row_count": 4,
                    "rows_with_cells": 0,
                    "max_cell_count": 0,
                }
            ],
        )
        self.assertNotIn("Dato interno", str(summary))

    def test_accessibility_summary_has_only_structural_metadata(self):
        driver = FakeDriver([FakeTable(["Propietario", "Dato interno"], row_count=4)])

        summary = report_accessibility_summary(driver)

        self.assertEqual(summary["frame_count"], 0)
        self.assertEqual(summary["frames"], [])
        self.assertEqual(summary["main_structure"][0]["header_count"], 2)
        self.assertNotIn("Dato interno", str(summary))

    def test_resolves_configured_aliases_and_marks_absent_columns_empty(self):
        indexes = resolve_field_indexes(
            ["Nombre", "Correo electrónico", "Propietario"],
            {
                "nombre": ["First Name", "Nombre"],
                "email": ["Email", "Correo electrónico"],
                "vehiculo_interes": ["Vehículo de interés"],
            },
        )

        self.assertEqual(indexes, {"nombre": 0, "email": 1, "vehiculo_interes": None})
        self.assertEqual(
            extract_row_details(["Ana", "ana@example.invalid", "AR_LEAD_QUALIF"], indexes),
            {"nombre": "Ana", "email": "ana@example.invalid", "vehiculo_interes": ""},
        )

    def test_find_report_table_raises_empty_error_on_sin_resultados(self):
        """El visor del reporte carga dentro de un iframe: "Sin resultados"
        ahí corta la espera en vez de quemar el timeout buscando la grilla."""
        driver = FakeEmptyReportDriver({0: "Sin resultados\nNo se devolvió ningún registro"})

        with self.assertRaises(ReportEmptyError):
            find_report_table(driver, timeout_seconds=2)

    def test_find_report_table_also_detects_english_no_results(self):
        driver = FakeEmptyReportDriver({"main": "No results found"})

        with self.assertRaises(ReportEmptyError):
            find_report_table(driver, timeout_seconds=2)

    def test_read_visible_unassigned_leads_returns_empty_on_empty_report(self):
        """Reporte cargado sin registros = bandeja vacía, no un error de bandeja."""
        driver = FakeEmptyReportDriver({0: "Total de registros 0\nSin resultados\nNo se devolvió ningún registro"})

        visible_rows, leads = read_visible_unassigned_leads(driver, timeout_seconds=2)

        self.assertEqual(visible_rows, 0)
        self.assertEqual(leads, [])

    def test_find_report_table_still_times_out_without_empty_marker(self):
        """Sin tabla ni texto "sin resultados" el comportamiento se mantiene:
        esperar al timeout (reporte pesado aún cargando)."""
        driver = FakeEmptyReportDriver({"main": "Cargando informe..."})

        with self.assertRaises(TimeoutException):
            find_report_table(driver, timeout_seconds=0.3)


class FakeEmptyReportDriver:
    """Driver con iframes cuyo contenido textual simula el visor de reportes."""

    def __init__(self, body_texts):
        self.body_texts = body_texts
        self.frames = [FakeFrame(index) for index in body_texts if index != "main"]
        self.context = "main"
        self.switch_to = FakeSwitchTo(self)

    def find_elements(self, by, selector):
        if selector == "iframe, frame":
            return self.frames if self.context == "main" else []
        return []

    def execute_script(self, script, *args):
        # Solo el sondeo de "sin resultados" devuelve texto; el deep-selector
        # y el resto de scripts devuelven listas vacías como en el DOM real.
        if script == "return document.body ? document.body.innerText : ''":
            return self.body_texts.get(self.context, "")
        return []


if __name__ == "__main__":
    unittest.main()
