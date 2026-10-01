# Línea base de cobertura productiva

- Fecha: 2026-10-01 (America/Bogota)
- Commit de referencia: `9a3d1e7`
- Entorno ejecutado: Windows, Python 3.14.3
- Comando: `cd automation_salesforce; python harness.py coverage`
- Resultado de tests: 126 aprobados, 0 fallidos
- Alcance: 22 módulos Python productivos; `tests/` y `harness.py` están excluidos
- Evidencia reproducible local: resumen de terminal y `automation_salesforce/coverage.xml`

## Resultado global

| Métrica | Cubierto | Total | Porcentaje |
| --- | ---: | ---: | ---: |
| Líneas | 820 | 1672 | 49,0% |
| Ramas | 177 | 364 | 48,6% |

Esta es una línea base, no un gate aprobado. Está por debajo de los objetivos de
85% de líneas y 75% de ramas globales definidos en el diseño.

## Resultado por archivo

| Archivo | Líneas | Ramas cubiertas |
| --- | ---: | ---: |
| `browser_factory.py` | 47,2% | 14,3% (2/14) |
| `comment_reader.py` | 89,0% | 66,7% (8/12) |
| `comment_writer.py` | 46,5% | 33,3% (14/42) |
| `correction_loader.py` | 90,9% | 100% (6/6) |
| `leads_ui.py` | 100% | N/A |
| `local_audit.py` | 45,8% | 100% (2/2) |
| `local_report.py` | 90,5% | 50% (1/2) |
| `open_persistent_browser.py` | 0% | 0% (0/8) |
| `productivity_metrics.py` | 100% | 83,3% (10/12) |
| `queue_loader.py` | 92,5% | 83,3% (15/18) |
| `report_reader.py` | 81,0% | 71,6% (73/102) |
| `run_comment_assisted.py` | 33,9% | 25% (1/4) |
| `run_comment_read_only.py` | 27,7% | 25% (1/4) |
| `run_corrections.py` | 18,6% | 8,3% (1/12) |
| `run_document_queue.py` | 37,3% | 42% (21/50) |
| `run_leads_ui.py` | 33,3% | 50% (3/6) |
| `run_read_only.py` | 0% | 0% (0/2) |
| `run_report_read_only.py` | 39,0% | 75% (3/4) |
| `salesforce_session.py` | 44,8% | 0% (0/2) |
| `snapshot_store.py` | 90,0% | 100% (4/4) |
| `ui_server.py` | 60,3% | 42,9% (12/28) |
| `verificar_pc.py` | 0% | 0% (0/30) |

## Comprobación de alcance

El arnés compara automáticamente las clases del XML con todos los `*.py` productivos
del directorio. La ejecución confirmó los 22 módulos y fallará si se omite cualquiera.
La lista crítica identifica de forma adicional escritura, correcciones, servidor,
persistencia y privacidad; ningún archivo crítico fue omitido.

Las brechas prioritarias observadas son `run_corrections.py` (18,6%/8,3%),
`salesforce_session.py` (44,8%/0%) y `ui_server.py` (60,3%/42,9%). Las tareas 2.2,
2.3 y 2.4 están destinadas a caracterizar esas rutas antes de activar umbrales.
