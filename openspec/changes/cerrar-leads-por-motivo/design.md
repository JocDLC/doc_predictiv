# Diseño: cerrar-leads-por-motivo

## Arquitectura

```
UI (documentador_predictivo.html)
  │  selección de cierre independiente (closureIds) + motivo por lead
  │  PUT /api/close-queue   → cola cerrada inmutable por run_id
  │  POST /run-close        → runner de cierre
  ▼
ui_server.py  ── run_lock compartido con documentación ──▶ run_close_queue.py
                                                              │
        lead_closure.py  ◀── valores y procedimientos ────────┤
        closure_store.py ◀── solicitudes/resultados JSON ─────┘
```

## Contrato de cola de cierre (`queues/cola_cierre_activa.json` → congelada `cierre_<run_id>.json`)

```json
{
  "operation": "close_leads",
  "generated_at": "…",
  "leads": [
    {"lead_id": "00Q…", "reason": "ilocalizable" | "deja_de_interactuar"}
  ]
}
```

La UI envía el código del motivo; el servidor/runner resuelven los literales.
El runner rechaza cualquier motivo desconocido (lista cerrada).

## Contrato de resultados (`queues/cola_cierre_activa.resultado.json`)

Entradas por Lead con `lead_id`, `status`, `reason`, `run_id`, `at`,
`elapsed_seconds`, `stage_seconds`, `verify_reloads` — sin contenido de
campos ni datos de clientes.

Estados:

| status | Significado |
|---|---|
| `cerrado_verificado` | Campos + Cerrado + propietario AR_LEAD_COLD tras conversión |
| `ya_cerrado` | Ya estaba en el resultado final compatible; no se escribió |
| `conversion_pendiente` | Guardado verificado (campos+Cerrado); conversión no ejecutada/verificable |
| `conversion_no_verificada` | Yes pudo enviarse pero el efecto no se comprobó; NO reintentar a ciegas |
| `conflicto` | El registro cambió desde la prevalidación / estado incompatible |
| `revision` | Estado desconocido, Lead duplicado o motivo previo incompatible |
| `error` | Fallo antes de cualquier cambio o durante lectura |

## Flujo por Lead (runner)

1. `driver.get(record_url)` + `wait_for_lightning_ready`.
2. Lectura: estado actual, `Comentario`, `Otra información` (hash para
   comprobar que no se altera) y propietario.
3. Si ya está `Cerrado` con propietario `AR_LEAD_COLD` y campos del motivo →
   `ya_cerrado`. Si está Cerrado con motivo distinto o convertido a otra
   entidad → `revision`. Si `Comentario` es `Lead Duplicado` → `revision`.
4. Edición: doble clic en el control de `Comentario` dentro de la sección
   Cualificación → formulario de edición. Reemplazar Comentario (valor
   exacto), seleccionar Cualificación por etiqueta, esperar
   Sub-Cualificación habilitada y elegir etiqueta exacta. Para `ilocalizable`,
   Salesforce puede exponer dos etiquetas equivalentes según el registro:
   probar `Ilocalizable` primero y `Permanece ilocalizable` como alternativa
   automática solo si la primera no existe. Selección y lectura
   resuelven el mismo control visible único; los controles de formularios e
   iframes ocultos se excluyen. Las opciones y el scroll se limitan al listbox
   identificado por `aria-controls` dentro de la raíz del control. Si hay
   ambigüedad, abortar; si el valor exacto ya está seleccionado, no repetir clics.
5. Validar los 3 valores en el formulario → Guardar (mismo patrón que
   `save_edit_form`: clic en el Guardar del formulario + esperar cierre del
   editor + settle). En timeout: recargar el registro y verificar persistido
   antes de declarar error (recuperación como en documentación).
6. Verificar: campos persistidos + `Estado de candidato = Cerrado` +
   `Otra información` intacta (mismo hash). Si todo ok → hito
   `conversion_pendiente` persistido en el resultado por paso.
7. `Convert Lead`: localizar el botón en la barra de acciones del Lead,
   verificar el diálogo/modal esperado y pulsar `Yes`. Persistir intención
   antes de confirmar. Sin verificación previa del diálogo → abortar Lead.
8. Verificación final: `Estado de candidato = Cerrado` +
   `Propietario del candidato = AR_LEAD_COLD`. Éxito solo con ambos. La lectura
   tolera el periodo de carga y el cambio asíncrono de propietario: relee en la
   misma página mientras el estado sea `Cerrado`, con recargas acotadas si el
   registro no expone campos. El lookup de propietario puede exponer un ID
   interno en `.value`; se lee el nombre visible (`.owner-name`). Si no llega el
   estado final dentro del plazo → `conversion_no_verificada`, sin repetir Yes.

## Servidor

- `PUT /api/close-queue`: escribe la cola activa de cierre (mismo patrón que
  `/api/queue`).
- `GET /api/close-results`: resultados del lote de cierre.
- `POST /run-close`: verifica navegador (mismos preflight que `/run`),
  congela la cola a `cierre_<run_id>.json` bajo `run_lock` y lanza
  `run_close_queue.py --auto --run-id … <congelada>`.
- Una operación a la vez: documentación y cierre comparten `current_process`.

## UI

- Checkbox `Cierre` por Lead en la vista de cola (independiente del checkbox
  `Cola` de documentación) + grupo de radios con los dos motivos.
- Barra: `Seleccionar todos` / `Ninguno`, `Asignar motivo a seleccionados`,
  `Preparar cierre` (escribe cola + revisión) y `Ejecutar cierre`.
- Sin motivo por defecto; sin habilitación por cantidad de INT.
- Estados de cierre separados del badge de documentación.

## Recuperación ante fallos

- Timeout de Guardar: recargar registro, releer campos; si persistió,
  continuar en verificación; si no, `error`.
- Fallo tras el primer guardado: el Lead queda `conversion_pendiente`; la
  reanudación requiere nueva autorización (el usuario puede reenviar el lote:
  los ya cerrados quedan `ya_cerrado`/`conflicto` por estado).
- `conversion_no_verificada` nunca repite `Yes` automáticamente.

## Datos

- Resultados sin contenido de campos. Snapshots de cierre (si se guarda
  evidencia) en `ui_output/`, nunca en `queues/` ni en Git.
- La auditoría registra `run_id`, `lead_id`, paso y códigos de estado; sin
  datos personales en logs.
