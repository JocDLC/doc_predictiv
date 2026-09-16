# Handoff — Piloto Selenium solo lectura (automatizar-lectura-salesforce)

> Estado al momento de pausar el trabajo. El siguiente agente debe leer este
> documento, los artefactos OpenSpec del cambio y los archivos Python antes de
> tocar código. **El piloto sigue siendo estrictamente solo lectura.**

## 1. Dónde estamos

Fase 3 (Lectura de bandeja de Leads) parcialmente implementada. Las fases 0, 1
y 2 están completadas y validadas manualmente. La fase 3 tiene el lector escrito
pero **sin probar contra Salesforce real**.

Resumen por fase (ver `openspec/changes/automatizar-lectura-salesforce/tasks.md`
para el detalle marcado):

| Fase | Estado |
|------|--------|
| 0 — Seguridad y preflight | completa |
| 1 — Fábrica de navegador y login manual | completa y validada el 2026-09-09 |
| 2 — Infraestructura de auditoría y selectores | parcial (2.1–2.2 OK; 2.3–2.5 pendientes de validación real) |
| 3 — Lectura de bandeja de Leads | parcial (código escrito, sin ejecutar contra Salesforce) |
| 4 — Lectura de Otra información y próximo INT | no iniciada |
| 5 — Verificación y cierre | no iniciada |
| 6 — Propuesta posterior (escritura) | fuera de alcance de este cambio |

## 2. Qué ya funciona (validado)

- Edge se abre con el perfil dedicado `C:\Users\ax24611\AppData\Local\RenaultPredictivo\edge-profile`.
- Login y 2FA manuales funcionan.
- `run_read_only.py` abre Salesforce raíz, espera confirmación por terminal y
  cierra limpio.
- `local_audit.mask_lead_id()` cubierto por tests unitarios (2/2 OK).
- Sintaxis de los cinco módulos Python verificada con `ast.parse`.

## 3. Qué falta validar / implementar

### 3.1 Prueba manual del lector de reporte (prioridad inmediata)

El lector `report_reader.read_visible_unassigned_leads()` nunca se ejecutó contra
el reporte real. Antes de confiar en sus selectores hay que:

1. Crear el runner `run_report_read_only.py` (no existe todavía) que:
   - abra Edge con el perfil dedicado;
   - llame a `prompt_for_manual_authentication(driver, config)`;
   - navegue a `config["report_url"]`;
   - espere Lightning con `wait_for_lightning_ready`;
   - llame a `read_visible_unassigned_leads(driver, timeout)`;
   - imprima solo: conteo total de filas visibles, conteo de Leads
     `AR_LEAD_QUALIF` y Lead IDs enmascarados;
   - nunca haga click en editar/guardar/reasignar;
   - capture screenshot si `find_report_table` lanza `TimeoutException`.
2. Pedir al usuario que lo ejecute desde PowerShell (el terminal del agente no
   puede completar `input()`).
3. Comparar el conteo y los primeros IDs con lo que el usuario ve en Salesforce.
4. Ajustar selectores según el DOM real de Lightning y registrar el ajuste en
   `tasks.md`.

### 3.2 Selectores que probablemente necesiten ajuste

`report_reader.py` asume:

- La grilla es `<table>` o un elemento con `role='grid'`.
- Los encabezados están en `thead th` o `[role='columnheader']`.
- Las filas están en `tbody tr` o `[role='row']`.
- Las celdas son `td` o `[role='gridcell']`.
- El Lead ID se extrae de un `<a href>` que coincide con
  `/(?:[A-Za-z0-9]{15,18})(?:/view|$)/`.

Salesforce Lightning suele usar una grilla virtualizada (`lightning-datatable`)
donde estas suposiciones pueden no sostenerse. Si la grilla no se encuentra,
`find_report_table` lanza `TimeoutException`; el runner debe capturar screenshot
y loguear para que el siguiente agente inspeccione el DOM real.

### 3.3 Tests unitarios pendientes

- Filtro `is_unassigned_owner`: exacto, con espacios y con otro owner.
- `find_header_index` con encabezados normalizados y ausentes.
- `row_values` con celdas `td` y `gridcell`.
- `extract_lead_id` con href válido, inválido y sin link.
- Deduplicación por Lead ID (cuando se implemente).
- Parser `N INT` (Fase 4, cuando exista `comment_reader.py`).

### 3.4 Tareas de Fase 4 y 5

No iniciar Fase 4 hasta que la Fase 3 esté validada manualmente. La Fase 4
requiere abrir Leads individuales y leer "Otra información" sin editar; el
parser `next_attempt_number` aún no existe.

## 4. Archivos actuales del piloto

```
automation_salesforce/
├── HANDOFF.md                 (este archivo)
├── README.md
├── requirements.txt           selenium==4.48.0
├── config.example.json
├── config.json                (local, ignorado por Git)
├── browser_factory.py         detect_browser() + create_driver()
├── local_audit.py             mask_lead_id, create_logger, capture_failure
├── salesforce_session.py      load_config, wait_for_authentication,
│                              wait_for_lightning_ready,
│                              prompt_for_manual_authentication
├── report_reader.py           find_report_table, read_visible_unassigned_leads
├── run_read_only.py           runner de login (Fase 1)
└── tests/
    └── test_local_audit.py    2 tests de mask_lead_id (OK)
```

Falta crear:

- `automation_salesforce/run_report_read_only.py` — runner de la Fase 3.
- Tests unitarios de `report_reader` (sin navegador).

## 5. Configuración vigente

`config.json` (local):

```json
{
  "browser": "edge",
  "profile_directory": "%LOCALAPPDATA%\\RenaultPredictivo\\edge-profile",
  "salesforce_url": "https://renaultarca.lightning.force.com",
  "report_url": "https://renaultarca.lightning.force.com/lightning/r/Report/00O67000006cstjEAA/view?queryScope=userFolders",
  "timeouts": {
    "page_load_seconds": 30,
    "authentication_seconds": 300
  },
  "screenshot_directory": "screenshots",
  "log_directory": "logs"
}
```

## 6. Restricciones que se mantienen

- **Solo lectura.** No escribir, no guardar, no reasignar, no cerrar Leads.
- **No automatizar 2FA ni credenciales.**
- **No enviar datos a servidores externos.**
- **Logs y screenshots locales y sin datos sensibles** (comentarios, teléfonos,
  emails). Lead IDs siempre enmascarados en logs.
- **No commitear** `config.json`, `logs/`, `screenshots/`, `profiles/`,
  `queues/` ni archivos de clientes.
- El usuario debe ejecutar los runners desde PowerShell; el terminal del agente
  no puede completar `input()`.

## 7. Estado Git

```
M  .gitignore
M  documentador_predictivo.html
M  graphify-out/*
M  openspec/changes/preparar-predictivo/*
?? automation_salesforce/
?? openspec/changes/automatizar-lectura-salesforce/
```

No se ha commiteado nada del piloto Selenium todavía. No commitear ni pushear
sin confirmación explícita del usuario.

## 8. Secuencia sugerida para el siguiente agente

1. Anunciar que retoma el piloto solo lectura.
2. Leer:
   - `openspec/changes/automatizar-lectura-salesforce/proposal.md`
   - `openspec/changes/automatizar-lectura-salesforce/design.md`
   - `openspec/changes/automatizar-lectura-salesforce/specs/lectura-salesforce/spec.md`
   - `openspec/changes/automatizar-lectura-salesforce/tasks.md`
   - `automation_salesforce/HANDOFF.md` (este archivo)
   - Los cinco módulos Python listados arriba.
3. Ejecutar `python -m unittest discover -s tests -v` (debe dar 2/2 OK).
4. Agregar tests unitarios de `report_reader` sin navegador.
5. Crear `run_report_read_only.py` siguiendo 3.1.
6. Pedir al usuario que lo ejecute desde PowerShell.
7. Comparar resultados con Salesforce y ajustar selectores.
8. Marcar tareas en `tasks.md` a medida que se validen.
9. Solo después de validar Fase 3, considerar Fase 4.
