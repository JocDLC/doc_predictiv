# Spec: cierre-leads-por-motivo

## ADDED Requirements

### Requirement: REQ-701: Motivos de cierre cerrados y explícitos

El sistema MUST soportar exactamente dos motivos de cierre elegidos por el
auxiliar por Lead: `ilocalizable` y `deja_de_interactuar`. MUST NOT inferir el
motivo desde resultados del predictivo ni cerrar Leads sin motivo asignado.
Los valores Salesforce aprobados son:

| Campo | ilocalizable | deja_de_interactuar |
|---|---|---|
| Comentario | `Ilocalizable` | `Cliente deja de interactuar` |
| Cualificación | `Rechazo no argumentado` | `Rechazo argumentado` |
| Sub-Cualificación | `Ilocalizable` (o `Permanece ilocalizable` si la primera no existe) | `Interesado en precio o condición` |

#### Scenario: motivo obligatorio

**Given** un lote de cierre con un Lead sin motivo asignado.
**When** el auxiliar intenta ejecutar el cierre.
**Then** la ejecución se bloquea para ese Lead y el lote no arranca hasta
que todos los seleccionados tengan motivo.

#### Scenario: motivo desconocido en la cola

**Given** una cola de cierre con un código de motivo no registrado.
**When** el runner la valida.
**Then** rechaza la cola sin abrir el navegador.

### Requirement: REQ-702: Sin umbral de intentos

La habilitación del cierre MUST NOT depender de la cantidad de intentos `INT`
documentados ni de ningún conteo automático. La decisión de cuándo cerrar es
del auxiliar.

#### Scenario: Lead con pocos intentos

**Given** un Lead con cualquier cantidad de intentos documentados.
**When** el auxiliar lo incluye en el lote de cierre con motivo asignado.
**Then** la cantidad de intentos no lo bloquea; puede bloquearlo la
documentación requerida pendiente u otros estados incompatibles.

### Requirement: REQ-703: Edición controlada del trío de campos

El runner MUST editar únicamente `Comentario`, `Cualificación` y
`Sub-Cualificación` con los valores exactos del motivo, pulsando Guardar solo
en el formulario del Lead correcto. MUST NOT modificar `Otra información` ni
otros campos, MUST NOT invocar APIs internas ni acciones de negocio distintas
de `Convert Lead → Yes`.

#### Scenario: valores exactos

**Given** un Lead en edición.
**When** el runner completa el formulario.
**Then** `Comentario` contiene exactamente el literal del motivo, sin texto
adicional, y los picklists se eligen por etiqueta exacta.

#### Scenario: variante dependiente de Sub-Cualificación para ilocalizable

**Given** un Lead con motivo `ilocalizable` cuya lista dependiente no ofrece
`Ilocalizable` pero sí ofrece `Permanece ilocalizable`.
**When** el runner completa la Sub-Cualificación.
**Then** MUST elegir `Permanece ilocalizable` como alternativa del mismo
motivo y MUST verificar exactamente esa etiqueta persistida. Si ambas
etiquetas aparecen, MUST preferir `Ilocalizable`; si ninguna aparece, MUST
abortar ese Lead sin elegir una opción aproximada.

#### Scenario: formulario oculto con otro motivo

**Given** un formulario visible del Lead activo y otro oculto con una
Cualificación distinta.
**When** el runner selecciona y verifica la Cualificación de cualquiera de
los dos motivos soportados.
**Then** MUST leer el mismo control visible usado para seleccionar, ignorar
el oculto y avanzar a Sub-Cualificación cuando observe la etiqueta exacta,
sin volver a seleccionar un valor ya confirmado.

#### Scenario: desplegable ajeno o campo ambiguo

**Given** otro desplegable abierto con una opción de igual texto, o más de un
control visible con la etiqueta del campo solicitado.
**When** el runner intenta seleccionar una opción.
**Then** MUST limitar la búsqueda al listbox asociado al control objetivo;
si el campo o la opción son ambiguos, MUST abortar sin elegir el primero.

#### Scenario: Otra información intacta

**Given** un Lead cerrado por el runner.
**When** termina la ejecución.
**Then** el contenido de `Otra información` conserva el hash previo.

### Requirement: REQ-704: Verificación en dos hitos

Tras Guardar, el runner MUST confirmar campos persistidos + estado `Cerrado`
antes de intentar la conversión. El éxito final (`cerrado_verificado`) MUST
requerir además `Propietario del candidato = AR_LEAD_COLD`. El estado
`Cerrado` tras el primer Guardar por sí solo MUST NOT reportarse como cierre
completo.

#### Scenario: guardado sin conversión

**Given** un Lead cuyos campos quedaron persistidos y estado `Cerrado`.
**When** la conversión no se ejecutó o no pudo verificarse.
**Then** el estado es `conversion_pendiente` o `conversion_no_verificada`,
nunca `cerrado_verificado`.

#### Scenario: cierre completo

**Given** un Lead tras Convert Lead → Yes.
**When** el runner relee el registro.
**Then** `cerrado_verificado` solo si estado `Cerrado` y propietario
`AR_LEAD_COLD` son observados.

#### Scenario: propietario expuesto como ID interno durante la carga

**Given** un Lead cuyo estado ya es `Cerrado` tras la conversión.
**When** Salesforce muestra temporalmente un lookup de propietario cuyo
`.value` es un ID interno o un propietario anterior.
**Then** el runner MUST esperar el nombre visible del propietario y leerlo
desde la etiqueta visible del lookup; MUST NOT terminar la verificación por
un valor interno no vacío ni recargar continuamente la página.

#### Scenario: verificación final agotada

**Given** un Lead tras Convert Lead → Yes cuyo resultado final no llega al
estado esperado dentro del plazo acotado.
**When** termina la verificación.
**Then** el resultado MUST ser `conversion_no_verificada` y MUST NOT repetir
Guardar ni `Yes` automáticamente.

### Requirement: REQ-705: Conversión no reintentable a ciegas

`Convert Lead → Yes` MUST ejecutarse solo sobre el diálogo verificado del Lead
correcto. Si se pierde la respuesta tras enviar `Yes`, el runner MUST registrar
`conversion_no_verificada` y MUST NOT reenviar la acción automáticamente.

#### Scenario: respuesta de conversión perdida

**Given** un Lead donde el clic en `Yes` pudo haberse ejecutado pero el
resultado no se comprobó.
**When** termina el procesamiento del Lead.
**Then** el estado es `conversion_no_verificada` y el Lead requiere revisión
o nueva autorización, no reintento automático.

### Requirement: REQ-706: Cola y resultados independientes

La cola de cierre MUST ser inmutable por ejecución (`run_id`) y sus
resultados MUST separarse de los de documentación. Los resultados MUST NOT
incluir contenido de campos ni datos de clientes.

#### Scenario: aislamiento de operaciones

**Given** una ejecución de documentación en curso.
**When** se solicita un cierre.
**Then** el servidor responde 409 y no lanza el runner.

#### Scenario: resultado sin contenido

**Given** un resultado de cierre registrado.
**When** se inspecciona el archivo.
**Then** contiene `lead_id`, `status`, `reason`, `run_id`, tiempos y fecha;
nunca valores de `Comentario` ni `Otra información`.

### Requirement: REQ-707: Selección masiva en la UI

La UI MUST permitir marcar `Incluir en cierre` por Lead y ofrecer
`Seleccionar todos`/`Ninguno` y `Asignar motivo a seleccionados`. Ninguna de
esas acciones MUST ejecutar operaciones en Salesforce; la ejecución requiere
confirmación explícita del lote.

#### Scenario: selección masiva sin ejecución

**Given** 50 Leads con checkbox de cierre.
**When** el auxiliar pulsa `Seleccionar todos` y asigna `Ilocalizable`.
**Then** los 50 quedan preparados con ese motivo, visibles para revisión, y
ningún cambio llega a Salesforce hasta confirmar.
