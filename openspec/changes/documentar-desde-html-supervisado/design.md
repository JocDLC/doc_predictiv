# Diseño técnico: documentar desde el HTML con supervisión

## Flujo

```text
documentador_predictivo.html
  -> botón "Exportar cola para bot"
  -> descarga cola_predictivo_{YYYYMMDD_HHMMSS}.json (solo Leads pendientes)
  -> el operador lo guarda en automation_salesforce/queues/

python run_document_queue.py queues/cola_predictivo_....json
  -> login/2FA manual
  -> por cada Lead de la cola:
       abrir /lightning/r/Lead/{id}/view
       scroll hasta "Otra información"        (comment_writer.scroll_toward_other_information)
       leer historial                          (comment_reader.find_other_information)
       next_int = next_attempt_number(historial)
       texto = compose_attempts(historial, next_int, intentos)
       imprimir métricas (sin contenido) y pedir PREPARAR
       activar editor y cargar texto por JS    (sin Guardar)
       esperar Enter: el operador guardó o canceló a mano
       registrar resultado en queues/{cola}.resultado.json
  -> resumen final: preparados / omitidos / errores
```

## Contrato de la cola (JSON UTF-8)

```json
{
  "generated_at": "2026-09-17T10:15:00",
  "source_file": "predictivo_ARG_20260915.csv",
  "leads": [
    {
      "lead_id": "00Q67000001AbCdEAA",
      "attempts": [
        {"result": "No contesta", "date": "15/09/2026", "time": "10:30", "call_id": "12345"},
        {"result": "Cliente contesta", "date": "15/09/2026", "time": "11:02", "call_id": "12346"}
      ]
    }
  ]
}
```

Reglas:

- `lead_id`: 15 o 18 caracteres alfanuméricos (misma validación que `comment_reader`).
- `attempts`: orden cronológico (el HTML ya ordena `oldest first`), mínimo 1.
- `result`: el texto ya traducido por el HTML (`displayResult`), es decir, aplica
  `resultMap` y `DESC1` para `ANSWER`. El bot no vuelve a traducir.
- No incluye número INT, nombre, teléfono ni ningún otro campo.
- Solo se exportan Leads con `isDone(lead) === false`.

## Composición del texto

```text
línea_i = f"{next_int + i} INT\t{result}\t{date}\t{time}\t{call_id}"
si historial vacío:   "\n".join(líneas)
si historial existe:  historial.rstrip() + "\n" + "\n".join(líneas)
```

`compose_attempts()` reemplaza a `compose_other_information()` para colas; la
función existente se mantiene para el runner de un solo intento. Ambas rechazan
`next_int < 1` y listas vacías.

## Escritura en el editor

`replace_editor_value()` hoy usa `clear()` + `send_keys()`. Un `\t` enviado por
`send_keys` se interpreta como tecla TAB y cambia el foco. Se reemplaza por:

```js
arguments[0].focus();
arguments[0].value = arguments[1];
arguments[0].dispatchEvent(new Event('input',  {bubbles: true}));
arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
```

Tras escribir, el runner relee `editor.value` y verifica que:

1. termina exactamente con el texto compuesto de intentos nuevos;
2. la longitud coincide con `len(texto)`.

Si no coincide, toma captura local, registra el error y **no reintenta**.

## Resultado por Lead

`queues/{nombre_cola}.resultado.json`:

```json
{"lead_id": "00Q...", "status": "preparado|omitido|error", "next_int": 3, "attempts": 2, "at": "..."}
```

`status` refleja solo lo que hizo el bot. Nunca infiere si el operador guardó.

## Seguridad y control humano

- Sin `click` sobre controles cuyo texto/atributo sea Guardar, Cancelar, Save,
  Cerrar, Convertir, Cambiar propietario o Estado. Se conserva el test estático
  de `escritura-asistida-salesforce` y se extiende al nuevo runner.
- Antes de editar cada Lead: `PREPARAR` por teclado. `s` = omitir Lead, `q` =
  terminar la cola.
- Después de editar: Enter obligatorio antes de navegar al siguiente Lead. Si el
  operador guardó o canceló a mano, Lightning ya cerró el editor; si no lo hizo,
  el runner avisa y espera de nuevo (no navega con un editor abierto).
- Consola: Lead ID en claro (decisión operativa vigente), caracteres previos,
  próximo INT, cantidad de intentos, caracteres finales. Logs: ID enmascarado.
- Ni consola, ni logs, ni capturas, ni Git reciben el texto del comentario.

## Cambios en el HTML

- Nuevo botón en la toolbar de DOCUMENTAR: **"Exportar cola para bot"**.
- Función `buildBotQueue()` que recorre `leads.filter(l => !isDone(l))` y produce
  el JSON del contrato. Reutiliza `displayResult()` para `result`.
- Descarga con `Blob` + `<a download>`, mismo patrón que `downloadCSV()`.
- El texto de ayuda del botón aclara dónde guardar el archivo.
- No se toca `docText()`, `getOffset()` ni el flujo manual actual: siguen
  funcionando para quien documente a mano.

## Errores y recuperación

| Situación | Acción |
|---|---|
| Cola inválida (JSON, IDs, intentos vacíos) | Informar y terminar antes de abrir el navegador |
| Campo `Otra información` no encontrado | Captura, `status=error`, pasar al siguiente tras Enter |
| Editor no aparece tras el click en editar | Captura, `status=error`, no reintentar |
| Verificación post-escritura falla | Captura, `status=error`, avisar al operador para que cancele a mano |
| Operador escribe `s` | `status=omitido`, siguiente Lead |
| Operador escribe `q` | Resumen y salida; los Leads restantes no se tocan |
| Timeout / WebDriverException | Captura, log, `status=error`, continuar con el siguiente |

## Componentes

| Archivo | Cambio |
|---|---|
| `documentador_predictivo.html` | Botón y `buildBotQueue()` |
| `automation_salesforce/queue_loader.py` | Nuevo: carga y valida la cola |
| `automation_salesforce/comment_writer.py` | `compose_attempts()`, escritura por JS, verificación |
| `automation_salesforce/run_document_queue.py` | Nuevo runner de cola |
| `automation_salesforce/tests/test_queue_loader.py` | Nuevo |
| `automation_salesforce/tests/test_comment_writer.py` | Casos de `compose_attempts()` y verificación |
| `automation_salesforce/tests/test_run_document_queue.py` | Nuevo: métricas sin contenido, confirmaciones `PREPARAR`/`s`/`q`, escaneo estático anti-Guardar sobre el nuevo runner |
| `automation_salesforce/README.md` | Sección "Documentar desde el HTML" |
