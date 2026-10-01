# Diseño: medir-productividad-documentacion

## Definición de tiempo del bot

```text
inicio_lead = reloj monotónico justo antes de abrir el Lead
  abrir Lead → leer campo → calcular INT → preparar editor → Guardar
  → esperar persistencia → releer y verificar
fin_lead = reloj monotónico al registrar guardado/error/omitido
elapsed_seconds = fin_lead - inicio_lead
```

Se usa un reloj monotónico para que ajustes de reloj del sistema no alteren las
duraciones. El login y 2FA se realizan antes del lote y quedan fuera de la
medición. El tiempo de corrección humana posterior tampoco se agrega porque no
forma parte del recorrido automático del bot.

## Contrato de resultado extendido

La entrada existente por Lead agrega `elapsed_seconds` solamente cuando el
runner inició el procesamiento del Lead:

```json
{
  "lead_id": "...",
  "status": "guardado",
  "next_int": 6,
  "attempts": 3,
  "elapsed_seconds": 31.8,
  "at": "..."
}
```

El resultado sigue sin incluir textos, teléfonos, nombres, snapshots ni datos
personales. `elapsed_seconds` se redondea a una décima para reporte y se calcula
con precisión interna de reloj monotónico.

## Medición por etapas

Cada resultado automático agrega `stage_seconds` (solo duraciones, en segundos)
y `verify_reloads` (conteo de recargas de respaldo de la verificación):

```json
"stage_seconds": {
  "navigation": 4.2,
  "comment_check": 1.1,
  "field_read": 0.9,
  "editor": 4.8,
  "save_settle": 4.6,
  "verification": 1.0,
  "snapshot": 0.9
},
"verify_reloads": 0
```

Las etapas se miden con el mismo reloj monotónico y el mismo redondeo de una
décima. Un `duplicado` registra solo `navigation` y `comment_check`. Un
`error` conserva las etapas completadas antes del fallo; la etapa ausente
indica dónde falló. Esto permite ubicar el cuello de botella sin exponer
contenido.

El resumen agrega `stage_seconds_mean` (media por etapa sobre los resultados
que la ejecutaron) y `verify_reloads` total del lote. El aviso de cierre de la
UI muestra el desglose por etapa para diagnóstico inmediato.

## Resumen del lote

Un archivo local separado `<cola>.metricas.json` contiene únicamente agregados:

```json
{
  "sample_size": 10,
  "saved": 9,
  "errors": 1,
  "success_rate": 90.0,
  "saved_elapsed_seconds": {
    "mean": 32.4,
    "median": 31.9,
    "min": 28.7,
    "max": 38.2
  },
  "effective_leads_per_hour": 111.1
}
```

La capacidad efectiva se calcula a partir del tiempo de ciclo del lote completo
(inicio del primer Lead hasta resultado del último), para no ocultar pausas o
fallos. Las estadísticas por Lead guardado se muestran por separado.

## Inspección visual por Lead

La UI conserva `elapsed_seconds` de cada resultado `guardado` y muestra un badge
con segundos y clasificación en la lista general y en la cola del bot. El
promedio del lote terminado es la referencia del color:

| Clasificación | Regla |
|---|---|
| Verde · normal | `elapsed_seconds` ≤ promedio del lote |
| Naranja · intermedio | mayor al promedio y hasta 20% por encima |
| Rojo · alto | más de 20% por encima del promedio |

Los estados `duplicado` y `error` muestran su propio estado y no reciben una
clasificación de tiempo. La clasificación incluye texto además del color.

## Presentación

La presentación HTML usa tres categorías explícitas:

- **Rango declarado:** manual sin aplicación (40–55 s) y manual asistido
  (23–29 s).
- **Muestra medida:** resultados del bot, incluyendo fecha, tamaño de muestra y
  rango de resultados.
- **Proyección:** ahorro y capacidad calculados a partir de los valores
  anteriores, identificados como proyección y no como dato observado.

No se carga ningún archivo de datos de clientes en la presentación. Solo se
importa o incorpora el archivo agregado de métricas.

## Seguridad y efectos

La instrumentación no agrega clicks ni llamadas a Salesforce. El flujo de
escritura autorizado permanece: editar exclusivamente `Otra información`, usar
solo el Guardar del formulario activo y verificar persistencia. La corrida real
sobre 10 Leads requiere confirmación explícita inmediata antes de iniciarla.