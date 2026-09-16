import unittest

from selenium.webdriver.common.by import By

from report_reader import (
    REPORT_CANDIDATE_SELECTOR,
    VisibleLead,
    deduplicate_visible_leads,
    extract_created_at,
    extract_lead_id,
    find_header_index,
    find_owner_header_index,
    find_report_table,
    find_report_rows,
    is_unassigned_owner,
    is_visible_element,
    report_accessibility_summary,
    report_structure_summary,
    read_visible_unassigned_leads,
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

    def find_elements(self, by, selector):
        if selector == "iframe, frame":
            return self.frames if self.context == "main" else []
        if selector == REPORT_CANDIDATE_SELECTOR:
            if self.context == "main":
                return self.main_tables
            return self.frame_tables[self.context]
        return []


class FakeLink:
    def __init__(self, href: str):
        self.href = href

    def get_attribute(self, name: str) -> str:
        if name != "href":
            return ""
        return self.href


class FakeRow:
    def __init__(self, cells=None, links=None, displayed=True, attributes=None):
        self.cells = cells or []
        self.links = links or []
        self.displayed = displayed
        self.attributes = attributes or {}
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
        invalid_row = FakeRow(
            links=[FakeLink("https://example.invalid/lightning/r/Lead/not-a-salesforce-id/view")]
        )
        no_link_row = FakeRow()
        data_attribute_row = FakeRow(attributes={"data-recordid": "a1B000000000002AAA"})

        self.assertEqual(extract_lead_id(valid_row), "a1B000000000001AAA")
        self.assertEqual(extract_lead_id(invalid_row), "")
        self.assertEqual(extract_lead_id(no_link_row), "")
        self.assertEqual(extract_lead_id(data_attribute_row), "a1B000000000002AAA")

    def test_extract_lead_id_supports_configurable_salesforce_object(self):
        row = FakeRow(
            links=[
                FakeLink(
                    "https://example.invalid/lightning/r/Prospecto__c/a1B000000000003AAA/view"
                )
            ]
        )

        lead_id = extract_lead_id(row, record_object_api_name="Prospecto__c")

        self.assertEqual(lead_id, "a1B000000000003AAA")

    def test_deduplicate_visible_leads_uses_salesforce_lead_id(self):
        first_lead = VisibleLead("00Q000000000001AAA", "2026-09-09")
        duplicate_dom_row = VisibleLead("00Q000000000001AAA", "2026-09-09")
        second_lead = VisibleLead("00Q000000000002AAA", "2026-09-09")

        unique_leads = deduplicate_visible_leads(
            [first_lead, duplicate_dom_row, second_lead]
        )

        self.assertEqual(unique_leads, [first_lead, second_lead])

    def test_reader_includes_date_position_and_status_in_local_report_data(self):
        other_owner_row = FakeRow(
            cells=[FakeCell("2026-09-01"), FakeCell("OTRO_PROPIETARIO")]
        )
        qualifying_row = FakeRow(
            cells=[FakeCell("2026-09-02"), FakeCell("AR_LEAD_QUALIF")],
            links=[
                FakeLink(
                    "https://example.invalid/lightning/r/Lead/00Q000000000001AAA/view"
                )
            ],
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


if __name__ == "__main__":
    unittest.main()
