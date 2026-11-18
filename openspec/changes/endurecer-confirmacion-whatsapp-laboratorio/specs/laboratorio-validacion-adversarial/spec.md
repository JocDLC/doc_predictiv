## ADDED Requirements

### Requirement: Matriz adversarial reproducible
La implementación MUST tener tests de clasificador, runner/journal y fixture
DOM local con ambos motores; SHALL informar por separado PASS, FAIL, skip y pendientes.

#### Scenario: Eventos temporales
- **WHEN** se prueban avisos breves, tardíos, modificados, removidos y repetidos
- **THEN** solo eventos positivos atribuibles dentro del deadline confirman; el número de clics efectivos nunca supera uno

#### Scenario: DOM y transporte adversos
- **WHEN** aparecen shadow roots/iframes soportados, conexión perdida o pestaña cerrada
- **THEN** se conserva el aislamiento y el resultado es verificable o queda explícitamente ambiguo

#### Scenario: Fallos actuales reproducidos
- **WHEN** se ejecutan las regresiones de error falso positivo, toast viejo, estado genérico, historial literal, ID vacío y cambio de campaña
- **THEN** todos cumplen sus expectativas de seguridad sin debilitar los tests existentes

### Requirement: Auditoría cruzada de persistencia
La auditoría SHALL comprobar la línea reservada contra una lectura independiente
por motor y guardar el resultado, sin interpretar elegibilidad como persistencia.

#### Scenario: Línea falta o está duplicada
- **WHEN** un motor encuentra cero o varias ocurrencias de la línea reservada
- **THEN** la auditoría registra discrepancia y no declara persistencia correcta

#### Scenario: Ambos motores coinciden
- **WHEN** ambos leen exactamente una ocurrencia en el registro esperado
- **THEN** se informa persistencia verificada para ese registro, sin inferir entrega de WhatsApp

### Requirement: Comparación con denominadores explícitos
Las métricas SHALL distinguir leads únicos, evaluaciones, descartados, fallos,
sesión inicial y caliente, y SHALL comparar pares equivalentes con orden registrado.

#### Scenario: Lote de ochenta leads con dos motores
- **WHEN** se obtienen 160 resultados para 80 leads con descartados de cero segundos
- **THEN** se muestran ambos recuentos y los descartados no contaminan el tiempo de navegación de los pares aptos

#### Scenario: Un motor falla en un lead
- **WHEN** hay un desacuerdo de estado
- **THEN** aparece como discrepancia con razón concreta y se excluye del conjunto de pares exitosos sin ocultar el fallo

### Requirement: Puertas de habilitación del piloto
El siguiente piloto real SHALL comenzar solo tras tests determinísticos y fixture
aprobados, conservación de bloqueos y selección de leads aptos sin reservas previas.

#### Scenario: Falla una prueba crítica
- **WHEN** hay falsos éxitos, pérdida de historial, duplicación o navegación de pestaña ajena en las pruebas
- **THEN** el piloto real permanece no habilitado y se informa el bloqueo concreto

#### Scenario: Piloto con grupos distintos
- **WHEN** pasan las puertas y se ejecuta un envío controlado por motor
- **THEN** se usan leads distintos seleccionados para ese piloto, se captura evidencia y se detiene la ampliación ante ambigüedad
