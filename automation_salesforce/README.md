# Piloto de lectura Salesforce

Este módulo usa Selenium para validar acceso de solo lectura a Salesforce.

## Alcance actual

- Detecta Edge y Chrome; Edge es el valor predeterminado.
- Abre un perfil de navegador dedicado.
- Permite login y 2FA manual.
- Comprueba que Salesforce esté accesible después de la autenticación.
- Lee las filas visibles del reporte y filtra el propietario exacto configurado.
- Extrae IDs Salesforce de 15/18 caracteres sin fijar su prefijo; el objeto se
  define con `record_object_api_name` (`Lead` por defecto).

No escribe campos, no guarda, no cierra registros y no automatiza 2FA.

## Primera ejecución

1. Copiar `config.example.json` a `config.json`.
2. Ejecutar `python -m pip install -r requirements.txt`.
3. Ejecutar `python run_read_only.py`.
4. En Edge, iniciar sesión en Salesforce y completar 2FA manualmente.
5. Volver a la terminal y presionar Enter.
6. Confirmar que el resultado indica autenticación correcta.

Usar Ctrl+C para detener. No compartir la carpeta de perfil, `config.json`, logs ni capturas.

## Lectura del reporte

Ejecutar `python run_report_read_only.py`, completar login y 2FA manualmente y
presionar Enter. El runner crea una instantánea JSON local en `queues/` con ID,
fecha de creación, posición visible y estado `SIN_GESTION`. Ese directorio está
ignorado por Git y no debe compartirse fuera del entorno autorizado.

## Lectura de “Otra información”

Ejecutar `python run_comment_read_only.py`, completar login y 2FA manualmente e
ingresar un único Lead ID. El runner abre la página individual del registro, lee
“Otra información” y muestra solo el estado del campo, la cantidad de caracteres
y el próximo `INT`. No imprime el comentario, no activa edición y no guarda
cambios en Salesforce.

## Preparación asistida de Otra información

La preparación asistida trata un único Lead y nunca guarda automáticamente. Crear
primero un archivo UTF-8 dentro de `queues/`, por ejemplo
`queues/borrador.txt`, con **solo el cuerpo** de un nuevo intento. No incluir el
prefijo `N INT`, porque el runner lo calcula según el historial real del Lead.

Ejecutar `python run_comment_assisted.py`, completar login y 2FA manualmente e
ingresar el Lead ID y la ruta del borrador local. El runner muestra únicamente
métricas y exige escribir `PREPARAR` antes de abrir el editor. Después carga el
borrador en “Otra información” y se detiene: el usuario debe revisar y pulsar
**Guardar** o **Cancelar** directamente en Salesforce. El runner no automatiza
ninguno de esos botones.

## Documentar desde el HTML (cola)

`documentador_predictivo.html` exporta una cola JSON con los Leads pendientes:

1. En la vista DOCUMENTAR, pulsar **“Exportar cola para bot”** y guardar el
   archivo dentro de `automation_salesforce/queues/`.
2. Ejecutar `python run_document_queue.py queues/cola_predictivo_<fecha>.json`.
3. Completar login y 2FA manualmente.
4. Por cada Lead el runner abre el registro, lee `Otra información`, calcula el
   próximo `N INT` real y muestra solo métricas (caracteres, próximo INT,
   cantidad de intentos).
5. Responder:
   - `PREPARAR` → carga el texto en el editor del campo, sin guardar.
   - `s` → omite el Lead.
   - `q` → termina la cola.
6. Con el borrador cargado, revisar en Salesforce y pulsar **Guardar** o
   **Cancelar** a mano; luego Enter en la terminal para pasar al siguiente.

El runner escribe el texto por JavaScript sobre el editor (los tabuladores se
conservan) y relee el valor para verificarlo. Al final queda
`queues/<cola>.resultado.json` con el estado por Lead (`preparado`, `omitido`,
`error`), que se actualiza después de cada Lead.

### Modo automático (`--auto`)

Con `--auto` el runner procesa la cola sin pausas: por cada Lead prepara el
texto, pulsa **solo el botón Guardar del formulario de edición**, reabre el
registro y relee `Otra información` para verificar igualdad exacta. El estado
`guardado` solo se registra tras esa verificación; en caso contrario queda
`error`. Tras cada guardado verificado se guarda un snapshot privado del campo
en `ui_output/<cola>.snapshots.json` (valor completo + hash SHA-256), que la UI
puede importar para revisión local. Sigue prohibido pulsar Cancelar o cualquier
otro control de negocio.

```powershell
python run_document_queue.py --auto queues/cola_predictivo_<fecha>.json
```

En la UI: el checkbox **“Cola”** de cada tarjeta y el selector
**“Seleccionar…”** permiten armar tandas; **“Exportar selección”** genera una
cola solo con los marcados. **“Importar resultado del bot”** lee el
`*.resultado.json` y marca `por bot` a los `guardado`; el encabezado muestra
`N documentados · M por bot · K manual`.

### Cola viva (sin exportar a mano)

Con **“Ir a cola del bot”** la UI muestra solo los Leads seleccionados. Al
vincular la carpeta `automation_salesforce` una sola vez (permiso guardado en
el navegador), la UI **escribe sola** `queues\cola_activa.json` cada vez que
cambia la selección, sin diálogos. El comando es siempre el mismo:

```powershell
python run_document_queue.py --auto queues\cola_activa.json
```

Para no usar la terminal: con `python ui_server.py` corriendo (una vez, junto
al navegador persistente), el botón **“Ejecutar bot”** de la vista de cola
lanza la misma corrida. El servidor solo escucha en `127.0.0.1` y exige un
token de sesión que la UI lee sola de `ui_output/bot_session.json`; no ejecuta
comandos arbitrarios.

Mientras el bot corre, la vista relee `queues\cola_activa.resultado.json` y
`ui_output\cola_activa.snapshots.json` cada ~3 segundos: los estados se ven en
vivo, los `guardado` se marcan `por bot` y **salen solos de la cola** (una
segunda corrida no los repite). **“Volver a la lista”** aplica el último
estado a cada Lead y regresa a la vista principal.

### Correcciones seguras

Desde la UI se puede editar localmente el snapshot confirmado de un Lead
(“Guardar borrador local” — no toca Salesforce). **“Exportar correcciones”**
genera `correcciones_<fecha>.json` con los borradores que difieren del snapshot
(`lead_id`, `new_value`, `base_hash`); guardarlo en
`automation_salesforce/ui_output/` (contiene texto del campo: no compartir).

```powershell
python run_corrections.py ui_output/correcciones_<fecha>.json
```

Por cada corrección el bot reabre el Lead, relee `Otra información` y compara
el hash con `base_hash`:

- **coincide** → reemplaza el campo, pulsa Guardar y verifica releyendo →
  `corregido`; el snapshot local se actualiza.
- **no coincide** → `conflicto` y no escribe nada.

Importar el `*.resultado.json` en la UI muestra `corregido` o `conflicto`;
los conflictos conservan el botón manual “Abrir en Salesforce”.

## Navegador persistente (opcional)

Para no autenticarse en cada ejecución:

```powershell
python open_persistent_browser.py
```

Abre Edge con el perfil dedicado y un puerto de depuración local
(`127.0.0.1:9222`, configurable con `debugger_address` en `config.json`).
Iniciar sesión una sola vez y dejar la ventana abierta: los runners que soportan
la conexión se adjuntan a esa ventana, detectan la sesión activa y **no la
cierran al terminar**. Si el navegador persistente está cerrado, el runner abre
uno propio y pide login como antes.

Notas:

- El puerto de depuración solo escucha en `localhost`, pero cualquier programa
  local podría controlar esa ventana mientras esté abierta; cerrarla al terminar.
- Mientras el navegador persistente esté abierto, no lanzar otros runners que
  usen el mismo perfil sin adjuntarse (Edge no permite dos instancias del mismo
  perfil).
