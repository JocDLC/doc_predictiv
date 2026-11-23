import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from distribucion_loader import (
    load_distribucion_queue,
    parse_archivo,
    validate_distribucion_queue,
)

VALID_LEAD = {"lead_id": "00Q000000000001AAA", "persona": "Ana Perez"}
VALID_QUEUE = {"operation": "distribuir_leads", "source_file": "bd.xlsx", "leads": [VALID_LEAD]}


def make_xlsx(sheets: dict[str, list[list]]) -> bytes:
    import openpyxl

    workbook = openpyxl.Workbook()
    for name, rows in sheets.items():
        worksheet = workbook.active if workbook.active.title == "Sheet" else workbook.create_sheet()
        worksheet.title = name
        for row in rows:
            worksheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


class ParseArchivoTests(unittest.TestCase):
    def test_xlsx_multiple_sheets_with_headers_and_rows(self):
        content = make_xlsx(
            {
                "Leads": [
                    ["Lead ID", "Otra información", "Distribucion"],
                    ["00Q000000000001AAA", "Ana Perez", ""],
                    ["00Q000000000002AAA", "Juan Lopez", ""],
                    ["", "", ""],  # fila vacía: se omite
                ],
                "Duplicados": [["Lead ID"], []],  # sin datos: la hoja no sale
            }
        )

        parsed = parse_archivo("QUALIF 24-10.xlsx", content)

        self.assertEqual(len(parsed["sheets"]), 1)
        sheet = parsed["sheets"][0]
        self.assertEqual(sheet["name"], "Leads")
        self.assertIn("Otra información", sheet["headers"])
        self.assertEqual(len(sheet["rows"]), 2)
        self.assertEqual(sheet["rows"][0]["Lead ID"], "00Q000000000001AAA")
        self.assertEqual(sheet["rows"][0]["Otra información"], "Ana Perez")
        self.assertFalse(sheet["truncated"])

    def test_csv_semicolon_and_comma(self):
        for text in ("Lead ID;Destino\n00Q000000000001AAA;Ana\n", "Lead ID,Destino\n00Q000000000001AAA,Ana\n"):
            parsed = parse_archivo("bd.csv", text.encode("utf-8"))
            self.assertEqual(parsed["sheets"][0]["rows"][0]["Destino"], "Ana")

    def test_csv_cp1252_fallback(self):
        content = "Lead ID;Destino\n00Q000000000001AAA;Pérez\n".encode("cp1252")
        parsed = parse_archivo("bd.csv", content)
        self.assertEqual(parsed["sheets"][0]["rows"][0]["Destino"], "Pérez")

    def test_rejects_garbage_and_unknown_extension(self):
        with self.assertRaises(ValueError):
            parse_archivo("bd.xlsx", b"no es un zip")
        with self.assertRaises(ValueError):
            parse_archivo("bd.pdf", b"%PDF-1.4")
        with self.assertRaises(ValueError):
            parse_archivo("bd.xlsx", b"")


class DistribucionQueueTests(unittest.TestCase):
    def test_validates_pairs_lead_persona(self):
        leads = validate_distribucion_queue(VALID_QUEUE)
        self.assertEqual(leads, [{"lead_id": "00Q000000000001AAA", "persona": "Ana Perez"}])

    def test_keeps_nombre_when_present(self):
        """El nombre del lead viaja en la cola para mostrar la columna Lead
        en la tabla de resultados aunque la página se recargue."""
        queue = {**VALID_QUEUE, "leads": [{**VALID_LEAD, "nombre": "Juan Cliente"}]}
        leads = validate_distribucion_queue(queue)
        self.assertEqual(leads[0]["nombre"], "Juan Cliente")

    def test_nombre_absent_keeps_pair_only(self):
        """Colas viejas sin nombre validan igual: el campo es opcional."""
        leads = validate_distribucion_queue(VALID_QUEUE)
        self.assertNotIn("nombre", leads[0])

    def test_rejects_wrong_operation_empty_leads_and_duplicates(self):
        with self.assertRaises(ValueError):
            validate_distribucion_queue({"operation": "otra", "leads": [VALID_LEAD]})
        with self.assertRaises(ValueError):
            validate_distribucion_queue({"operation": "distribuir_leads", "leads": []})
        with self.assertRaises(ValueError):
            validate_distribucion_queue({"operation": "distribuir_leads", "leads": [VALID_LEAD, VALID_LEAD]})

    def test_rejects_bad_lead_id_and_empty_persona(self):
        with self.assertRaises(ValueError):
            validate_distribucion_queue(
                {"operation": "distribuir_leads", "leads": [{"lead_id": "123", "persona": "Ana"}]}
            )
        with self.assertRaises(ValueError):
            validate_distribucion_queue(
                {"operation": "distribuir_leads", "leads": [{"lead_id": "00Q000000000001AAA", "persona": " "}]}
            )

    def test_modo_prueba_validates_and_loads(self):
        queue = {**VALID_QUEUE, "modo": "prueba"}
        leads = validate_distribucion_queue(queue)
        self.assertEqual(leads, [{"lead_id": "00Q000000000001AAA", "persona": "Ana Perez"}])
        with TemporaryDirectory() as tmp:
            queues = Path(tmp) / "queues"
            queues.mkdir()
            path = queues / "cola.json"
            path.write_text(json.dumps(queue), encoding="utf-8")
            self.assertEqual(load_distribucion_queue(str(path), queues)["modo"], "prueba")

    def test_modo_missing_defaults_real_and_invalid_is_rejected(self):
        with TemporaryDirectory() as tmp:
            queues = Path(tmp) / "queues"
            queues.mkdir()
            path = queues / "cola.json"
            path.write_text(json.dumps(VALID_QUEUE), encoding="utf-8")
            self.assertEqual(load_distribucion_queue(str(path), queues)["modo"], "real")
        with self.assertRaises(ValueError):
            validate_distribucion_queue({**VALID_QUEUE, "modo": "demo"})
        with self.assertRaises(ValueError):
            validate_distribucion_queue({**VALID_QUEUE, "modo": 7})

    def test_load_queue_requires_queues_directory(self):
        with TemporaryDirectory() as tmp:
            queues = Path(tmp) / "queues"
            queues.mkdir()
            path = queues / "cola.json"
            path.write_text(json.dumps(VALID_QUEUE), encoding="utf-8")
            loaded = load_distribucion_queue(str(path), queues)
            self.assertEqual(loaded["source_file"], "bd.xlsx")
            outside = Path(tmp) / "fuera.json"
            outside.write_text(json.dumps(VALID_QUEUE), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_distribucion_queue(str(outside), queues)


class MezclarAperturaTests(unittest.TestCase):
    """La mezcla identifica al lead SOLO por Lead ID: un duplicado
    archivo+apertura queda una sola fila con el destino del archivo, y dos
    nombres iguales con IDs distintos son dos filas independientes."""

    def test_duplicado_conserva_fila_y_destino_del_archivo(self):
        from distribucion_loader import mezclar_apertura

        filas = [{"lead_id": "00Q1", "persona": "Ana", "nombre": "Maria"}]
        merged, resumen = mezclar_apertura(filas, [{"lead_id": "00Q1", "bandeja": "AR"}], ["00Q1"])
        self.assertEqual(merged, filas)
        self.assertEqual(resumen["duplicados"], ["00Q1"])
        self.assertEqual(resumen["agregados"], 0)

    def test_nombres_iguales_ids_distintos_dos_filas(self):
        from distribucion_loader import mezclar_apertura

        filas = [{"lead_id": "00Q1", "persona": "", "nombre": "Maria Perez"}]
        merged, _ = mezclar_apertura(filas, [{"lead_id": "00Q2", "bandeja": "MX"}], ["00Q2"])
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[1]["origen"], "apertura")

    def test_id_no_disponible_se_omite(self):
        """Solo se agregan IDs que el store ofrece — nada se inventa."""
        from distribucion_loader import mezclar_apertura

        merged, resumen = mezclar_apertura([], [], ["00Q9"])
        self.assertEqual(merged, [])
        self.assertEqual(resumen["omitidos"], ["00Q9"])

    def test_sin_archivo_funciona(self):
        from distribucion_loader import mezclar_apertura

        merged, resumen = mezclar_apertura([], [{"lead_id": "00Q1", "bandeja": "CO", "lote_id": "lote1"}], ["00Q1"])
        self.assertEqual(resumen["agregados"], 1)
        self.assertEqual(merged[0]["bandeja"], "CO")
        self.assertEqual(merged[0]["lote_id"], "lote1")


if __name__ == "__main__":
    unittest.main()
