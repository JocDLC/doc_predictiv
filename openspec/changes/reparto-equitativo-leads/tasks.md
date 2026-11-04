# Tareas — reparto-equitativo-leads

1. [x] `distribucion_loader.py` (o módulo nuevo `reparto_equitativo.py`):
   función pura `repartir(leads, trabajan_hoy)` → `{lead_id: persona, …}` con
   metadatos (`se_queda`/`se_mueve`, cupos). Partes iguales + resto de a uno;
   leads cuyo auxiliar trabaja se conservan hasta el cupo; excedentes y de
   auxiliares ausentes cubren déficits (orden estable por fila del archivo).
2. [x] Persistencia equipo del día: `distribucion_equipo` en estado
   (`monitor_store` o archivo propio bajo `ui_output/`) + endpoints
   `GET/PUT /api/distribucion-equipo` en `ui_server.py` (alta, baja, tilde
   "trabaja hoy"). Reusar validación de personas del equipo del monitor si aplica.
3. [x] Endpoint `POST /api/distribucion/reparto` (o cómputo en cliente si la
   BD ya está parseada en la UI — decidir: preferir server-side para testear
   el algoritmo con unittest): recibe filas parseadas + equipo tildado →
   devuelve destino por lead + `se_queda` + cupos.
4. [x] UI: modo "Reparto equitativo" en Distribuir leads — panel de equipo
   (agregar/quitar/tilde persistente), botón "Calcular reparto", columna
   "Acción" (se queda / se mueve) en la vista previa, resumen de cupos.
5. [x] Lista WhatsApp: sección/tabla "Reasignación WhatsApp" con
   `lead → nueva persona` para filas con `Preferred mean of contact`
   conteniendo "whatsapp" (case/diacríticos insensible). Visible tras el
   reparto; accesible también en resultados.
6. [x] Tests: reparto (partes iguales, resto, se queda vs se mueve, auxiliar
   ausente, vacíos, determinismo), endpoints equipo + reparto, flag WhatsApp
   por alias de columna.
7. [x] Verificación: `python harness.py test`, `ruff check`, sync a `dist/`,
   `openspec validate --changes`, `graphify update .`, log en Gantt.
7.1. [x] Exportación Excel del reparto: `POST /api/distribucion/exportar`
   (.xlsx en memoria con openpyxl — distribución completa con acción por
   lead y lista WhatsApp para GTR) + botones "Descargar … (.xlsx)" en la
   vista previa tras "Calcular reparto".
8. [x] Reparto entrelazado por secuencia (no por bloques): `se_queda`
   espaciado uniforme dentro de la sublista propia + bolsa `se_mueve`
   asignada round-robin cíclico por orden de archivo. Mismo mínimo de
   reasignaciones; tests del patrón documentado (A:1,4,7,10 · B:2,5,8,11 ·
   C:3,6,9,12) y del espaciado de la conservación.
9. [x] Verificación de la extensión: `python harness.py test`, `ruff check`,
   sync a `dist/`, `openspec validate --changes`, `graphify update .`, log
   en Gantt.
