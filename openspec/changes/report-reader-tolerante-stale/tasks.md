# Tasks: report-reader-tolerante-stale

## 1. Extracción materializada

- [ ] 1.1 `report_reader.py`: el scan devuelve los datos de la fila (nombre, lead_id, fecha_creacion y campos usados) materializados dentro de la misma evaluación JS que localiza la fila — sin exportar `WebElement`.
- [ ] 1.2 Lecturas auxiliares del scan (scroll/otras) pasan por los helpers tolerantes de `comment_reader`.
- [ ] 1.3 Tests con driver que simula handles stale: el scan devuelve datos materializados sin propagar la excepción.

## 2. Reintento acotado y error con contexto

- [ ] 2.1 Reintentar el scan (2-3 intentos) ante elemento/frame muerto antes de declarar `bandeja_error`.
- [ ] 2.2 `bandeja_error` registra bandeja + excepción + intentos (campo estructurado o string con contexto).
- [ ] 2.3 `lead_monitor.py`: la excepción de lectura no aborta la toma ni el ciclo — se registra y sigue.
- [ ] 2.4 Tests del reintento y del `bandeja_error` con contexto.

## 3. Cierre

- [ ] 3.1 Suite completa + lint + format-check + compileall.
- [ ] 3.2 Verificación in situ: ciclo del monitor (o sonda del scan) contra la bandeja real post-refresh.
- [ ] 3.3 CHANGELOG `[Sin publicar]`, `graphify update .`, log en Gantt, `openspec validate --changes`.
