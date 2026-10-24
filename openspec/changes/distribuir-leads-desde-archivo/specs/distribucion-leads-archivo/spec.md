# Spec delta: distribucion-leads-archivo

## ADDED Requirements

### Requirement: REQ-901: Carga y parseo del archivo de distribución

La UI MUST aceptar archivos `.xlsx` y `.csv` (export de Salesforce con la
BD de leads). El parseo MUST hacerlo el servidor local vía
`POST /api/distribucion/parse` recibiendo `{filename, content_b64}` y
devolviendo `{sheets: [{name, headers, rows}]}` con todas las hojas del
libro, hasta 1000 filas por hoja. El archivo fuente MUST NOT persistirse
en disco ni escribirse en logs. Para `.csv` el parser MUST autodetectar
el separador (`;`, `,` o tab) y soportar `utf-8-sig` con fallback
`cp1252`. Un archivo inválido, vacío o sin filas MUST producir un error
explícito sin efectos colaterales.

#### Scenario: xlsx multi-hoja

**Given** un `.xlsx` con hojas `Leads` y `Duplicados`.
**When** la UI lo envía a `/api/distribucion/parse`.
**Then** la respuesta incluye ambas hojas con sus encabezados y filas, y
ningún archivo queda escrito en el servidor.

#### Scenario: archivo corrupto

**Given** un archivo que no es xlsx ni csv legible.
**When** se envía al endpoint.
**Then** responde error descriptivo y no se crea cola ni proceso.

### Requirement: REQ-902: Mapeo de columnas con autodetección

Tras el parseo la UI MUST permitir elegir la hoja (si hay más de una) y
mapear columnas con autodetección por alias + selección manual, igual
que el módulo "Preparar campaña predictiva". MUST exigir columna de
`Lead ID` y columna de persona destino; la columna de nombre del lead es
opcional (solo visual). La selección de hoja y columnas MUST actualizar
la vista previa sin volver a enviar el archivo.

#### Scenario: autodetección del export QUALIF

**Given** la hoja `Leads` de `QUALIF 24-10.xlsx`.
**When** se muestra el mapeo.
**Then** `Lead ID` propone la columna `Lead ID` y destino propone
`Otra información`, ambos editables.

#### Scenario: falta columna obligatoria

**Given** el usuario deja sin mapear la columna destino.
**When** intenta avanzar a la vista previa/ejecutar.
**Then** la UI bloquea la acción con mensaje explícito.

### Requirement: REQ-903: Vista previa editable

Antes de ejecutar, la UI MUST mostrar una fila por lead con: checkbox de
inclusión, Lead ID, nombre si se mapeó, y el destino en un campo
editable precargado desde la columna mapeada. Filas con Lead ID ausente
o inválido MUST quedar excluidas por defecto y contadas. El payload que
se envía a `/api/distribucion-queue` MUST ser exactamente lo visible y
editado en la tabla.

#### Scenario: corrección de destino especial

**Given** una fila con destino "Jose Manuel de la Colina".
**When** el operador edita el campo a otra persona y ejecuta.
**Then** la cola persistida lleva el destino editado, no el del archivo.

#### Scenario: filas inválidas excluidas

**Given** dos filas sin Lead ID válido.
**When** se arma la vista previa.
**Then** aparecen tachadas/excluidas, se cuentan, y no entran a la cola.

### Requirement: REQ-904: Persistencia de la cola y disparo único

`PUT /api/distribucion-queue` MUST persistir
`queues/cola_distribucion.json` con `{generated_at, source_file,
leads: [{lead_id, persona}]}` — sin datos personales de clientes — y
disparar `run_distribucion_queue.py` como proceso hijo. MUST NOT lanzar
un segundo proceso mientras uno corre. Si el monitor de bandeja está
activo MUST devolver `monitor_activo: true` como advertencia sin
bloquear.

#### Scenario: doble ejecución

**Given** un lote de distribución en curso.
**When** llega otro `PUT /api/distribucion-queue`.
**Then** se rechaza con conflicto y el proceso vigente sigue intacto.

### Requirement: REQ-905: Reasignación por lead verificada

Por cada lead el runner MUST abrir el registro por `lead_id`, leer el
propietario actual y resolver:

- propietario ya es el destino (comparación normalizada) →
  `ya_asignado`, MUST NOT modificar nada;
- propietario es una cola excluida (`AR_LEAD_COLD`,
  `AR_LEAD_EXPORT_GETLEAD`, `AR_LEAD_LEADIT_EXPORT` — leads ya en frío
  o exportados) → `cola_excluida`, MUST NOT modificar nada;
- propietario es una cola configurable (`unassigned_owner` de las
  bandejas del config, ej. `AR_LEAD_QUALIF`) → `Pick Up` + verificación
  de cambio de propietario, guardado best-effort del panel "Contact
  Client" **sin escribir marca ni texto** en `Otra información`, luego
  `reassign_owner` al destino;
- propietario es cualquier otro (usuario del bot o tercero) →
  `reassign_owner` directo al destino.

El runner MUST NOT escribir nada en `Otra información` ni en otros
campos del lead: solo el cambio de propietario. El resultado MUST
quedar `reasignado` solo tras releer el propietario y confirmar el
destino; los fallos reportan `reasignacion_error:<paso>`,
`pickup_error` o `lead_inaccesible` y el lead jamás queda sin owner
conocido.

#### Scenario: lead en cola distribuido

**Given** un lead con propietario `AR_LEAD_QUALIF` y destino "Ana Perez".
**When** el runner lo procesa.
**Then** hace Pick Up, guarda el panel si aparece, reasigna a "Ana
Perez" y el resultado es `reasignado` con `Otra información` intacta.

#### Scenario: lead de otra persona hacia el destino

**Given** un lead cuyo propietario es un tercero distinto del destino
indicado en el archivo.
**When** el runner lo procesa.
**Then** reasigna el propietario a la persona destino y el resultado es
`reasignado` verificado por relectura.

#### Scenario: lead en cola excluida

**Given** un lead con propietario `AR_LEAD_COLD` (o cualquier cola de la
lista excluida).
**When** el runner lo procesa.
**Then** no modifica nada y el resultado es `cola_excluida` con el
propietario observado.

### Requirement: REQ-906: Resultados incrementales consultables

El runner MUST registrar el resultado por lead apenas termina
(`record_result` al `.resultado.json`, patrón de cola de cierre) y la UI
MUST poder leerlo por `GET /api/distribucion-results` mientras corre.
Los resultados MUST contener solo `lead_id`, `persona` y outcome — sin
datos personales de clientes.

#### Scenario: progreso visible

**Given** un lote de 17 leads en ejecución.
**When** la UI consulta `/api/distribucion-results` a mitad del lote.
**Then** ve los resultados ya terminados y los pendientes restantes.

#### Scenario: re-ejecución tras corte

**Given** un lote interrumpido con resultados parciales.
**When** se vuelve a ejecutar con la misma cola.
**Then** los leads ya `reasignado`/`ya_asignado` se reportan
`ya_asignado` sin efectos en Salesforce.
