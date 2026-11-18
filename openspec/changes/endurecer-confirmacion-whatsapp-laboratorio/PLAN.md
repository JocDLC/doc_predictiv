# Plan de ejecución: confirmación segura y pruebas adversariales del laboratorio

Estado: **plan listo para implementación; siguiente piloto real NO habilitado**.
Alcance solicitado: preparar trabajo verificable para otro agente.
Este documento, `design.md`, `tasks.md` y `specs/` son la fuente del traspaso.

## Instrucción para el agente ejecutor

Implementar el cambio OpenSpec `endurecer-confirmacion-whatsapp-laboratorio` en
`C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo`.
Invocar `openspec-apply-change`, Graphify y Gantt. Trabajar tareas en orden,
marcar únicamente lo terminado y adjuntar resultados. No ejecutar el script
`automation_salesforce/lab_debug_eval.py` por importación: contiene código activo
de auditoría contra Salesforce. No borrar ni resetear cambios existentes.

La vía SDD ya está determinada: cambian la mecánica de Salesforce y los contratos
de confirmación. La planificación continúa el laboratorio aprobado. No confundir
artefactos OpenSpec completos con implementación terminada.

## Qué se verificó antes de entregar este plan

| Verificación ejecutada | Resultado |
| --- | --- |
| `python harness.py test` desde `automation_salesforce` | 686 tests PASS, exit 0, 104,245 s |
| `python harness.py lint` | PASS, exit 0 |
| `python harness.py compile` | PASS |
| `python harness.py format-check` | FAIL preexistente: agent_browser.py, lab_debug_eval.py, ui_server.py |
| `python harness.py business-contracts` | FAIL: 32 tests ejecutados, 19 fallos y 9 errores; hash del diagrama técnico no coincide |
| Sondas adversariales del JS productivo en Node y runner con fakes | 14 casos: 8 PASS, 6 FAIL |
| Journal SQLite abierto en `mode=ro` | 35 docs confirmadas; 5 envíos registrados confirmados; 30 no_confirmado; 0 evidencias |
| Resultados de comparación existentes | 80 leads/160 evaluaciones; 79 coincidencias; 1 falta de botón en Selenium |

Evidencias: `baseline-tests.log`, `business-contracts.log` y `diagnostico-resultados.json`.
OpenSpec valida los cuatro artefactos del cambio y los 25 cambios abiertos.

El gate de contratos falla por el archivo protegido
`.archify/architecture-documentador-20260928-090859/documentador-architecture.html`,
ajeno a los cambios de esta sesión. El hash esperado en `business_contract_graph/paths.py`
empieza `24a07fe6`; el observado empieza `64e629b2`. Investigar la procedencia de esa
diferencia. No cambiar el hash esperado, borrar tests ni regenerar el archivo protegido
solo para obtener verde. Si su reconciliación requiere una decisión ajena al laboratorio,
entregar el diagnóstico concreto al usuario y mantener ese gate pendiente.

Las sondas ejecutadas son diagnósticos de código en un DOM mínimo simulado.
La matriz completa con navegadores y los envíos futuros NO se ejecutaron en esta
sesión de planificación; quedan como tareas explícitas.

Para repetir las sondas desde la raíz:

```powershell
python openspec/changes/endurecer-confirmacion-whatsapp-laboratorio/diagnostico_adversarial.py
```

Exit 1 es el resultado esperado del código actual porque hay seis fallos.
El script escribe únicamente su reporte local, usa SQLite temporal para mutaciones
de prueba y abre el journal productivo en solo lectura. Nunca envía WhatsApp.

### Seis hallazgos reproducidos

| Caso | Resultado actual | Comportamiento requerido |
| --- | --- | --- |
| `Error: WhatsApp no enviado` | Se reconoce como confirmación | Rechazar |
| `WhatsApp status actualizado` | Se reconoce como confirmación | No atribuir envío |
| Toast positivo ya existente | Se acepta sin baseline temporal | No confirmar la operación nueva |
| Línea legítima `Modificar Otra información` dentro del historial | Se elimina al leer | Conservar contenido literal |
| Mismo lead ambiguo en campaña nueva | No bloquea | Bloquear reenvío dentro del laboratorio |
| Identidad del registro vacía | Verificación devuelve apto | Bloquear |

El mismo patrón amplio de toast existe en los helpers del Monitor usados por
SeleniumLabBrowser. No atribuir los falsos positivos exclusivamente a agent-browser.
No basta aumentar el timeout: tres fallos afectan falsos éxitos, no esperas cortas.

### Correcciones a conclusiones anteriores

No hay evidencia que explique los 30 casos históricos. “Toast no visto” no significa
“no enviado”. Tampoco cinco registros confirmados prueban cinco entregas.
La comparación normal no equivale a la auditoría exacta de ocho líneas del journal.
Los resultados activos se reemplazan entre corridas; SQLite conserva operaciones,
pero no todas las filas históricas de verificación.
La pestaña se crea al conectar, no por lead; cada comando CLI sí inicia un proceso.
No inferir el costo por etapa sin instrumentar.

En los 49 pares donde ambos motores dieron apto: mediana Selenium **10,44 s**,
agent-browser **9,80 s** (~6,1% menos). El orden fijo y la muestra impiden concluir
superioridad general o recomendar migración completa.

## Orden de ejecución

1. **Preservar y reproducir.** Respaldar datos, confirmar entorno, reparar formato
   preexistente y convertir los seis hallazgos en regresiones.
2. **Corregir garantías.** Identidad estricta, historial literal, reserva durable
   entre campañas, observación previa al clic y clasificación de evidencia.
3. **Probar localmente.** Matriz siguiente sobre fixtures, ambos motores y transporte
   real Windows; no tocar Salesforce para inducir fallos.
4. **Hacer visible la evidencia.** Resultados por run, auditoría independiente y
   métricas comparables en Laboratorio.
5. **Validar y pilotar.** Gates completos, auditoría de lectura y pequeño piloto con
   leads distintos y sin reservas. Entregar decisión respaldada por evidencia.

Los archivos y contratos concretos están en `design.md`; `tasks.md` permite avanzar
sin perder el orden de dependencias. Reutilizar tests existentes del laboratorio;
solo crear fixture/módulo nuevo cuando su responsabilidad no tenga lugar adecuado.

## Matriz adversarial obligatoria para la implementación

Cada caso registra motor, versión, semilla/orden, resultado esperado/observado,
guardados, clics efectivos, efecto simulado, journal y evidencia. Los casos
temporales A01–A07 se repiten tres veces por motor con eventos controlados.

| ID | Estímulo | Oráculo y resultado requerido |
| --- | --- | --- |
| A01 | Confirmación positiva inmediata | Un clic/efecto; aceptación atribuida; nunca afirmar entrega |
| A02 | Toast de 50–100 ms entre consultas CLI | Observer conserva evento válido tras desaparecer |
| A03 | Confirmación tardía antes del deadline | Un clic; confirmación sin reintento |
| A04 | Confirmación después del deadline | Ambiguo; reconciliación solo lectura, nunca segundo clic |
| A05 | Toast previo de otro intento/lead | No confirma; baseline identificado |
| A06 | Mismo nodo cambia de texto/error a éxito | Clasificación por evento y contexto; conflicto no resuelto queda ambiguo |
| A07 | Mensaje negativo, genérico, guardado, o error y éxito simultáneos | Cero falsos éxitos |
| A08 | Texto localizado/case/tildes y variante no conocida | Aceptar solo positivos validados; desconocido queda sin confirmar |
| A09 | Toast en shadow root/iframe same-origin; root tardío | Descubrir y capturar; cross-origin inaccesible queda explícito |
| A10 | Botón oculto, disabled, aria-disabled, cubierto o duplicado | Cero clics efectivos; motivo verificable |
| A11 | Usuario cambia pestaña o cierra la del laboratorio | App intacta; no fallback; target perdido bloquea |
| A12 | URL/ID vacío, otro lead, host ajeno, ID 15/18 válido | Solo identidad positiva equivalente permite mutar |
| A13 | Sesión vence o cambia registro durante save/reload/preclick | No operar sobre nuevo registro; ambiguo si ya hubo reserva |
| A14 | Campo vacío, ausente, tardío o labels repetidos | Vacío ≠ ilegible; no leer/escribir campo equivocado |
| A15 | Historial multilínea con texto igual al label o al botón | Preservar texto, espacios autorizados y numeración |
| A16 | Otro actor cambia historial antes de guardar | Releer/recomponer sin borrar; bloqueo si no es verificable |
| A17 | Guardado rechazado o no persistido después de reload | Cero envíos, documentación marcada con fallo |
| A18 | Crash tras doc, reserva, clic o antes de terminal | Reanudar sin repetir línea ni clic; reserva domina |
| A19 | Nueva campaña/archivo/motor y dos runners | Una reserva transaccional; cero duplicaciones |
| A20 | CLI timeout, JSON inválido, daemon/CDP perdido | Sin falso éxito ni fallback de pestaña; conservar bloqueo |
| A21 | Toast sin X o con botón de acción distinto | No pulsar botón arbitrario al cerrar |
| A22 | Reinicio, otra corrida y migración de SQLite | Históricos/estados/evidencias conservados; UI recuperable |
| A23 | Auditoría de línea ausente/duplicada o diferencias entre motores | Reportar discrepancia; no cambiar doc/send por ser apto |
| A24 | Comparación con descartados, fallos y orden A/B–B/A | Denominadores correctos; cero mutaciones; métricas pareadas |

Además: API sin token/run_id inválido, interrupción segura, privacidad de capturas,
redacción de números/nombres y compatibilidad del paquete. La prueba local cuenta
clic y efecto simulado por separado para detectar `element.click()` sobre disabled.

## Comandos y puertas de aceptación

Desde `automation_salesforce`:

```powershell
python harness.py test
python harness.py format-check
python harness.py lint
python harness.py compile
python harness.py business-contracts
```

Comprobar `$LASTEXITCODE` inmediatamente después de cada comando; no ocultar fallos
con pipelines ni declarar exit 0 por el último comando. Registrar el resultado del
test de JS/fixture agregado por el implementador y configurar su ejecución en CI.

Desde la raíz:

```powershell
openspec validate endurecer-confirmacion-whatsapp-laboratorio --strict
openspec validate --changes
```

**Gate local:** cero fallos de regresión y cero falsos éxitos, pérdida de historial,
duplicaciones o navegación ajena en A01–A24. Fixture positiva demuestra efecto
simulado exactamente una vez; negativos/ambiguos quedan diferenciados.
No debe haber skips de escenarios críticos por falta de Edge/Node/CLI: resolver
dependencia o reportar piloto no habilitado.

**Gate lectura real:** comprobar que no hay procesos concurrentes y auditar muestra
de ocho operaciones históricas (cuatro confirmadas, cuatro no confirmadas) con ambos
motores. Guardar resultado por run y comprobar exactamente una ocurrencia de la
línea reservada. Este paso no confirma entrega ni habilita reenvío de esos leads.

**Gate piloto:** preparar selección explícita de nuevos leads de prueba que cumplan
Argentina/preferencia WhatsApp y no tengan reservas históricas. Si no existen leads
de prueba identificados para esta nueva tanda, pedir solo esa selección después de
entregar implementación y evidencia local revisables. No reciclar los 35 anteriores.
Comenzar con uno por motor, distintos; aumentar a tres por motor solo si el primer
par cumple íntegramente. Detener ampliación ante cualquier ambigüedad/error.

**Aceptación final:** evidencia atribuible por operación, UI coherente tras reinicio,
historial íntegro, cero duplicados, resultado no confirmado conservado cuando falte
evidencia. Informar muestra y limitaciones; no fabricar un umbral porcentual de
fiabilidad a partir de seis leads.

## Entrega esperada del otro agente

Reporte con casos ejecutados/PASS/FAIL/pendiente, versiones, comandos y artefactos;
comparación por operación (lectura, escritura, confirmación), no solo velocidad.
Explicar qué hipótesis se confirmaron y cuáles siguen abiertas. Preservar los datos
históricos sin reinterpretarlos. Publicar ZIP/dist únicamente tras los gates y
sin incluir datos reales, tokens, perfiles ni scripts de depuración.

Tracker: proyecto `wolkvox`, tarea `wo-laboratorio-whatsapp-age`; start/stop/log sin
`--push`. Actualizar Graphify al cambiar código y cerrar OpenSpec solo al terminar.
