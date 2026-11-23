# Diseño: tiempo-total-informes

## Context

`productivity_metrics.summarize_results` ya calcula `cycle_elapsed_seconds`
para Documentar y Cierre, y `laboratory_metrics` para el laboratorio. Los
JSON lo tienen; la UI y la consola no lo muestran. Distribución no escribe
métricas de ciclo en absoluto (solo `elapsed_seconds` por lead).

## Goals / Non-Goals

**Goals:**
- Tiempo total visible en los cuatro informes de fin de proceso.
- Cero regresión: si falta la métrica, los informes se ven como hoy.
- Métricas de distribución compatibles con el formato existente.

**Non-Goals:**
- No se agregan métricas nuevas (throughput, %aprovechamiento, etc.).
- No se toca la mecánica de Salesforce ni formatos de cola.
- No se cambia el cálculo de `cycle_elapsed_seconds` existente.

## Decisions

1. **Reusar `summarize_results` de `productivity_metrics` para distribución.**
   El formato de métricas ya es el de la casa. Alternativa descartada:
   un writer ad-hoc divergente.
2. **Persistir métricas de distribución en `cola_distribucion_activa.metricas.json`**
   junto a `cola_distribucion_activa.resultado.json`. Alternativa: anidar
   en el resultado — rechazada para no romper consumidores del resultado.
3. **La UI lee métricas vía los endpoints/archivos ya existentes**
   (`/api/monitor/bot-file` o el endpoint del proceso). Si cierre no expone
   su métrica, se agrega lectura — sin endpoint nuevo si basta el genérico.
4. **Formato de display**: segundos totales si < 60, `Mm Ss` en adelante;
   una sola línea adicional, sin re-layout del informe.

## Risks / Trade-offs

- [Distribución corre por reanudación con resultados previos] →
  `cycle_elapsed_seconds` mide la corrida actual; el resumen por lead
  acumula lo procesado. Se documenta en el propio archivo.
- [Métricas escritas en disco vs. servidor en otra carpeta] → reutilizar
  la misma ruta que ya usa el runner; sin rutas nuevas.
- [Alert de cierre sin endpoint de métricas] → verificar primero; si no
  existe, exponerlo replicando el patrón del de documentación.

## Migration Plan

Aditivo: un archivo nuevo y líneas nuevas de display. Rollback = revert.
