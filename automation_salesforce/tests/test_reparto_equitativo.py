"""Tests del reparto equitativo de leads y de la persistencia del equipo del día."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from reparto_equitativo import (
    is_whatsapp,
    load_equipo_reparto,
    repartir,
    save_equipo_reparto,
    validate_equipo_reparto,
)


def fila(lead_id, auxiliar="", whatsapp=False):
    return {"lead_id": lead_id, "auxiliar": auxiliar, "whatsapp": whatsapp}


def ids(prefix, count):
    return [f"{prefix}{i:012d}AAA" for i in range(count)]


class RepartirTests(unittest.TestCase):
    def test_partes_iguales_sin_auxiliar_todo_se_mueve(self):
        filas = [fila(lead_id) for lead_id in ids("00Q", 6)]
        asignaciones, resumen = repartir(filas, ["Ana", "Beto"])
        # Round-robin: la bolsa se reparte alternando personas.
        self.assertEqual([a["destino"] for a in asignaciones], ["Ana", "Beto"] * 3)
        self.assertTrue(all(a["accion"] == "se_mueve" for a in asignaciones))
        self.assertEqual(resumen["Ana"], {"cupos": 3, "se_quedan": 0, "entran": 3})
        self.assertEqual(resumen["Beto"], {"cupos": 3, "se_quedan": 0, "entran": 3})

    def test_entrelazado_round_robin_12_leads_3_personas(self):
        # Escenario del spec: 12 leads sin auxiliar del equipo → cada
        # persona recibe posiciones repartidas a lo largo del archivo,
        # nunca un bloque contiguo.
        filas = [fila(lead_id) for lead_id in ids("00Q", 12)]
        asignaciones, _ = repartir(filas, ["A", "B", "C"])
        por_persona = {"A": [], "B": [], "C": []}
        for index, asignacion in enumerate(asignaciones):
            por_persona[asignacion["destino"]].append(index)
        self.assertEqual(por_persona["A"], [0, 3, 6, 9])  # filas 1,4,7,10
        self.assertEqual(por_persona["B"], [1, 4, 7, 10])  # filas 2,5,8,11
        self.assertEqual(por_persona["C"], [2, 5, 8, 11])  # filas 3,6,9,12

    def test_resto_se_reparte_de_a_uno_en_orden(self):
        filas = [fila(lead_id) for lead_id in ids("00Q", 7)]
        _, resumen = repartir(filas, ["Ana", "Beto", "Cora"])
        self.assertEqual(resumen["Ana"]["cupos"], 3)
        self.assertEqual(resumen["Beto"]["cupos"], 2)
        self.assertEqual(resumen["Cora"]["cupos"], 2)

    def test_diferencia_maxima_de_uno(self):
        filas = [fila(lead_id) for lead_id in ids("00Q", 10)]
        _, resumen = repartir(filas, ["Ana", "Beto", "Cora"])
        cupos = [entry["cupos"] for entry in resumen.values()]
        self.assertLessEqual(max(cupos) - min(cupos), 1)
        self.assertEqual(sum(cupos), 10)

    def test_se_queda_hasta_el_cupo_y_excedente_se_mueve(self):
        # 5 filas, 2 personas: cupos Ana=3, Beto=2. Ana tiene 4 leads: se
        # queda con 3 espaciados (índices 0,2,3 de su sublista) y su
        # excedente (índice 1) cubre el déficit de Beto.
        filas = [fila(lead_id, "Ana") for lead_id in ids("00Q", 4)] + [fila("00Q000000000009AAA", "Beto")]
        asignaciones, resumen = repartir(filas, ["Ana", "Beto"])
        self.assertEqual(
            [(a["destino"], a["accion"]) for a in asignaciones],
            [
                ("Ana", "se_queda"),
                ("Beto", "se_mueve"),
                ("Ana", "se_queda"),
                ("Ana", "se_queda"),
                ("Beto", "se_queda"),
            ],
        )
        self.assertEqual(resumen["Ana"], {"cupos": 3, "se_quedan": 3, "entran": 0})
        self.assertEqual(resumen["Beto"], {"cupos": 2, "se_quedan": 1, "entran": 1})

    def test_se_queda_espaciado_uniforme_en_la_sublista(self):
        # Ana tiene 8 leads y cupo 5 (15 filas / 3 personas): conserva los
        # índices round(i*7/4) de su sublista → {0,2,4,5,7}, no un bloque.
        filas = [fila(lead_id, "Ana") for lead_id in ids("00Q", 8)]
        filas += [fila(lead_id, "Zzz Ausente") for lead_id in ids("00R", 7)]
        asignaciones, resumen = repartir(filas, ["Ana", "Beto", "Cora"])
        quedan_ana = {i for i, a in enumerate(asignaciones) if a["destino"] == "Ana" and a["accion"] == "se_queda"}
        self.assertEqual(quedan_ana, {0, 2, 4, 5, 7})
        self.assertEqual(resumen["Ana"], {"cupos": 5, "se_quedan": 5, "entran": 0})
        # Sus 3 excedentes + 7 ajenos = 10 leads se mueven 5/5 por round-robin.
        self.assertEqual(resumen["Beto"], {"cupos": 5, "se_quedan": 0, "entran": 5})
        self.assertEqual(resumen["Cora"], {"cupos": 5, "se_quedan": 0, "entran": 5})

    def test_auxiliar_fuera_del_equipo_va_a_la_bolsa(self):
        filas = [fila("00Q000000000001AAA", "Carlos Ausente"), fila("00Q000000000002AAA", "Ana")]
        asignaciones, _ = repartir(filas, ["Ana", "Beto"])
        self.assertEqual((asignaciones[0]["destino"], asignaciones[0]["accion"]), ("Beto", "se_mueve"))
        self.assertEqual((asignaciones[1]["destino"], asignaciones[1]["accion"]), ("Ana", "se_queda"))

    def test_auxiliar_vacio_es_movible(self):
        filas = [fila("00Q000000000001AAA", "")]
        asignaciones, _ = repartir(filas, ["Ana"])
        self.assertEqual(asignaciones[0]["accion"], "se_mueve")
        self.assertEqual(asignaciones[0]["destino"], "Ana")

    def test_match_normalizado_diacriticos_y_substring(self):
        filas = [fila("00Q000000000001AAA", "José Manuel Pérez")]
        asignaciones, _ = repartir(filas, ["jose manuel"])
        self.assertEqual(asignaciones[0]["accion"], "se_queda")
        filas = [fila("00Q000000000001AAA", "Jose")]
        asignaciones, _ = repartir(filas, ["Jose Manuel"])
        self.assertEqual(asignaciones[0]["accion"], "se_queda")

    def test_la_bolsa_respeta_el_orden_del_archivo(self):
        # Los movibles entran en orden de fila y se reparten en round-robin
        # cíclico: cada lead va a la siguiente persona con cupo incompleto.
        filas = [fila(lead_id) for lead_id in ids("00Q", 5)] + [fila("00Q000000000005AAA", "Cora")]
        asignaciones, _ = repartir(filas, ["Ana", "Beto", "Cora"])
        self.assertEqual(
            [a["destino"] for a in asignaciones],
            ["Ana", "Beto", "Cora", "Ana", "Beto", "Cora"],
        )

    def test_errores_de_entrada(self):
        with self.assertRaises(ValueError):
            repartir([], ["Ana"])
        with self.assertRaises(ValueError):
            repartir([fila("00Q000000000001AAA")], [])
        with self.assertRaises(ValueError):
            repartir([fila("00Q000000000001AAA")], ["", "  "])
        with self.assertRaises(ValueError):
            repartir([{"auxiliar": "Ana"}], ["Ana"])  # fila sin lead_id
        with self.assertRaises(ValueError):
            repartir("no-lista", ["Ana"])
        with self.assertRaises(ValueError):
            repartir([fila("00Q000000000001AAA")], "no-lista")

    def test_determinismo(self):
        auxiliares = ["Ana", "", "Beto", "Ana", "Carlos", "Ana", "Beto"]
        filas = [fila(lead_id, auxiliar) for lead_id, auxiliar in zip(ids("00Q", 7), auxiliares)]
        self.assertEqual(repartir(filas, ["Ana", "Beto"]), repartir(filas, ["Ana", "Beto"]))

    def test_flag_whatsapp_se_conserva_en_la_asignacion(self):
        filas = [fila("00Q000000000001AAA", "", whatsapp=True), fila("00Q000000000002AAA")]
        asignaciones, _ = repartir(filas, ["Ana", "Beto"])
        self.assertTrue(asignaciones[0]["whatsapp"])
        self.assertFalse(asignaciones[1]["whatsapp"])

    def test_trabajan_dedup_por_nombre_normalizado(self):
        filas = [fila(lead_id) for lead_id in ids("00Q", 4)]
        _, resumen = repartir(filas, ["José", "jose", "Beto"])
        self.assertEqual(list(resumen), ["José", "Beto"])


class IsWhatsappTests(unittest.TestCase):
    def test_deteccion_insensible_a_case(self):
        for text in ("WhatsApp", "WHATSAPP", "prefiere whatsapp", "Whatsapp Business", "  whatsapp  "):
            self.assertTrue(is_whatsapp(text), text)

    def test_no_whatsapp(self):
        for text in ("Llamada", "Email", "", None):
            self.assertFalse(is_whatsapp(text), text)


class EquipoRepartoTests(unittest.TestCase):
    def test_validate_ok_y_dedup_normalizado(self):
        equipo = validate_equipo_reparto(
            [
                {"nombre": "José Manuel", "trabaja": True},
                {"nombre": "jose manuel", "trabaja": False},
                {"nombre": "Ana", "trabaja": False},
            ]
        )
        self.assertEqual(
            equipo,
            [{"nombre": "José Manuel", "trabaja": True}, {"nombre": "Ana", "trabaja": False}],
        )

    def test_validate_rechaza_entradas_invalidas(self):
        with self.assertRaises(ValueError):
            validate_equipo_reparto("no-lista")
        with self.assertRaises(ValueError):
            validate_equipo_reparto([{"nombre": "", "trabaja": True}])
        with self.assertRaises(ValueError):
            validate_equipo_reparto([{"nombre": "Ana"}])
        with self.assertRaises(ValueError):
            validate_equipo_reparto([{"nombre": "Ana", "trabaja": "si"}])
        with self.assertRaises(ValueError):
            validate_equipo_reparto(["Ana"])

    def test_roundtrip_archivo(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "equipo_reparto.json"
            self.assertEqual(load_equipo_reparto(path), [])
            equipo = [{"nombre": "Ana", "trabaja": True}, {"nombre": "Beto", "trabaja": False}]
            save_equipo_reparto(path, equipo)
            self.assertEqual(load_equipo_reparto(path), equipo)

    def test_load_tolerante_a_archivo_roto(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "equipo_reparto.json"
            path.write_text("no es json", encoding="utf-8")
            self.assertEqual(load_equipo_reparto(path), [])
            path.write_text('{"no": "lista"}', encoding="utf-8")
            self.assertEqual(load_equipo_reparto(path), [])


if __name__ == "__main__":
    unittest.main()
