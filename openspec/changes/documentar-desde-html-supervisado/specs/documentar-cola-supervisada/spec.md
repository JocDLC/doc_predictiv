# Capability: documentar cola de intentos con supervisión

## ADDED Requirements

### Requirement: REQ-501: Exportación de cola desde el HTML

`documentador_predictivo.html` MUST ofrecer una acción "Exportar cola para bot"
que genere un archivo JSON local con los Leads no marcados como documentados. Cada
Lead MUST incluir únicamente `lead_id` y la lista `attempts` con `result`, `date`,
`time` y `call_id`. El archivo MUST NOT incluir números INT, nombre, teléfono ni
otros datos del cliente.

#### Scenario: exportar con Leads ya documentados

**Given** una BD cargada con 57 Leads de los cuales 3 están marcados como hechos.
**When** el operador pulsa "Exportar cola para bot".
**Then** el JSON contiene 54 Leads, cada uno con sus intentos en orden cronológico
y `result` ya traducido por las equivalencias configuradas.

### Requirement: REQ-502: Validación de la cola antes de abrir el navegador

El runner MUST validar la cola (JSON válido, Lead IDs de 15 o 18 caracteres
alfanuméricos, al menos un intento por Lead, campos requeridos presentes) y MUST
terminar con un mensaje claro antes de crear el navegador si la cola es inválida.

#### Scenario: Lead ID con formato incorrecto

**Given** una cola con un `lead_id` de 12 caracteres.
**When** el runner se ejecuta.
**Then** informa el índice del Lead inválido, no abre Edge y no modifica archivos.

### Requirement: REQ-503: Numeración desde Salesforce

Para cada Lead, el runner MUST leer el contenido real de `Otra información` y
calcular el próximo INT con `next_attempt_number()`. Los intentos MUST numerarse
consecutivamente desde ese valor, ignorando cualquier número que el operador haya
configurado en el HTML.

#### Scenario: historial con tres intentos y dos nuevos

**Given** `Otra información` contiene `1 INT`, `2 INT` y `3 INT`.
**When** la cola aporta dos intentos para ese Lead.
**Then** el texto preparado añade `4 INT ...` y `5 INT ...`.

#### Scenario: historial vacío

**Given** `Otra información` está vacío.
**When** la cola aporta un intento.
**Then** el texto preparado es exactamente `1 INT ...` sin línea vacía inicial.

### Requirement: REQ-504: Formato del texto y separación

Cada intento MUST tener el formato `N INT<TAB>resultado<TAB>fecha<TAB>hora<TAB>callId`
en una línea propia. Si existe historial, el runner MUST conservarlo íntegro y
agregar el primer intento nuevo en la línea inmediatamente siguiente, sin línea
vacía (los saltos finales del historial se recortan antes de unir).

#### Scenario: historial existente

**Given** un historial de 35 caracteres.
**When** se compone el texto con un intento nuevo.
**Then** el resultado es `historial + "\n" + línea` y los tabuladores se preservan.

### Requirement: REQ-505: Escritura sin guardar y verificación

El runner MUST activar solo el editor asociado a `Otra información`, cargar el
texto mediante JavaScript sobre el control editable (no mediante teclas), releer el
valor y verificar que coincide. El runner MUST NOT pulsar Guardar, Cancelar ni
ningún control de negocio. Tras cargar, MUST detenerse hasta que el operador
confirme por teclado.

#### Scenario: verificación post-escritura falla

**Given** el valor releído del editor no coincide con el texto compuesto.
**When** el runner detecta la diferencia.
**Then** toma captura local, registra `status=error` con ID enmascarado, avisa al
operador que cancele a mano y no reintenta.

### Requirement: REQ-506: Control por Lead

Antes de editar cada Lead el runner MUST mostrar Lead ID, caracteres previos,
próximo INT, cantidad de intentos y caracteres finales, y MUST esperar `PREPARAR`
(editar), `s` (omitir) o `q` (terminar). Después de editar MUST esperar Enter y
MUST NOT navegar al siguiente Lead mientras el editor siga abierto.

#### Scenario: operador omite un Lead

**Given** el runner muestra las métricas de un Lead.
**When** el operador escribe `s`.
**Then** el Lead se registra como `omitido`, Salesforce no se toca y se pasa al
siguiente.

### Requirement: REQ-507: Resultados y privacidad

El runner MUST escribir un archivo local de resultados por cola con `lead_id`,
`status`, `next_int`, `attempts` y timestamp. Consola y logs MUST NOT contener el
texto del comentario, historial ni datos del cliente. Logs MUST usar ID enmascarado.
Los archivos de cola y resultados MUST residir en `queues/`, ignorado por Git.

#### Scenario: fin de cola

**Given** una cola de 5 Leads con 3 preparados, 1 omitido y 1 error.
**When** el runner termina.
**Then** imprime ese resumen, el archivo de resultados tiene 5 entradas y
`git status` no muestra archivos de `queues/`.
