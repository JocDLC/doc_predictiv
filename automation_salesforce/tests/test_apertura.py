import unittest
from datetime import datetime

from apertura import (
    CLASIF_FUERA_DE_RANGO,
    CLASIF_NO_HABIL,
    CLASIF_REVISION,
    CLASIF_TURNO_PERSONAL,
    classify_lead,
    parse_apertura_range,
)


def slot(start, end, bandejas=None):
    return {"start": start, "end": end, "bandejas": bandejas or []}


def bandeja(code="AR", tz_offset=0):
    return {
        "code": code,
        "enabled": True,
        "url": "https://x.lightning.force.com/lightning/r/Report/00O/view",
        "tz_offset": tz_offset,
    }


def details(fecha):
    return {"fecha_creacion": fecha}


class ClassifyLeadTests(unittest.TestCase):
    def test_nocturno_sin_franja_es_elegible(self):
        """Lead creado viernes 23:30 sin franja a esa hora → no_habil."""
        schedule = [slot("12:00", "17:59", ["AR"])]
        result = classify_lead(details("21/11/2026 11:30 PM"), bandeja("AR"), schedule, [])
        self.assertEqual(result, CLASIF_NO_HABIL)

    def test_turno_personal_aunque_sea_sabado(self):
        """Las franjas son día-agnósticas: sábado 10:00 con franja 09:00-12:00
        pertenece a quien cubre esa franja."""
        schedule = [slot("09:00", "12:00", ["AR"])]
        result = classify_lead(details("21/11/2026 10:00 AM"), bandeja("AR"), schedule, [])
        self.assertEqual(result, CLASIF_TURNO_PERSONAL)

    def test_franja_de_equipo_tambien_es_turno_personal(self):
        equipo = [{"nombre": "ROGER", "franjas": [slot("08:00", "13:00", ["CO"])]}]
        result = classify_lead(details("20/11/2026 11:00 AM"), bandeja("CO"), [], equipo)
        self.assertEqual(result, CLASIF_TURNO_PERSONAL)

    def test_franja_de_otra_bandeja_no_cubre(self):
        """Una franja MX no convierte en personal un lead CO."""
        equipo = [{"nombre": "ANA", "franjas": [slot("08:00", "13:00", ["MX"])]}]
        result = classify_lead(details("20/11/2026 11:00 AM"), bandeja("CO"), [], equipo)
        self.assertEqual(result, CLASIF_NO_HABIL)

    def test_fecha_de_ayer_se_clasifica_por_su_hora(self):
        """Un lead de ayer a las 15:00 con franja 12:00-17:59 es turno personal,
        no elegible de apertura."""
        schedule = [slot("12:00", "17:59", ["AR"])]
        result = classify_lead(details("20/11/2026 03:00 PM"), bandeja("AR"), schedule, [])
        self.assertEqual(result, CLASIF_TURNO_PERSONAL)

    def test_fecha_ilegible_va_a_revision(self):
        for fecha in ("", "ayer", "21/11/2026", None):
            with self.subTest(fecha=fecha):
                result = classify_lead(details(fecha), bandeja("AR"), [slot("00:00", "23:59")], [])
                self.assertEqual(result, CLASIF_REVISION)

    def test_tz_offset_de_documentacion_no_corre_el_reporte(self):
        """``tz_offset`` de la bandeja existe para documentar los intentos
        WhatsApp en la hora del país del lead — el reporte ya muestra la
        hora del visor (= la PC del bot). Aplicarlo a la clasificación
        corría leads en-franja a ``sin_cobertura``: un lead creado 07:34
        con franja 06:00-08:59 quedaba en 05:34 y no se tomaba."""
        lead = details("23/11/2026 07:34 AM")
        self.assertEqual(
            classify_lead(lead, bandeja("AR", tz_offset=2), [slot("06:00", "08:59", ["AR"])], []),
            CLASIF_TURNO_PERSONAL,
        )

    def test_fuera_de_rango(self):
        """El rango es [desde, hasta): lunes 06:00 queda fuera de
        viernes 18:00 → lunes 06:00."""
        schedule = []
        viernes_2330 = details("20/11/2026 11:30 PM")
        lunes_0600 = details("23/11/2026 06:00 AM")
        desde = datetime(2026, 11, 20, 18, 0)
        hasta = datetime(2026, 11, 23, 6, 0)
        self.assertEqual(classify_lead(viernes_2330, bandeja("AR"), schedule, [], desde, hasta), CLASIF_NO_HABIL)
        self.assertEqual(classify_lead(lunes_0600, bandeja("AR"), schedule, [], desde, hasta), CLASIF_FUERA_DE_RANGO)


class ParseRangeTests(unittest.TestCase):
    def test_rango_valido(self):
        desde, hasta = parse_apertura_range("2026-11-20T18:00", "2026-11-23T06:00", now=datetime(2026, 11, 23, 8, 0))
        self.assertEqual(desde, datetime(2026, 11, 20, 18, 0))
        self.assertEqual(hasta, datetime(2026, 11, 23, 6, 0))

    def test_desde_posterior_a_hasta_rechaza(self):
        with self.assertRaises(ValueError):
            parse_apertura_range("2026-11-23T06:00", "2026-11-20T18:00", now=datetime(2026, 11, 24))

    def test_hasta_futuro_rechaza(self):
        with self.assertRaises(ValueError):
            parse_apertura_range("2026-11-20T18:00", "2026-12-01T06:00", now=datetime(2026, 11, 23, 8, 0))

    def test_formato_invalido_rechaza(self):
        with self.assertRaises(ValueError):
            parse_apertura_range("viernes", "2026-11-23T06:00", now=datetime(2026, 11, 24))
        with self.assertRaises(ValueError):
            parse_apertura_range("", "2026-11-23T06:00", now=datetime(2026, 11, 24))


if __name__ == "__main__":
    unittest.main()
