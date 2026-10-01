# Propuesta: medir-productividad-documentacion

## Objetivo

Medir de forma reproducible el tiempo operativo del bot de documentación y
presentar el impacto de la aplicación frente a los flujos manuales. La medición
no debe exponer datos de clientes ni cambiar el comportamiento de Salesforce.

## Línea base declarada

| Modalidad | Tiempo por Lead | Origen |
|---|---:|---|
| Documentación manual sin aplicación | 40–55 segundos | estimación operativa del equipo |
| Aplicación + documentación manual | 23–29 segundos | observación operativa del equipo |
| Aplicación + bot | por determinar | prueba controlada con datos reales autorizados |

Los dos primeros valores se presentan como rangos declarados, no como
cronometrajes instrumentados.

## Alcance

1. Registrar por Lead el tiempo transcurrido del modo `--auto`, desde el inicio
   de procesamiento del Lead hasta que se registra su resultado final.
2. Conservar solo métricas operativas: duración, estado, cantidad de intentos y
   marca de tiempo; nunca texto del comentario, teléfono, nombre u otro dato de
   cliente.
3. Generar un resumen local de lote con tamaño de muestra, guardados, errores,
   promedio, mediana, mínimo, máximo, tasa de éxito y capacidad equivalente por
   hora para Leads guardados.
4. Ejecutar una prueba controlada de 10 Leads pendientes, únicamente después de
   la confirmación explícita del operador; los resultados se usarán como la
   primera muestra del bot.
5. Crear una presentación HTML local con la evolución de los tres flujos,
   supuestos, métricas verificadas y controles de seguridad.
6. Mostrar visualmente el tiempo individual de cada Lead guardado, tanto en la
   lista general como en la cola del bot, comparado con el promedio del lote.

## Fuera de alcance

- Cronometrar login, 2FA o revisión humana posterior al guardado; no son trabajo
  repetitivo por Lead del bot.
- Cambiar las restricciones de escritura del bot o ejecutar acciones adicionales
  en Salesforce.
- Enviar métricas o datos a servicios externos.
- Presentar proyecciones como resultados medidos.

## Criterio de éxito

El equipo puede abrir un reporte local de productividad donde cada métrica del
bot proviene de un archivo de resultados de una prueba real, con la cantidad de
Leads de la muestra visible y sin exponer información de clientes.