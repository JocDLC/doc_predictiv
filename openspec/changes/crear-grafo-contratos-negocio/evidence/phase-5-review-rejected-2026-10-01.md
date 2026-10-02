# Revisión no aprobada del primer prototipo — Fase 5

Fecha: 2026-10-01

## Resultado

El primer artefacto `documentador-business-contracts.html` no fue aprobado por
el usuario y no debe presentarse como vigente.

## Causas registradas

1. La visualización fue construida con una plantilla HTML propia y no con
   Archify, por lo que no conservó la calidad visual del gráfico técnico.
2. El recorrido lineal mezcló dos procesos diferentes y dificultó entender el
   movimiento de la información.
3. El contrato de carga anunció XLSX aunque la aplicación vigente acepta
   `.csv,.txt`, usa lectura de texto y muestra un error cuando no encuentra IDs
   de Lead en el contenido cargado.

## Decisión de corrección

- Generar un Workflow v2 nativo de Archify.
- Separar Salesforce → Wolkvox de Wolkvox → Salesforce.
- Mostrar la bifurcación de documentación manual o mediante bot.
- Describir únicamente CSV como formato operativo vigente.
- Conservar el prototipo rechazado solo como evidencia histórica.
