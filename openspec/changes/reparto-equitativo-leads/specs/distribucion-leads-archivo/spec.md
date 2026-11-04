# Delta spec — reparto equitativo de leads

## ADDED Requirements

### Requirement: Equipo del día persistente

La vista MUST mantener una lista persistente de auxiliares para el reparto
(alta, baja y tilde "trabaja hoy" guardadas server-side). La lista se precarga
en cada uso y el usuario solo ajusta el tilde del día.

#### Scenario: Persistencia del equipo

- **GIVEN** un auxiliar agregado a la lista
- **WHEN** se recarga la vista
- **THEN** el auxiliar sigue listado con su tilde anterior

#### Scenario: Equipo vacío

- **GIVEN** ninguna persona tildada
- **WHEN** se pide calcular el reparto
- **THEN** la UI MUST rechazar el cálculo pidiendo tildar al menos una persona

### Requirement: Reparto equitativo con mínimo de reasignaciones

Dado el lote de leads de la BD y el equipo tildado, el sistema MUST asignar
cada lead a una persona del equipo con diferencia máxima de 1 lead entre
personas, minimizando los cambios: un lead cuyo auxiliar actual (según el
archivo) trabaja hoy MUST quedarse con esa persona hasta completar su cupo;
los leads de auxiliares que no trabajan y los excedentes MUST cubrir los
déficits. El reparto MUST ser determinista para la misma entrada.

#### Scenario: Lead de quien trabaja hoy

- **GIVEN** un lead cuyo auxiliar en el archivo está tildado
- **WHEN** su cupo no está completo
- **THEN** queda asignado a esa persona (`se_queda`)

#### Scenario: Lead de quien no trabaja

- **GIVEN** un lead cuyo auxiliar en el archivo no está tildado
- **WHEN** corre el reparto
- **THEN** se asigna a una persona tildada con cupo incompleto (`se_mueve`)

#### Scenario: Excedente de cupo

- **GIVEN** una persona tildada con más leads que su cupo
- **THEN** sus excedentes se marcan `se_mueve` y cubren déficits de otros

#### Scenario: Diferencia máxima de uno

- **GIVEN** cualquier lote y equipo
- **THEN** los cupos asignados difieren a lo sumo en 1 lead

#### Scenario: Entrelazado por secuencia, no por bloques

- **GIVEN** 12 leads cuyo auxiliar no trabaja y equipo [A, B, C]
- **WHEN** corre el reparto
- **THEN** cada persona recibe leads repartidos a lo largo del archivo
  (A: 1,4,7,10 · B: 2,5,8,11 · C: 3,6,9,12 — round-robin en orden de
  aparición), nunca un bloque contiguo

#### Scenario: "se queda" espaciado

- **GIVEN** una persona con más leads en el archivo que su cupo
- **WHEN** se elige cuáles conserva
- **THEN** conserva posiciones espaciadas uniformemente dentro de su propia
  lista (no un bloque contiguo), manteniendo el mínimo de reasignaciones

### Requirement: Vista previa con acción por lead

La vista previa MUST mostrar el destino computado y una columna "Acción"
(`se queda` / `se mueve`) por lead, editable como en el modo archivo, y un
resumen de cupos por persona. La ejecución (real o simulación) MUST usar la
misma cola y runner sin cambios.

#### Scenario: Resumen de cupos

- **GIVEN** un reparto calculado
- **THEN** se muestra leads por persona y cuántos se mueven vs se quedan

### Requirement: Lista de reasignación WhatsApp

El sistema MUST generar la lista de leads cuyo `Preferred mean of contact`
contiene "whatsapp" (insensible a mayúsculas/diacríticos) con su nueva
persona destino, visible en la UI tras el reparto y junto a los resultados.

#### Scenario: Lead WhatsApp

- **GIVEN** un lead con preferencia de contacto WhatsApp
- **WHEN** se calcula el reparto
- **THEN** aparece en la lista "Reasignación WhatsApp" → nueva persona

### Requirement: Exportación Excel del reparto

El sistema MUST generar archivos `.xlsx` descargables desde la UI tras el
reparto: (a) distribución final para el equipo — lead_id, nombre, auxiliar
actual, nueva persona, acción (se queda/se mueve); y (b) lista de
reasignación WhatsApp para los GTR — lead_id y nueva persona. La generación
MUST hacerse server-side (openpyxl) sin persistir datos de clientes más allá
del archivo exportado.

#### Scenario: Descarga de distribución

- **GIVEN** un reparto calculado
- **WHEN** el usuario pulsa "Descargar distribución (.xlsx)"
- **THEN** se descarga un Excel con una fila por lead: id, nombre, auxiliar
  actual, nueva persona y acción

#### Scenario: Descarga de WhatsApp para GTR

- **GIVEN** un reparto calculado con leads WhatsApp
- **WHEN** el usuario pulsa "Descargar WhatsApp (.xlsx)"
- **THEN** se descarga un Excel solo con los leads WA: lead_id y nueva
  persona
