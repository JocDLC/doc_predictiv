# Propuesta: documentar-automatico-guardado

## Objetivo

Escalar la documentación predictiva de "supervisada por Lead" a "lote automático":
el bot abre cada Lead, calcula el próximo `N INT` desde Salesforce, compone el
texto, lo carga en `Otra información`, **pulsa Guardar** y **verifica la
persistencia releyendo el campo**. La UI del documentador permite seleccionar
qué Leads procesar y muestra el estado de cada uno.

> Decisión del operador (2026-09-17): se levanta la restricción "nunca Guardar"
> tras pilotos supervisados exitosos (1 + 3 + 8 Leads verificados a mano). El
> resto de restricciones se mantiene: sin reasignar, sin cerrar, sin cambiar
> estado del Lead, sin tocar otros campos.

## Alcance

1. **Modo automático en el runner** (`run_document_queue.py --auto`): procesa
   la cola completa sin pausas; por Lead: preparar → Guardar → reabrir →
   releer → registrar `guardado`/`error`. El modo supervisado actual queda
   disponible como comportamiento por defecto.
2. **Verificación post-guardado**: el estado `guardado` se confirma releyendo
   `Otra información` tras recargar el registro, no se asume.
3. **UI de estados y selección** en `documentador_predictivo.html`:
   checkboxes por Lead, exportación de la selección como cola, importación del
   `*.resultado.json` para marcar `documentado por bot`, y vista de tres
   estados (bot / manual / pendiente).
4. **Ejecución desatendida**: corre en la ventana del navegador persistente
   (se puede minimizar); no headless porque la sesión vive en ese perfil.
5. **Trazabilidad y corrección local**: la pantalla conserva el comentario nuevo
   preparado para el flujo manual y, cuando documenta el bot, una copia local del
   campo completo `Otra información` confirmada tras releer Salesforce. El operador
   puede revisar y corregir esa copia desde la pantalla.
6. **Aplicación segura de correcciones**: antes de reemplazar el campo completo
   con una corrección local, el bot relee Salesforce y solo guarda si coincide con
   la última copia conocida por la aplicación. Una diferencia se registra como
   conflicto y nunca se sobrescribe automáticamente.

## Fuera de alcance

- Editar cualquier otro campo o realizar acciones de negocio.
- Reprocesar Leads ya documentados (la cola se regenera excluyéndolos).
- Notificaciones o reportes externos; todo sigue local.
- Guardar snapshots, textos de comentarios o datos de clientes en Git, consola,
  logs, capturas o servicios externos.

## Riesgos aceptados

- Escritura automática en Salesforce: mitigada por verificación post-guardado
  y por el piloto previo. No hay deshacer automático; los errores quedan
  registrados para revisión manual.
