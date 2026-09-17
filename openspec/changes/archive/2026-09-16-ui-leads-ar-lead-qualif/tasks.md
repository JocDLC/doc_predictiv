# Tareas: ui-leads-ar-lead-qualif

> Alcance: lectura Salesforce y UI local. No se permite editar, guardar,
> reasignar, cerrar ni modificar ningún Lead.

## Fase 0 — Preflight y privacidad

- [x] 0.1 Confirmar los artefactos de este cambio y que el reporte configurado es
      `00O67000006cstjEAA`.
- [x] 0.2 Añadir a `.gitignore` el directorio local de UI e instantáneas con datos
      personales (`automation_salesforce/ui_output/`).
- [x] 0.3 Añadir la configuración de etiquetas/alias de campos sin incluir datos
      de clientes ni credenciales.

## Fase 1 — Extracción segura desde el reporte

- [x] 1.1 Escribir tests sintéticos para resolver columnas por etiquetas y alias,
      sin índices fijos.
- [x] 1.2 Extender el lector para extraer los campos disponibles solo de filas
      visibles con propietario exacto `AR_LEAD_QUALIF`.
- [x] 1.3 Escribir tests para que una columna ausente produzca el marcador "No
      disponible en bandeja" y no dispare consultas adicionales.
- [x] 1.4 Mantener orden visible, deduplicar por Lead ID cuando exista y evitar
      imprimir datos personales en consola o logs.

## Fase 2 — UI local por secciones

- [x] 2.1 Escribir tests de generación HTML con escape de valores provenientes de
      Salesforce y sin recursos externos.
- [x] 2.2 Crear el generador de UI local con tarjetas divididas en Información
      cliente, Información general, Síntesis, Cualificación e Información sobre
      la fuente de lead; incluir Descripción y Otra información cuando estén
      disponibles en bandeja.
- [x] 2.3 Añadir buscador y filtros locales de País, Estado de candidato y
      Vehículo de interés construidos desde los valores visibles.
- [x] 2.4 Agregar enlaces "Abrir Lead" solo para IDs Salesforce válidos y prueba
      que garantice que no hay controles de edición o guardado.

## Fase 3 — Runner, pruebas y validación manual

- [x] 3.1 Crear `run_leads_ui.py`: login/2FA manual, lectura del reporte,
      generación local de la UI y apertura en navegador.
- [x] 3.2 Ejecutar tests unitarios y Ruff; corregir todos los errores. Resultado:
      47/47 tests correctos y Ruff sin errores.
- [x] 3.3 Prueba manual con Salesforce: comparar conteo y algunos campos de la UI
      con la bandeja visible, sin modificar datos.
- [x] 3.4 Confirmar que la instantánea y la UI local no aparecen en `git status`.
      Verificado mediante `git check-ignore` para `ui_output/`.
- [x] 3.5 Actualizar resultados, Graphify y validar OpenSpec desde una terminal
      con la CLI disponible.
