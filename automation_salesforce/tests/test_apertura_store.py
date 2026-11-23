"""Almacén de apertura (apertura_store): lotes JSONL en ui_output/apertura/.

REQ-834: cada toma persiste por lead; `en_curso` que quedó al reiniciar pasa a
`revisar` (nunca se reintenta a ciegas); solo `tomado_confirmado` no consumido
se ofrece a Distribuir leads.
"""

import tempfile
import unittest
from pathlib import Path

from apertura_store import (
    ESTADO_EN_CURSO,
    ESTADO_ERROR,
    ESTADO_REVISION,
    ESTADO_TOMADO_CONFIRMADO,
    create_lote,
    disponibles,
    load_lote,
    lotes,
    marcar_consumidos,
    reconciliar_en_curso,
    update_lead,
)

LEAD_A = "00Q000000000001AAA"
LEAD_B = "00Q000000000002AAA"


class AperturaStoreTests(unittest.TestCase):
    def _dir(self):
        return Path(self._tmp.name)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _lote(self, ids=(LEAD_A, LEAD_B), **kw):
        params = {
            "bandeja": "AR",
            "desde": "2026-11-20T18:00",
            "hasta": "2026-11-23T06:00",
            "lead_ids": list(ids),
        }
        params.update(kw)
        return create_lote(self._dir(), **params)

    def test_lote_persiste_leads_en_curso(self):
        lote = self._lote()
        self.assertTrue((self._dir() / f"{lote['lote_id']}.json").exists())
        recargado = load_lote(self._dir(), lote["lote_id"])
        self.assertEqual(recargado["bandeja"], "AR")
        self.assertEqual(recargado["desde"], "2026-11-20T18:00")
        for lead_id in (LEAD_A, LEAD_B):
            self.assertEqual(recargado["leads"][lead_id]["estado"], ESTADO_EN_CURSO)

    def test_exito_parcial_solo_confirmados_quedan_disponibles(self):
        lote = self._lote()
        update_lead(self._dir(), lote["lote_id"], LEAD_A, ESTADO_TOMADO_CONFIRMADO)
        update_lead(self._dir(), lote["lote_id"], LEAD_B, ESTADO_ERROR, motivo="timeout")
        disp = disponibles(self._dir())
        self.assertEqual([d["lead_id"] for d in disp], [LEAD_A])
        recargado = load_lote(self._dir(), lote["lote_id"])
        self.assertEqual(recargado["leads"][LEAD_B]["motivo"], "timeout")

    def test_reinicio_deja_en_curso_en_revision(self):
        lote = self._lote()
        update_lead(self._dir(), lote["lote_id"], LEAD_A, ESTADO_TOMADO_CONFIRMADO)
        reconciliar_en_curso(self._dir())
        recargado = load_lote(self._dir(), lote["lote_id"])
        self.assertEqual(recargado["leads"][LEAD_B]["estado"], ESTADO_REVISION)
        self.assertEqual(recargado["leads"][LEAD_A]["estado"], ESTADO_TOMADO_CONFIRMADO)

    def test_consumido_no_se_reofrece(self):
        lote = self._lote()
        update_lead(self._dir(), lote["lote_id"], LEAD_A, ESTADO_TOMADO_CONFIRMADO)
        marcar_consumidos(self._dir(), [LEAD_A], run_id="run_1")
        self.assertEqual(disponibles(self._dir()), [])
        recargado = load_lote(self._dir(), lote["lote_id"])
        self.assertEqual(recargado["leads"][LEAD_A]["consumido"], "run_1")

    def test_disponibles_filtra_por_bandeja(self):
        lote_ar = self._lote(ids=(LEAD_A,))
        lote_mx = self._lote(ids=(LEAD_B,), bandeja="MX")
        update_lead(self._dir(), lote_ar["lote_id"], LEAD_A, ESTADO_TOMADO_CONFIRMADO)
        update_lead(self._dir(), lote_mx["lote_id"], LEAD_B, ESTADO_TOMADO_CONFIRMADO)
        disp = disponibles(self._dir(), bandeja="MX")
        self.assertEqual([(d["lead_id"], d["bandeja"]) for d in disp], [(LEAD_B, "MX")])

    def test_lotes_lista_todos_los_archivos(self):
        self._lote(ids=(LEAD_A,))
        self._lote(ids=(LEAD_B,))
        self.assertEqual(len(lotes(self._dir())), 2)
        self.assertEqual(lotes(Path(self._tmp.name) / "vacio"), [])


if __name__ == "__main__":
    unittest.main()
