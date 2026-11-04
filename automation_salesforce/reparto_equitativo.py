"""Reparto equitativo del lote de leads entre quienes trabajan hoy.

Módulo puro (sin Selenium ni Salesforce): la UI manda las filas de la BD
parseada —``lead_id``, auxiliar actual y flag WhatsApp— junto con la lista
de personas que trabajan y ``repartir`` devuelve el destino de cada lead
con la menor cantidad de reasignaciones posible. La ejecución sigue siendo
la cola y el runner de distribución de siempre; aquí solo se computa a
quién va cada lead.

Reglas del reparto:

- cupo por persona = ``len(filas) // N``, más un lead extra para las
  primeras de la lista por el resto (diferencia máxima de 1 lead entre
  personas);
- un lead cuyo auxiliar (según el archivo) trabaja hoy se queda con esa
  persona hasta completar su cupo (``se_queda``). Cuando la persona tiene
  más leads en el archivo que su cupo, conserva posiciones ESPACIADAS
  uniformemente dentro de su propia sublista (orden del archivo): con cupo
  ``q`` y ``m`` leads propios se conservan los índices
  ``round(i*(m-1)/(q-1))`` para ``i`` en ``0..q-1`` (con ``q == 1``, el
  primero);
- los excedentes de cupo y los leads de auxiliares que no trabajan (o
  auxiliar vacío) van a una bolsa en orden de fila del archivo y cubren
  los déficits en orden CÍCLICO de personas (``se_mueve``): cada lead
  asignado va a la siguiente persona con cupo incompleto y avanza el
  cursor — nadie recibe un bloque contiguo, sus leads quedan entrelazados
  a lo largo del archivo. Ejemplo: 12 leads sin auxiliar del equipo y
  [A, B, C] → A recibe las filas 1,4,7,10 · B 2,5,8,11 · C 3,6,9,12.

El entrelazado mantiene el MISMO mínimo de reasignaciones que el reparto
por bloques: solo cambia QUÉ posiciones del archivo cae cada lead, no
cuántas se mueven. El reparto es determinista: mismas filas y mismo orden
de personas producen siempre el mismo resultado.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

ACCION_SE_QUEDA = "se_queda"
ACCION_SE_MUEVE = "se_mueve"

# Equipo del día persistente: ui_output/equipo_reparto.json (lista
# ``[{"nombre": str, "trabaja": bool}]``). Vive fuera del repositorio.
EQUIPO_REPARTO_FILE_NAME = "equipo_reparto.json"


def _normalize(value: object) -> str:
    """Minúsculas + sin diacríticos + espacios unificados.

    Paridad con ``normalized_key`` de lead_closure y con el
    ``normalizeHeader`` de la UI.
    """
    return " ".join(
        "".join(
            char
            for char in unicodedata.normalize("NFD", str(value or "").lower())
            if unicodedata.category(char) != "Mn"
        ).split()
    )


def _same_person(first: object, second: object) -> bool:
    """Match por nombre normalizado en ambos sentidos (como el runner)."""
    a = _normalize(first)
    b = _normalize(second)
    return bool(a and b) and (a in b or b in a)


def is_whatsapp(value: object) -> bool:
    """True si el texto normalizado contiene "whatsapp" (case/diacríticos insensible)."""
    return "whatsapp" in _normalize(value)


def _personas_unicas(trabajan: object) -> list[str]:
    """Nombres de ``trabajan`` en orden, sin vacíos ni duplicados normalizados."""
    if not isinstance(trabajan, list):
        raise ValueError("Se esperaba la lista de personas que trabajan hoy.")
    personas = []
    seen = set()
    for entry in trabajan:
        nombre = str(entry or "").strip()
        key = _normalize(nombre)
        if nombre and key not in seen:
            seen.add(key)
            personas.append(nombre)
    return personas


def _asignacion(fila: dict, destino: str, accion: str) -> dict:
    return {
        "lead_id": str(fila.get("lead_id") or "").strip(),
        "auxiliar": str(fila.get("auxiliar") or "").strip(),
        "whatsapp": bool(fila.get("whatsapp")),
        "destino": destino,
        "accion": accion,
    }


def _indices_espaciados(m: int, q: int) -> set[int]:
    """Posiciones a conservar dentro de una sublista de ``m`` leads con cupo ``q``.

    Espaciado uniforme: ``round(i*(m-1)/(q-1))`` para ``i`` en ``0..q-1``
    (``round`` de Python desempata al par más cercano). Con ``q == 1`` se
    conserva el primero; con ``q <= 0`` ninguno; con ``q >= m`` todos.
    """
    if q <= 0:
        return set()
    if q >= m:
        return set(range(m))
    if q == 1:
        return {0}
    return {round(i * (m - 1) / (q - 1)) for i in range(q)}


def repartir(filas: object, trabajan: object) -> tuple[list[dict], dict]:
    """Reparte ``filas`` entre las personas de ``trabajan``.

    ``filas`` es la lista de dicts ``{lead_id, auxiliar, whatsapp}`` en el
    orden del archivo. Devuelve ``(asignaciones, resumen)``: una asignación
    por fila (``lead_id``, ``auxiliar``, ``whatsapp``, ``destino``,
    ``accion``) y el resumen ``{persona: {cupos, se_quedan, entran}}``.
    """
    if not isinstance(filas, list) or not filas:
        raise ValueError("No hay filas de leads para repartir.")
    personas = _personas_unicas(trabajan)
    if not personas:
        raise ValueError("Tildá al menos una persona que trabaja hoy.")
    for index, fila in enumerate(filas):
        if not isinstance(fila, dict) or not str(fila.get("lead_id") or "").strip():
            raise ValueError(f"La fila {index} no tiene Lead ID válido.")
    base, resto = divmod(len(filas), len(personas))
    cupos = {persona: base + (1 if i < resto else 0) for i, persona in enumerate(personas)}
    asignaciones: list[dict | None] = [None] * len(filas)
    se_quedan = dict.fromkeys(personas, 0)
    entran = dict.fromkeys(personas, 0)
    # Se quedan: cada persona conserva posiciones espaciadas uniformemente
    # dentro de su propia sublista (leads sin asignar que la matchean, en
    # orden del archivo). Sus excedentes no reclamados quedan libres para
    # que otra persona del equipo los retenga si los matchea; lo demás va
    # a la bolsa.
    for persona in personas:
        propias = [
            index
            for index, fila in enumerate(filas)
            if asignaciones[index] is None and _same_person(fila.get("auxiliar"), persona)
        ]
        conservar = _indices_espaciados(len(propias), cupos[persona])
        for posicion, index in enumerate(propias):
            if posicion in conservar:
                asignaciones[index] = _asignacion(filas[index], persona, ACCION_SE_QUEDA)
                se_quedan[persona] += 1
    # Se mueven: la bolsa en orden de archivo cubre los cupos incompletos
    # en orden CÍCLICO de personas — cada lead va a la siguiente con
    # capacidad y avanza el cursor, así nadie recibe un bloque contiguo.
    movibles = [index for index, asignacion in enumerate(asignaciones) if asignacion is None]
    capacidad = {persona: cupos[persona] - se_quedan[persona] for persona in personas}
    cursor = 0
    for index in movibles:
        for _ in personas:
            destino = personas[cursor]
            if capacidad[destino] > 0:
                break
            cursor = (cursor + 1) % len(personas)
        else:
            break  # sin capacidad: no debería pasar (cupos suman len(filas))
        asignaciones[index] = _asignacion(filas[index], destino, ACCION_SE_MUEVE)
        capacidad[destino] -= 1
        entran[destino] += 1
        cursor = (cursor + 1) % len(personas)
    resumen = {
        persona: {"cupos": cupos[persona], "se_quedan": se_quedan[persona], "entran": entran[persona]}
        for persona in personas
    }
    return asignaciones, resumen


def validate_equipo_reparto(entries: object) -> list[dict]:
    """Valida ``[{nombre, trabaja}]`` del equipo del día.

    Dedup por nombre normalizado: ante un repetido gana la primera
    aparición en la lista.
    """
    if not isinstance(entries, list):
        raise ValueError("Se esperaba una lista de personas del equipo.")
    validated = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"La persona {index} debe ser un objeto con 'nombre' y 'trabaja'.")
        nombre = str(entry.get("nombre") or "").strip()
        if not nombre:
            raise ValueError(f"La persona {index} necesita el nombre exacto de Salesforce.")
        trabaja = entry.get("trabaja")
        if not isinstance(trabaja, bool):
            raise ValueError(f"La persona {index} necesita 'trabaja' verdadero o falso.")
        key = _normalize(nombre)
        if key in seen:
            continue
        seen.add(key)
        validated.append({"nombre": nombre, "trabaja": trabaja})
    return validated


def load_equipo_reparto(path: str | Path) -> list[dict]:
    """Lectura tolerante: archivo ausente o roto devuelve la lista vacía."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    try:
        return validate_equipo_reparto(payload)
    except ValueError:
        return []


def save_equipo_reparto(path: str | Path, equipo: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(equipo, indent=2, ensure_ascii=False), encoding="utf-8")


# --- Exportación Excel del reparto ------------------------------------------
# Se genera en memoria (nada persiste en disco): la UI descarga el archivo
# para repartirlo al equipo (distribución) o a los GTR (lista WhatsApp).
ACCION_LABELS = {ACCION_SE_QUEDA: "se queda", ACCION_SE_MUEVE: "se mueve"}

EXPORT_DISTRIBUCION = "distribucion"
EXPORT_WHATSAPP = "whatsapp"
EXPORT_TIPOS = (EXPORT_DISTRIBUCION, EXPORT_WHATSAPP)


def _export_headers_rows(tipo: str, filas: list[dict]) -> tuple[list[str], list[list]]:
    if tipo == EXPORT_DISTRIBUCION:
        headers = ["Lead ID", "Lead", "Auxiliar actual", "Nueva persona", "Acción"]
        rows = [
            [
                str(fila.get("lead_id") or "").strip(),
                str(fila.get("nombre") or "").strip(),
                str(fila.get("auxiliar") or "").strip(),
                str(fila.get("destino") or "").strip(),
                ACCION_LABELS.get(str(fila.get("accion") or ""), str(fila.get("accion") or "")),
            ]
            for fila in filas
        ]
        return headers, rows
    headers = ["Lead ID", "Nueva persona"]
    rows = [[str(fila.get("lead_id") or "").strip(), str(fila.get("destino") or "").strip()] for fila in filas]
    return headers, rows


def build_export_xlsx(tipo: object, filas: object) -> tuple[str, bytes]:
    """Genera el .xlsx del reparto en memoria: ``(filename, content)``.

    ``tipo`` es ``"distribucion"`` (una fila por lead con auxiliar, destino
    y acción) o ``"whatsapp"`` (solo lead_id → nueva persona, para GTR).
    """
    if tipo not in EXPORT_TIPOS:
        raise ValueError(f"Tipo de exportación inválido: {tipo!r} (válidos: {', '.join(EXPORT_TIPOS)}).")
    if not isinstance(filas, list) or not filas:
        raise ValueError("No hay filas para exportar.")
    for index, fila in enumerate(filas):
        if not isinstance(fila, dict) or not str(fila.get("lead_id") or "").strip():
            raise ValueError(f"La fila {index} no tiene Lead ID válido.")
    import io
    from datetime import datetime

    import openpyxl

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "WhatsApp" if tipo == EXPORT_WHATSAPP else "Distribución"
    headers, rows = _export_headers_rows(tipo, filas)
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    base = "reasignacion_whatsapp" if tipo == EXPORT_WHATSAPP else "distribucion"
    filename = f"{base}_{datetime.now().date().isoformat()}.xlsx"
    return filename, buffer.getvalue()
