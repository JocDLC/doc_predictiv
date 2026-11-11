## Context

El Monitor de Bandeja llama hoy a `read_visible_unassigned_leads`, que solo
inspecciona las celdas renderizadas en el viewport inicial. Lightning
virtualiza horizontalmente los reportes anchos: en AR se observa
`Propietario del candidato` a la izquierda y los enlaces de `Nombre`/`Apellido`
o la columna `Lead ID` a la derecha. Con la ventana dedicada de 1150x760 —y
más aún con escalado de Windows— esos datos pueden no coexistir en el DOM.

`report_reader.py` ya contiene un barrido horizontal para otros flujos, pero
solo agrega objetos que previamente obtuvieron un Lead ID. No puede conservar
un fragmento con propietario QUALIF pero sin ID para unirlo con un fragmento
posterior. Además, la búsqueda de atributos `data-*` se limita a la fila raíz,
aunque Lightning puede colocar la identidad en un descendiente.

La lectura precede a una escritura real (`Pick Up`). La correlación entre
fragmentos debe ser conservadora: una asociación dudosa no puede abrir ni tomar
un Lead. Los diagnósticos deben explicar la omisión sin registrar valores de
campos ni datos personales.

## Goals / Non-Goals

**Goals:**

- Detectar Leads QUALIF aunque propietario, estado, detalles e identidad estén
  repartidos entre varios fragmentos horizontales de la misma fila.
- Correlacionar fragmentos únicamente con una identidad estructural estable y
  verificable dentro de un único barrido.
- Extraer el Lead ID desde enlaces, atributos estructurales descendientes o la
  columna visible `Lead ID`.
- Fallar cerrado ante identidad ausente, cambiante o ambigua.
- Dar observabilidad suficiente para distinguir bandeja vacía, propietario mal
  configurado y fila QUALIF sin identidad.
- Conservar el comportamiento y contratos actuales de CO, MX, Pick Up,
  cobertura horaria y reasignación.

**Non-Goals:**

- Modificar reportes, filtros o columnas guardadas en Salesforce.
- Usar APIs privadas de Salesforce, exportar el reporte o agregar dependencias.
- Recorrer verticalmente las 95+ filas del reporte durante cada tick; el
  Monitor conserva la semántica de procesar las filas visibles/recientes.
- Tomar una fila cuando no pueda demostrarse qué Lead ID le corresponde.
- Cambiar endpoints, formato de `monitor_state.json` o reglas de negocio.

## Decisions

### 1. Separar captura de fragmentos y materialización de Leads

El lector incorporará una representación interna de fragmento de fila con:
identidad estructural, posición/índice declarado por la grilla, Lead ID si está
disponible, coincidencia de propietario, estado y detalles visibles. Cada
posición horizontal captura fragmentos; la materialización de `VisibleLead`
ocurre después de unir los fragmentos compatibles.

Esto reemplaza la suposición actual de que propietario e ID deben aparecer en
la misma pasada. Se prefiere a ensanchar únicamente la ventana porque el ancho
efectivo cambia con pantalla, DPI y layout del reporte.

### 2. Identidad estable con política fail-closed

La correlación prioriza claves estructurales que Lightning exponga en la fila
o descendientes (`data-row-key-value`, `data-recordid`, `data-record-id` y
equivalentes). Cuando el propio valor sea un Salesforce ID válido, sirve además
como Lead ID.

Como respaldo se podrá usar `aria-rowindex` o el índice explícito de la fila
solo dentro del mismo barrido horizontal, siempre que la secuencia completa de
filas permanezca estable entre pasadas. Si faltan claves, hay duplicados o la
secuencia cambia, esos fragmentos se marcan irresolubles y no se materializa
ningún Lead a partir de ellos. Nunca se correlaciona por nombre, correo,
teléfono ni otro dato personal.

### 3. Barrido horizontal acotado y sin scroll vertical en el Monitor

El Monitor reinicia el scroll horizontal, captura la primera vista y avanza
hasta que el contenedor no se mueva o alcance un máximo de 20 pasadas. Espera
brevemente el re-render de Lightning después de cada movimiento. No desplaza la
grilla verticalmente durante este flujo, lo que mantiene estable el conjunto de
filas y limita el tiempo del tick.

La lógica común de captura/unión vivirá en `report_reader.py`. El lector
visible actual conservará su firma para compatibilidad; el Monitor usará la
variante horizontal segura. El lector completo existente reutilizará las
funciones puras de unión cuando sea razonable, sin cambiar sus contratos.

### 4. Extracción de ID por varias fuentes

Para cada fragmento se busca, en orden:

1. ruta `/Lead/<id>` en cualquier enlace descendiente;
2. Salesforce ID válido en atributos estructurales de la fila o descendientes;
3. valor de la columna `Lead ID` cuando esté renderizada.

Los IDs deben conservar la validación actual de 15/18 caracteres y del objeto
configurado. Un atributo de otro objeto o texto parecido no habilita una toma.

### 5. Diagnóstico estructural y seguro

El evento `bandeja_scan` y el log añadirán solo conteos/metadatos:
`horizontal_passes`, `viewport_width`, `owner_without_id` y
`unstable_or_ambiguous_rows`. No incluirán nombres, campañas, propietarios
individuales adicionales, correos, teléfonos ni valores de celdas. El Lead ID
solo podrá aparecer enmascarado mediante el helper existente.

El mensaje diferenciará explícitamente una fila QUALIF sin identidad de una
bandeja realmente vacía.

### 6. Ventana más ancha como defensa en profundidad

Al crear la ventana dedicada, el servidor intentará usar un ancho mayor cuando
el área disponible lo permita, con límites para no cubrir toda la pantalla ni
mover la ventana fuera del escritorio. Un fallo de `set_window_rect` mantiene
el comportamiento actual. La corrección funcional no dependerá de este ajuste.

### 7. Liberación como parche con piloto escalonado

El cambio no altera contratos externos, por lo que corresponde `1.5.1`. Antes
de una toma real se ejecutará modo prueba en un notebook de 13 pulgadas con AR
y CO habilitadas. Solo después de verificar detección e identidad se autorizará
un único Lead real. El ZIP se construirá con `packaging/build_zip.py` y se
validará su contenido e integridad.

## Risks / Trade-offs

- **Asociar fragmentos de filas distintas** → exigir clave estable, verificar
  secuencia entre pasadas y fallar cerrado ante cualquier ambigüedad.
- **El reporte cambia mientras se barre** → detectar cambio de claves/orden,
  descartar el barrido y esperar el siguiente ciclo.
- **Ciclo más lento por scroll horizontal** → máximo de 20 pasadas, salida
  inmediata al llegar al extremo y ausencia de scroll vertical.
- **Atributos Lightning diferentes entre países/versiones** → jerarquía de
  fuentes y pruebas para enlaces, fila, descendientes y columna visible.
- **Ventana ancha roba espacio o foco** → ajuste best-effort solo al crearla;
  no maximizar ni minimizar y mantener las protecciones actuales de foco.
- **Diagnóstico expone información sensible** → registrar exclusivamente
  conteos, dimensiones y IDs enmascarados; pruebas de privacidad específicas.

## Migration Plan

1. Implementar el lector y regresiones sin cambiar la versión distribuida.
2. Ejecutar formato, lint, compilación, suite completa y cobertura.
3. Validar OpenSpec y actualizar Graphify después de los cambios de código.
4. Probar AR/CO en modo prueba con viewport reducido y confirmar que no hay
   filas ambiguas ni cruces de identidad.
5. Ejecutar un piloto autorizado con un único Lead real.
6. Cambiar `APP_VERSION` a `1.5.1`, actualizar CHANGELOG y construir el ZIP.

Rollback: distribuir nuevamente `v1.5.0` y, como mitigación operativa, colocar
`Lead ID` junto a `Propietario del candidato` en el reporte AR. No hay migración
de datos ni cambio persistente que revertir.

## Open Questions

- El DOM real de AR puede exponer la clave estable en la fila, una celda o un
  nodo interno. La implementación cubrirá las variantes conocidas y el piloto
  confirmará cuál se usa, sin relajar la política fail-closed.
- El ancho máximo práctico dependerá del escalado de Windows; se determinará
  con una regla acotada y una prueba local, no con un valor obligatorio para la
  corrección.
