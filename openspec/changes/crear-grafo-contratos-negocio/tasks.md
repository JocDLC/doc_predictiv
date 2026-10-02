## 1. Protección del artefacto existente y harness

- [x] 1.1 Registrar ruta, tamaño y SHA-256 de `documentador-architecture.html`, y localizar el directorio servido por el puerto local. Verificación: evidencia versionada y acceso de solo lectura al HTML existente.
- [x] 1.2 Definir rutas independientes para las fuentes, generadores, pruebas y el gráfico de negocio. Verificación: ninguna ruta de salida coincide con el artefacto técnico.
- [x] 1.3 Integrar comandos determinísticos para validar contratos, generar un artefacto y ejecutar el smoke local. Verificación: cada comando devuelve cero y un error controlado devuelve un código distinto de cero.
- [x] 1.4 Añadir las verificaciones al harness/CI no destructivo sin acceder a Salesforce. Verificación: suite completa, lint, build y OpenSpec pasan.

## 2. Primera fuente contractual y trazabilidad

- [x] 2.1 Crear un esquema estructurado de macrofunciones, contratos, relaciones, referencias normativas y evidencia técnica. Verificación: campos ausentes, IDs duplicados y relaciones rotas son rechazados.
- [x] 2.2 Mapear las macrofunciones iniciales a requisitos y escenarios funcionales mediante una allowlist explícita. Verificación: cada macrofunción tiene al menos una referencia OpenSpec resoluble.
- [x] 2.3 Redactar propósitos, entradas, resultados, reglas y fallos esperados en español. Verificación: pruebas de contenido y snapshots de contratos.
- [x] 2.4 Separar implementación, pruebas y estado de verificación del contrato normativo. Verificación: una evidencia ausente se muestra como pendiente y no como aprobada.
- [x] 2.5 Implementar el verificador de referencias OpenSpec, ambigüedades y fuentes archivadas no vigentes. Verificación: referencias inexistentes, duplicadas o prohibidas hacen fallar el comando.

## 3. Prototipo inicial no aprobado

- [x] 3.1 Generar un segundo HTML independiente desde la primera fuente contractual. Verificación: el archivo técnico conserva su hash.
- [x] 3.2 Implementar un recorrido inicial, paneles contractuales, temas y adaptación de pantalla. Verificación: pruebas automatizadas y smoke local pasan.
- [x] 3.3 Verificar contratos, accesibilidad, privacidad y regresión de la aplicación. Verificación: harness completo verde.
- [x] 3.4 Presentar el prototipo durante Fase 5. Resultado: **revisión no aprobada** porque no fue generado con Archify, mezcló los recorridos y anunció XLSX sin soporte operativo.

## 4. Corregir el modelo de negocio y su fuente de verdad

- [x] 4.1 Registrar en la evidencia de revisión las tres causas de rechazo y marcar el prototipo como histórico, no vigente. Verificación: ningún reporte lo presenta como aprobado o publicable.
- [x] 4.2 Reorganizar el modelo en dos caminos: Salesforce → Wolkvox y Wolkvox → Salesforce. Verificación: una prueba estructural exige ambos caminos, sus orígenes y sus destinos.
- [x] 4.3 Incorporar la bifurcación `Documentar manualmente` / `Documentar con el bot` después de organizar los intentos. Verificación: ambas rutas son alcanzables y terminan en Salesforce.
- [x] 4.4 Corregir contratos y validadores para describir CSV como formato vigente y rechazar la afirmación de soporte XLSX. Verificación: un caso que anuncie XLSX como disponible falla con un mensaje identificable.
- [x] 4.5 Distinguir actividades del sistema, acciones manuales y acciones externas. Verificación: cada nodo tiene un tipo válido y la capa ejecutiva no atribuye automatizaciones inexistentes.

## 5. Generar el workflow nativo de Archify

- [x] 5.1 Crear un candidato Archify `workflow` schema v2 en un nuevo directorio `.archify/workflow-*`, con perfil `showcase` y estilo clásico estático. Verificación: el validador de Archify acepta el candidato.
- [x] 5.2 Representar visualmente los dos caminos mediante fases, carriles, nodos y aristas que expliquen el movimiento de la información. Verificación: la vista inicial muestra entradas, transformaciones, salidas y la bifurcación manual/bot sin etiquetas técnicas.
- [x] 5.3 Incorporar un contrato nativo por macrofunción con `Qué recibe`, `Qué entrega`, `Regla principal` y `Si falla`, más fuentes OpenSpec progresivas. Verificación: cada macrofunción tiene contrato completo y fuentes resolubles.
- [x] 5.4 Finalizar el candidato con Archify usando la raíz del repositorio y calidad `showcase`. Verificación: se generan HTML, recibos y evidencia de finalización válidos.
- [x] 5.5 Publicar el nuevo HTML en una URL independiente y comprobar que el SHA-256 del gráfico técnico no cambió. Verificación: ambas URLs responden, tienen títulos inequívocos y el hash técnico coincide con la línea base.

## 6. Pruebas de la corrección

- [x] 6.1 Actualizar y ampliar tests unitarios del esquema, los dos caminos, contratos, referencias y tipos de actividad. Verificación: casos válidos e inválidos pasan con mensajes identificables.
- [x] 6.2 Añadir regresiones específicas para CSV vigente, XLSX no anunciado, archivo Wolkvox con intentos y rutas manual/bot. Verificación: cada escenario OpenSpec tiene al menos una prueba automatizada o una comprobación Given/When/Then registrada.
- [x] 6.3 Ejecutar smoke de navegador para apertura, navegación, tarjetas, teclado, temas, tamaños habituales y errores de consola. Verificación: cero errores de consola y contenido esencial visible.
- [x] 6.4 Escanear candidato, HTML, recibos y exportaciones en busca de datos sensibles. Verificación: una fuga sintética deliberada bloquea la publicación.
- [x] 6.5 Ejecutar la suite completa, lint, build, generación reproducible y regresión del gráfico técnico. Verificación: todos los gates obligatorios devuelven código cero.

## 7. Revisión y cierre

- [ ] 7.1 Presentar el workflow a una persona no técnica y registrar si puede explicar los dos caminos, las entradas/salidas, la bifurcación manual/bot y tres contratos. Verificación: checklist de comprensión con observaciones sanitizadas.
- [x] 7.2 Ajustar únicamente vocabulario o disposición visual derivados de la revisión, sin alterar los contratos aprobados. Verificación: el destino común se muestra como `Documentar en Salesforce`, con tipo visual de sistema externo; candidato, snapshots y pruebas actualizados.
- [x] 7.3 Ejecutar `openspec validate --changes`, actualizar Graphify y revisar `git status`. Verificación: OpenSpec y Graphify quedan vigentes y no hay modificaciones accidentales del gráfico técnico.
- [ ] 7.4 Solicitar aprobación explícita del nuevo gráfico antes de archivar, commitear o publicar. Verificación: autorización registrada y tareas anteriores completas.
