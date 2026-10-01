# Tareas: medir-productividad-documentacion

## Fase 1 — Instrumentación segura

- [x] 1.1 Añadir reloj monotónico por Lead al runner automático.
- [x] 1.2 Extender el resultado con `elapsed_seconds`, sin contenido de cliente.
- [x] 1.3 Crear generador de métricas agregadas del lote.
- [x] 1.4 Cubrir éxito, error y redondeo con tests de regresión. (103 tests OK, Ruff OK.)

## Fase 1b — Diagnóstico por etapas

- [x] 1.5 Medir por Lead la duración de navegación, comprobación de duplicado,
      lectura del campo, editor, guardado, verificación y snapshot; contar las
      recargas de verificación.
- [x] 1.6 Agregar `stage_seconds_mean` y `verify_reloads` al resumen del lote y
      al aviso de cierre de la UI.
- [x] 1.7 Cubrir con tests etapas completas, parciales (`duplicado`/`error`) y
      las medias agregadas. (111 tests OK, Ruff OK, JS OK.)

## Fase 2 — Prueba controlada

- [ ] 2.1 Preparar una cola de exactamente 10 Leads pendientes autorizados.
- [ ] 2.2 Obtener confirmación explícita antes de la escritura real.
- [ ] 2.3 Ejecutar el bot, verificar estados en Salesforce y conservar solo
      `*.resultado.json` y `*.metricas.json` locales.
- [ ] 2.4 Revisar tamaño de muestra, éxitos/errores y valores atípicos.

## Fase 3 — Presentación de productividad

- [x] 3.1 Crear HTML local autocontenido de resultados.
- [x] 3.2 Mostrar rangos declarados (manual) y muestra medida (bot) de forma
      diferenciada.
- [x] 3.3 Calcular ahorro, reducción porcentual y capacidad por hora con
      fórmulas visibles.
- [x] 3.4 Verificar visualización, privacidad y sintaxis.
- [x] 3.5 Mostrar `elapsed_seconds` individual en la lista general y cola del
      bot, con clasificación verde/naranja/rojo contra el promedio del lote.
- [x] 3.6 Pruebas de límites: igual al promedio, hasta +20% y mayor a +20%;
      `error`/`duplicado` no reciben clasificación. (107 tests OK, Ruff OK,
      JS OK.)

## Fase 4 — Cierre

- [ ] 4.1 Ejecutar suite completa y Ruff.
- [ ] 4.2 Actualizar Graphify y revisar cambios.
- [ ] 4.3 Solicitar autorización antes de commit/push.