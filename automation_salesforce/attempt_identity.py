"""Identidad por llamada: qué ``call_id`` ya están en ``Otra información``.

La identidad mínima de un intento documentado es ``(lead_id, call_id)`` y el
``call_id`` se compara como string opaco: puede tener punto y ceros, nunca se
convierte a número ni se buscan subcadenas. Solo califican los tokens finales
de líneas que empiezan con ``N INT``, para no confundir teléfonos, importes o
fechas con IDs de llamada.
"""

from __future__ import annotations

import re

CALL_ID_PATTERN = re.compile(r"^\d{5,}\.\d{3,}$")
INT_LINE_PATTERN = re.compile(r"^\s*\d+\s+INT\b", re.IGNORECASE)


def documented_call_ids(field_text: str) -> set[str]:
    """Extrae los ``call_id`` presentes en líneas ``N INT`` del campo."""
    ids: set[str] = set()
    for line in str(field_text or "").splitlines():
        if not INT_LINE_PATTERN.match(line):
            continue
        tokens = line.split()
        if tokens and CALL_ID_PATTERN.match(tokens[-1]):
            ids.add(tokens[-1])
    return ids


def partition_attempts(
    existing_comment: str,
    attempts: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[str], list[dict[str, str]]]:
    """Divide los intentos de la cola en faltantes, presentes y ambiguos.

    Devuelve ``(missing, present_call_ids, unverifiable)``:

    - ``missing``: intentos cuyo ``call_id`` no aparece en el campo (o intentos
      sin ``call_id`` cuando el campo está vacío: no hay nada con qué chocar).
    - ``present_call_ids``: ``call_id`` solicitados que ya están documentados.
    - ``unverifiable``: intentos sin ``call_id`` cuando el campo ya tiene
      contenido — no se puede descartar una duplicación, van a revisión.

    Un mismo ``call_id`` repetido en la entrada se procesa una sola vez.
    """
    present_in_field = documented_call_ids(existing_comment)
    field_has_content = bool(str(existing_comment or "").strip())
    missing: list[dict[str, str]] = []
    present: list[str] = []
    unverifiable: list[dict[str, str]] = []
    seen: set[str] = set()
    for attempt in attempts:
        call_id = str(attempt.get("call_id") or "").strip()
        if not call_id:
            (unverifiable if field_has_content else missing).append(attempt)
        elif call_id in seen:
            continue  # mismo call_id repetido en la entrada: se procesa una vez
        elif call_id in present_in_field:
            seen.add(call_id)
            present.append(call_id)
        else:
            seen.add(call_id)
            missing.append(attempt)
    return missing, present, unverifiable
