## Context

La UI actual es un HTML local generado por `run_leads_ui.py`. La automatización
existente ya sabe leer el historial de `Otra información`, componer intentos de
Wolkvox y cargar el editor, pero se detiene antes de Guardar. El nuevo flujo debe
conservar la misma UI visible y procesar un lote seleccionado sin cerrar la lista.

## Goals / Non-Goals

**Goals:**

- Seleccionar Leads en la UI actual y solicitar documentación por lote.
- Ejecutar un Lead por vez, abrir su registro Salesforce en una pestaña adicional,
  conservar el historial de `Otra información`, agregar los intentos y guardar.
- Reflejar estados y errores en la UI sin exponer contenido de comentarios.
- Mantener una alternativa manual disponible para cualquier Lead no documentado.

**Non-Goals:**

- Crear una segunda aplicación o interfaz de usuario.
- Editar campos distintos de `Otra información`, convertir Leads, reasignar,
  cambiar estados o cerrar registros.
- Automatizar login, 2FA o datos de credenciales.
- Reintentar automáticamente una escritura que haya fallado la verificación.

## Decisions

### Puente local integrado en el runner

`run_leads_ui.py` iniciará un servidor loopback temporal junto a la UI existente.
El HTML se servirá desde ese proceso y usará endpoints locales para enviar la
selección y consultar estados. No se incorpora una aplicación ni ventana nueva:
el único panel visible sigue siendo la lista actual.

Se descarta dejar el HTML como `file://` porque el navegador no puede iniciar
Python/Selenium desde un botón. También se descarta un servicio persistente: el
puente vive únicamente mientras el runner está abierto.

### Confirmación explícita del lote

El botón muestra el número de Leads elegidos y exige confirmación explícita antes
de encolar. Esa confirmación autoriza guardar solamente esos IDs, una vez por
ejecución. El worker rechaza IDs que no formen parte del lote confirmado.

### Worker secuencial y pestañas Salesforce

El worker reutiliza el perfil/sesión Selenium existente. Para cada Lead abre una
pestaña Salesforce adicional, lee `Otra información`, compone los intentos,
verifica el valor del editor y pulsa exclusivamente el control de Guardar del
campo. Al completar o fallar, cierra solo la pestaña de trabajo y conserva la UI.

Se elige un worker secuencial para evitar colisiones de sesión, errores de DOM y
doble documentación. No habrá paralelismo.

### Estados y recuperación

Cada Lead seleccionado tiene estado local `pendiente`, `procesando`,
`documentado` o `error`. Los resultados se guardan por Lead sin texto de
comentarios ni datos personales. Un error deja el Lead seleccionado visible con
la acción manual disponible; el worker continúa con el siguiente Lead.

### Seguridad de escritura

Antes de Guardar se verifica que el editor contiene exactamente el historial
original más los intentos compuestos. El worker no guarda si falla la lectura, la
composición, la localización del editor o la verificación. Los logs usan IDs
enmascarados y métricas; no registran contenido, nombres, teléfonos ni correos.

## Risks / Trade-offs

- [Lightning cambia el DOM del botón Guardar] → selectores acotados al editor de
  `Otra información`, prueba estática y prueba manual de un Lead antes de lotes.
- [Doble clic o refresco de UI] → el backend rechaza trabajos activos y persiste
  IDs documentados/activos para la ejecución.
- [Sesión Salesforce expira] → marca el Lead actual como error, conserva los
  restantes como pendientes y permite retomar manualmente.
- [El operador necesita corregir un caso] → no se bloquea el flujo manual ni se
  elimina la opción de abrir el Lead.

## Migration Plan

1. Mantener la ejecución actual de UI como modo de lectura si el puente no se
   inicia correctamente.
2. Validar con un único Lead de prueba y confirmar el valor guardado.
3. Validar un lote pequeño con errores simulados y documentación manual.
4. Habilitar lotes operativos solo después de las pruebas y aprobación explícita.

## Open Questions

- Ninguna para la primera implementación: el lote se confirma con un diálogo que
  muestra el conteo y los errores no se reintentan automáticamente.
