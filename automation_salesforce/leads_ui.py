from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from report_reader import VisibleLead

DISPLAY_COLUMNS = (
    ("fecha_creacion", "Fecha de creación"),
    ("campana", "Campaña"),
    ("estado_candidato", "Estado del candidato"),
    ("preferencia_contacto", "Preferred mean of contact"),
    ("propietario_candidato", "Propietario"),
    ("subtipo_interes", "Sub-tipo de interés"),
    ("nombre", "Nombre y apellido"),
    ("telefono", "Teléfono móvil"),
    ("nombre_corto_concesionario", "Nombre corto concesionario"),
    ("vehiculo_interes", "Vehículo de interés"),
    ("email", "Correo"),
    ("lead_id", "Lead ID"),
    ("otra_informacion", "Otra información"),
)
FILTER_FIELDS = ("estado_candidato", "preferencia_contacto", "vehiculo_interes")
FALLBACK_COLUMNS = {
    "fecha_creacion": "col:Columna 2",
    "campana": "col:Columna 3",
    "estado_candidato": "col:Columna 4",
    "preferencia_contacto": "col:Columna 5",
    "propietario_candidato": "col:Columna 6",
    "subtipo_interes": "col:Columna 7",
    "nombre": "col:Columna 8",
    "apellido": "col:Columna 9",
    "telefono": "col:Columna 10",
    "nombre_corto_concesionario": "col:Columna 11",
    "vehiculo_interes": "col:Columna 12",
    "email": "col:Columna 13",
    "otra_informacion": "col:Columna 15",
}


def source_value(details: dict[str, str], field_name: str) -> str:
    return str(details.get(FALLBACK_COLUMNS.get(field_name, "")) or details.get(field_name, "")).strip()


def lead_payload(lead: VisibleLead) -> dict[str, object]:
    source = dict(lead.details)
    details = {field: source_value(source, field) for field, _ in DISPLAY_COLUMNS}
    details["lead_id"] = lead.lead_id
    details["nombre"] = " ".join(
        part for part in (details["nombre"], source_value(source, "apellido")) if part
    )
    return {"details": details}


def available_columns(leads: list[dict[str, object]]) -> list[tuple[str, str]]:
    return [
        (field, label)
        for field, label in DISPLAY_COLUMNS
        if any(str(lead["details"].get(field, "")).strip() for lead in leads)
    ]


def render_leads_ui(visible_row_count: int, leads: list[VisibleLead]) -> str:
    payload = [lead_payload(lead) for lead in leads]
    columns = available_columns(payload)
    shown = {field for field, _ in columns}
    omitted = [label for field, label in DISPLAY_COLUMNS if field not in shown]
    omitted_note = f": {', '.join(omitted)}" if omitted else ""
    safe_payload = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    safe_columns = json.dumps(columns, ensure_ascii=False)
    safe_filters = json.dumps(FILTER_FIELDS, ensure_ascii=False)
    return rf"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Leads sin gestión</title>
<style>body{{font-family:Arial,sans-serif;background:#f5f5f5;color:#222;margin:0}}header{{background:#002b5c;color:white;padding:18px}}h1{{margin:0 0 8px}}main{{padding:14px;max-width:100%;box-sizing:border-box}}input,select{{padding:6px;margin:3px;font-size:12px}}table{{border-collapse:collapse;width:100%;table-layout:fixed;background:white;font-size:10px}}th,td{{border:1px solid #d8d8d8;padding:4px;text-align:left;vertical-align:top;overflow-wrap:anywhere;word-break:break-word}}th{{background:#e9eef5;font-size:10px}}table.compact td{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}</style>
</head><body><header><h1>Leads sin gestión</h1><div>Filas visibles: {visible_row_count} · Leads AR_LEAD_QUALIF: {len(leads)}</div><div>Lectura local de bandeja: no se abrieron ni modificaron Leads.</div><div>Las columnas sin datos se omiten{omitted_note}.</div></header><main><input id="search" placeholder="Buscar en la bandeja"><span id="filters"></span><label><input type="checkbox" id="wrap" checked> Ajustar alto de fila al texto</label><table><thead><tr id="headers"></tr></thead><tbody id="rows"></tbody></table></main>
<script>const leads={safe_payload},columns={safe_columns},filterFields={safe_filters};function escapeHtml(value){{const node=document.createElement('span');node.textContent=value||'';return node.innerHTML}}function filters(){{const box=document.getElementById('filters');filterFields.filter(key=>columns.some(c=>c[0]===key)).forEach(key=>{{const select=document.createElement('select');select.id=key;select.append(new Option(`Todos: ${{columns.find(c=>c[0]===key)[1]}}`,''));[...new Set(leads.map(l=>l.details[key]).filter(Boolean))].sort().forEach(value=>select.add(new Option(value,value)));select.addEventListener('input',render);box.append(select)}})}}function render(){{const query=document.getElementById('search').value.toLowerCase();const result=leads.filter(lead=>filterFields.every(key=>!document.getElementById(key)||!document.getElementById(key).value||lead.details[key]===document.getElementById(key).value)&&JSON.stringify(lead.details).toLowerCase().includes(query));document.getElementById('headers').innerHTML=columns.map(([,label])=>`<th>${{escapeHtml(label)}}</th>`).join('');document.getElementById('rows').innerHTML=result.map(lead=>`<tr>${{columns.map(([key])=>`<td>${{escapeHtml(lead.details[key])}}</td>`).join('')}}</tr>`).join('')||`<tr><td colspan="${{Math.max(columns.length,1)}}">Sin coincidencias.</td></tr>`}}document.getElementById('search').addEventListener('input',render);document.getElementById('wrap').addEventListener('change',event=>{{document.querySelector('table').classList.toggle('compact',!event.target.checked)}});filters();render();</script></body></html>"""


def write_leads_ui(visible_row_count: int, leads: list[VisibleLead], output_directory: Path, generated_at: datetime | None = None) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    timestamp = generated_at or datetime.now()
    path = output_directory / f"leads_sin_gestion_{timestamp:%Y%m%d_%H%M%S}.html"
    path.write_text(render_leads_ui(visible_row_count, leads), encoding="utf-8")
    return path
