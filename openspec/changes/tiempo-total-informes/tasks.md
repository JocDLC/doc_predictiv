# Tasks: tiempo-total-informes

## 1. Distribución: métricas de ciclo

- [ ] 1.1 `run_distribucion_queue.py`: medir el inicio del ciclo y escribir `cola_distribucion_activa.metricas.json` con `cycle_elapsed_seconds`, conteos por estado y per-lead elapsed (reusar `productivity_metrics.summarize_results` o su patrón).
- [ ] 1.2 Persistir las métricas acumuladas si la corrida muere o se detiene a mitad (escritura en `finally`/al corte).
- [ ] 1.3 Tests del archivo de métricas de distribución (formato + `cycle_elapsed_seconds` correcto).

## 2. Consola: resúmenes con tiempo total

- [ ] 2.1 `run_document_queue.py`: imprimir el tiempo total del ciclo en el "Resumen" final.
- [ ] 2.2 `run_close_queue.py`: ídem.
- [ ] 2.3 `run_distribucion_queue.py`: ídem (leyendo las métricas de 1.1).
- [ ] 2.4 `run_laboratory_queue.py`: ídem (leyendo `laboratory_metrics`).
- [ ] 2.5 Tests del resumen de consola de los 4 runners.

## 3. UI: informes con tiempo total

- [ ] 3.1 `productivityMessage()`: línea con `cycle_elapsed_seconds` (formateado) en el alert de Documentar; tolerante a métrica ausente.
- [ ] 3.2 Alert de Cierre: exponer la métrica de cierre (verificar si el endpoint ya la sirve; si no, replicar el patrón del de documentación) y mostrarla.
- [ ] 3.3 Informe de Distribución: mostrar el tiempo total del ciclo desde `cola_distribucion_activa.metricas.json`.
- [ ] 3.4 Informe de Laboratorio: mostrar `cycle_elapsed_seconds` en la tarjeta/resumen final.
- [ ] 3.5 Test/manual check de que un JSON sin `cycle_elapsed_seconds` no rompe ningún informe.

## 4. Cierre

- [ ] 4.1 Suite completa + lint + format-check + compileall.
- [ ] 4.2 CHANGELOG `[Sin publicar]`, `graphify update .`, log en Gantt.
- [ ] 4.3 `openspec validate --changes` y sync/archive al aprobar el usuario.
