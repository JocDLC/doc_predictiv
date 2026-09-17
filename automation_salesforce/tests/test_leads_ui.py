import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from leads_ui import available_columns, lead_payload, render_leads_ui, write_leads_ui
from report_reader import VisibleLead


class LeadsUiTests(unittest.TestCase):
    def setUp(self):
        self.lead = VisibleLead(
            lead_id="00Q000000000001AAA",
            created_at="",
            details={
                "col:Columna 1": "1",
                "col:Columna 2": "15/09/2026 10:30",
                "col:Columna 3": "Campaña local",
                "col:Columna 4": "Nuevo",
                "col:Columna 5": "vía whatsapp",
                "col:Columna 6": "AR_LEAD_QUALIF",
                "col:Columna 7": "Solicitud de compra",
                "col:Columna 8": "Ana",
                "col:Columna 9": "Pérez",
                "col:Columna 10": "+5491100000000",
                "col:Columna 11": "ALPES",
                "col:Columna 12": "KWID",
                "col:Columna 13": "ana@example.invalid",
                "col:Columna 14": "00Q000000000001AAA",
                "col:Columna 15": "1 INT contacto",
                "col:Columna 16": "Contexto oculto",
            },
        )

    def test_renders_confirmed_columns_in_salesforce_order(self):
        rendered = render_leads_ui(12, [self.lead])

        expected = [
            "Fecha de creación", "Campaña", "Estado del candidato",
            "Preferred mean of contact", "Propietario", "Sub-tipo de interés",
            "Nombre y apellido", "Teléfono móvil", "Nombre corto concesionario",
            "Vehículo de interés", "Correo", "Lead ID", "Otra información",
        ]
        self.assertEqual([label for _, label in available_columns([lead_payload(self.lead)])], expected)
        for label in expected:
            self.assertIn(label, rendered)
        columns = available_columns([lead_payload(self.lead)])
        self.assertEqual([label for _, label in columns], expected)

    def test_omits_position_duplicate_context_and_dash_columns(self):
        rendered = render_leads_ui(1, [self.lead])

        self.assertIn("Ana Pérez", rendered)
        self.assertNotIn("Columna 1", rendered)
        self.assertNotIn("Columna 14", rendered)
        self.assertIn("Otra información", rendered)
        self.assertNotIn("Columna 15", rendered)
        self.assertNotIn("Columna 16", rendered)
        self.assertNotIn("Acción sugerida", rendered)

    def test_writes_html_in_requested_local_directory(self):
        with TemporaryDirectory() as temporary_directory:
            output = write_leads_ui(1, [self.lead], Path(temporary_directory), datetime(2026, 9, 15, 9, 0))
            rendered = output.read_text(encoding="utf-8")

        self.assertEqual(output.name, "leads_sin_gestion_20260915_090000.html")
        self.assertIn("<table>", rendered)


if __name__ == "__main__":
    unittest.main()
