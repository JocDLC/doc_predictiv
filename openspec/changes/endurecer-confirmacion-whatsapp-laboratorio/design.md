## Context

Continuación SDD del laboratorio aprobado. El usuario solicita un plan ejecutable por otro agente y verificaciones previas.
No alterar el trabajo sin commit existente ni los cambios OpenSpec ajenos.

Diagnóstico reproducible: `diagnostico_adversarial.py` y `diagnostico-resultados.json`.
El 17/11/2026: 686 tests existentes pasan; lint/compile pasan; format-check falla en
`agent_browser.py`, `lab_debug_eval.py` y `ui_server.py`. Las sondas locales usan el JS
productivo en Node con DOM mínimo y el runner con fakes: 8 PASS, 6 FAIL.
No equivalen a una fixture de navegador ni a un envío real.

El gate adicional `business-contracts` ejecutó 32 tests y reportó 19 fallos y
9 errores por hash discrepante de un HTML técnico protegido de `.archify/`.
Ver `business-contracts.log` y PLAN.md. Ese archivo no se modificó en esta sesión.
Reconciliar la procedencia sin rebaselinar automáticamente ni debilitar tests.

El journal real es `automation_salesforce/ui_output/laboratorio/laboratorio.sqlite3`.
Contiene 35 operaciones: documentación confirmada en las 35; cinco envíos registrados
como confirmados y treinta sin confirmación. Ninguna operación conserva evidencia en
`evidence`. No es posible reconstruir retrospectivamente por qué faltaron 30 toasts.
Tampoco se puede certificar la entrega de los cinco registros marcados confirmados.

La comparación disponible contiene 80 leads y 160 evaluaciones, 79/80 coincidencias de
estado. El desacuerdo fue `sin_boton_whatsapp` en Selenium. Para los 49 pares aptos,
medianas: Selenium 10,44 s y agent-browser 9,80 s (~6,1% menos); el orden fijo
Selenium primero introduce efecto caché. La mediana anterior de 9,9/9,2 incluía descartados.
La comparación normal solo comprueba elegibilidad, lectura y botón. No compara
automáticamente el texto contra la línea reservada del journal.

## Goals / Non-Goals

**Goals:** confirmar únicamente una respuesta positiva atribuible a la operación;
conservar historial literal; impedir duplicaciones; diagnosticar respuestas breves,
tardías, negativas o ambiguas; entregar métricas y evidencia consultables por corrida.

**Non-Goals:** sustituir todo Selenium; prometer entrega al teléfono a partir de un
toast; reenviar los 30 casos históricos; modificar el Monitor silenciosamente;
ampliar a otros países; optimizar pausas sin evidencia. No agregar servicios remotos
ni enviar contenido de Salesforce a modelos externos.

## Decisions

### 1. Corregir identidad e historial antes del detector

`verify_lead` y `send_for_lead` hoy permiten ID vacío mediante `if opened_id and ...`.
Exigir identidad positiva, origen Salesforce configurado y objeto Lead, después de
navegar, antes de guardar, tras recarga y antes del clic. Comparar IDs Salesforce
15/18 mediante canonicalización válida; nunca convertirlos arbitrariamente a minúsculas.
Si la identidad falta, cambia o no es verificable: bloquear sin mutación.

`textAfterLabel` actualmente elimina líneas de contenido que coincidan con textos
asistivos. Usar estructura DOM para excluir botones/labels, y leer el valor dedicado
sin aplicar filtros semánticos al historial. Distinguir campo vacío, ausente, oculto,
ambiguo y aún no renderizado. Probar múltiples campos iguales en paneles diferentes.

### 2. Capturar antes del clic y clasificar después

Separar captura de evidencia DOM, clasificación pura y decisión del runner.
Proponer contrato de laboratorio (nombres adaptables, garantías obligatorias):

```
arm_confirmation(context) -> observation_id
click_whatsapp(context) -> clicked | blocked | ambiguous
wait_confirmation(observation_id, deadline) -> ConfirmationEvidence
dispose_confirmation(observation_id)
```

`context` contiene run/operation, ID esperado, target de pestaña, origen y un nonce
local. `ConfirmationEvidence` contiene versión, outcome, reason, timestamps UTC,
tiempos monotónicos relativos, identidad observada, source, fingerprint del baseline,
eventos posteriores y fragmento redactado/clasificación. El nonce local delimita la
ventana de captura: NO demuestra que Salesforce haya correlacionado el evento.

Antes de reservar el clic, instalar un observador de mutaciones y tomar baseline.
Recorrer documento, shadow roots abiertos y frames same-origin soportados; descubrir
nuevos roots durante la ventana. Guardar un buffer acotado en la pestaña para que un
toast breve no dependa de la cadencia de CLI. Consumir cambios de nodos existentes,
texto, visibilidad y nodos removidos; fijar un límite para no capturar páginas enteras.
Una recarga/invalidation/target cerrado invalida la observación.

Después de validar el contexto, reservar el clic de forma duradera; revalidar identidad
y botón dentro de la misma acción que realiza el clic. Ejecutar exactamente un clic.
No asumir actionability de CLI: el código actual llama `element.click()` mediante eval.
Comprobar visible, habilitado, `aria-disabled`, hit testing y unicidad. Preferir acción
nativa sobre un localizador estable solo si se demuestra que conserva identidad y
no introduce una carrera; si no, acción DOM protegida y probada en fixture.

Aceptar solo mensajes positivos específicos respaldados por captura real redactada
(el comentario de código contiene `Message sent to Whatsapp! Please follow the
sending status of this message.`; sigue siendo una hipótesis hasta validarla).
Rechazar negaciones/error, estados genéricos, avisos de guardado, previos al clic,
contenedores que agreguen error y éxito, eventos de otra operación y múltiples
señales contradictorias. La falta de ID en el toast exige contexto exclusivo y
estable de pestaña/operación; si no se puede atribuir, resultado ambiguo.

Una respuesta `accepted_by_salesforce` se muestra como “Aceptado por Salesforce”,
nunca “entregado”. Preservar compatibilidad con `send_status=confirmado`, añadiendo
alcance de confirmación explícito. `no_confirmado` permanece ambiguo aunque se
documentó el intento. Una respuesta negativa también impide reintento automático
después de reservar el clic; la revisión manual se documenta aparte.

El deadline incluye latencia de cada llamada CLI; no sumar un timeout completo de
comando a cada vuelta. No aumentar ciegamente 15 s. Medir primero.
Desconectar observadores al cerrar operación; cerrar exclusivamente el botón X del
toast atribuido, nunca el primer botón arbitrario.

Alternativas descartadas: ampliar regex, aumentar sleeps como única solución,
inferir envío por `Se envía WhatsApp`, por desaparición del botón o por HTTP 200 sin
contrato de negocio. La API oficial sigue sin autorización/configuración demostrada.

### 3. Persistencia y exclusión entre campañas

Mantener el journal existente y sus operaciones históricas intactos. Agregar una
reserva de envío única por `(org_origen, lead_id_canonico, canal)` dentro del
laboratorio, con transacción SQLite atómica e índice único. Adquirirla antes del
clic; otro runner/motor/campaña no puede adquirirla. El precheck anterior a la
documentación también consulta esta reserva, para no documentar un nuevo intento
de un envío ya bloqueado. La transacción final protege contra carreras.

Migrar reservas desde operaciones confirmadas, no_confirmadas, indeterminadas o con
clic reservado. Si una operación histórica no tiene origen recuperable de su cola,
conservar un bloqueo conservador por lead en esta instalación y exigir revisión;
no asignar automáticamente un origen nuevo si config cambió.
Guardar `evidence` antes del cierre terminal con un único commit lógico.
Crash en cualquier punto posterior a reservar nunca provoca un segundo clic.
Para fallos antes de reservar, permitir reanudación que reconozca la línea ya
persistida sin duplicarla y verifique nuevamente la identidad.

No se promete exclusión con acciones manuales ni con el Monitor, cuyo journal es
distinto. Mantener el lock global del servidor y pausar tareas automáticas
concurrentes durante el piloto. Extender la exclusión al Monitor requiere su propio
alcance, no hacerlo implícitamente.

### 4. Resultados consultables y métricas honestas

Hoy `_start_laboratorio` elimina el JSONL activo; SQLite conserva operaciones/runs,
pero no todos los resultados de verificación. La UI lee JSONL, no cada operación
del journal. Por tanto la afirmación anterior “todo viene del journal” era incorrecta.

Persistir resultados por run: `laboratorio_<run_id>.resultado.jsonl` y `.metricas.json`.
Conservar alias activo compatible; nunca eliminar resultados de runs anteriores.
Agregar a `/api/laboratorio/results` selección opcional `run_id` validada y
enriquecimiento con doc/send/evidence desde journal; conservar `results` existente.
Reutilizar status para listar runs o ampliar su respuesta de forma aditiva.
No permitir traversal ni mezclar runs de campañas distintas por lead/engine.
En UI mostrar selección de corrida, modo, leads únicos/evaluaciones y ejes separados
de documentación/aceptación/pendiente de revisión. La propuesta de intento calculada
en modo prueba no debe parecer una línea escrita.

Auditoría cruzada: operación de solo lectura sobre líneas exactas reservadas;
comparar normalización de espacios permitida, número de ocurrencias (exactamente una),
identidad y, si existe snapshot previo, preservación del historial. Hash previo solo
no permite reconstruirlo. Persistir por motor el resultado y su alcance. No convertir
`apto` de comparación normal en “persistencia auditada”.

Métricas por run/mode/engine/status: elegibles navegados separados de descartados,
pares comunes con mismo estado, desacuerdos, p50/p95 nearest-rank, delta pareado,
fallos incluidos por separado. Separar cold start/conexión y sesión caliente.
`send_click` en prueba solo detecta botón; migrar a `button_check` con lectura legacy.
Alternar orden A/B y B/A para lectura, con semilla/orden guardados. Para envíos,
grupos distintos y comparables, nunca mismos leads.

### 5. Capas de pruebas y orden de trabajo

Primero convertir cada fallo de las sondas en regresión en los tests existentes.
El script diagnóstico registra hallazgos; no es la suite final. Mantener expectativas,
no adaptar tests al bug. Las pruebas JS deben ejecutar el JS productivo con DOM real
en fixture local para geometría, shadow DOM, iframes y MutationObserver.
Usar Selenium ya instalado para provisionar una fixture cuando sea práctico,
manteniendo ambos adaptadores de producción para evaluar acciones.

Crear `tests/fixtures/laboratorio_whatsapp.html` solo si no hay fixture equivalente.
Servidor loopback, datos sintéticos, contadores de guardados/clics/efectos reales
simulados y señales explícitas para controlar relojes; no depender de sleeps frágiles.
Navegador con perfil temporal y puerto libre exclusivo; no reutilizar 9222/9333
sin comprobar propiedad. Probar tres repeticiones de la matriz temporal en cada
motor y garantizar limpieza de procesos/pestañas propios.
Reloj falso para unidad; eventos/handshakes para integración.

Separar job CI determinístico (Python + Node fijados) de integración Windows con
Edge y agent-browser 0.43.0. CI actual usa Python 3.12 y el entorno local Python
3.14.3; verificar compatibilidad con ambos. Node 20.19 pertenece al harness OpenSpec;
agent-browser requiere >=22 (local v24.20.0). No cambiar globales ni instalar latest.

## Risks / Trade-offs

- [Faltan capturas históricas] → mantener causa desconocida; instrumentar el próximo
  piloto controlado. No fabricar fixtures “reales” a partir de hipótesis.
- [Un toast no identifica lead] → exclusividad/contexto estable y bloqueo ante
  ambigüedad; éxito de UI no implica entrega al destinatario.
- [Observer no ve un frame cross-origin] → diagnóstico explícito, nunca éxito por
  ausencia de error. No cambiar permisos del navegador.
- [Ambos motores comparten lógica] → Selenium ayuda a detectar divergencias DOM,
  pero no es un oráculo independiente. La fixture tiene un contador de efecto propio.
- [Reserva global bloquea nuevos contactos legítimos] → alcance conservador del
  piloto; futuros recontactos requieren flujo explícito, nunca reset automático.
- [Pruebas dinámicas pasan localmente y fallan en CI] → señalar capas/skips y versiones;
  no presentar un skip como PASS.

## Migration Plan

Respaldar SQLite consistentemente con `sqlite3.backup` y copiar colas/resultados
antes de migrar. Probar migración idempotente y rollback en copias temporales.
Una vez registrados nuevos clics, nunca volver a un backup que pierda reservas.
Rollback conservador: desactivar envío real y mantener journal/evidencia; permitir
solo lecturas. No volver al envío Selenium como bypass de bloqueos.

Tras aprobar puertas de validación: actualizar CHANGELOG/MEMORY (incluido path correcto),
regenerar ZIP con `python packaging/build_zip.py --sync-dist`, comprobar exclusión
de config/datos reales y del debug script de producción, actualizar Graphify/Gantt.
No archivar hasta completar las tareas y registrar el resultado del piloto.

## Open Questions

- ¿Qué texto/estructura/variante produce realmente Salesforce para éxito y error?
  Resolver con evidencia redactada del próximo piloto, no suponiendo que los 30 fallaron.
- ¿Existe estado de negocio consultable para reconciliar mensajes históricos?
  Inspección solo lectura; si no existe contrato demostrable, quedan sin confirmar.
- ¿Hay frames o shadow roots cerrados involucrados? Resolver en fixture y captura
  real. No rebajar el criterio de confirmación para lograr más verdes.
