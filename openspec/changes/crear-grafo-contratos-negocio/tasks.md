## 1. Protección del artefacto existente y harness

- [x] 1.1 Registrar ruta, tamaño y SHA-256 de `documentador-architecture.html`, y localizar el directorio servido por el puerto local. Verificación: evidencia versionada y acceso de solo lectura al HTML existente.
- [x] 1.2 Definir las rutas independientes para la fuente, plantilla, generador, tests y `documentador-business-contracts.html`. Verificación: ninguna ruta de salida coincide con el artefacto técnico.
- [x] 1.3 Integrar comandos determinísticos para validar contratos, generar el HTML y ejecutar el smoke local usando el framework existente. Verificación: cada comando devuelve cero y un error controlado devuelve código distinto de cero.
- [x] 1.4 Añadir el nuevo conjunto de verificaciones al harness/CI no destructivo sin acceder a Salesforce. Verificación: suite completa, lint, build y OpenSpec pasan.

## 2. Fuente contractual y trazabilidad OpenSpec

- [x] 2.1 Crear el esquema estructurado de macrofunciones, contratos, relaciones, referencias normativas y evidencia técnica. Verificación: campos ausentes, IDs duplicados y relaciones rotas son rechazados.
- [x] 2.2 Mapear las nueve macrofunciones aprobadas a requisitos y escenarios funcionales vigentes mediante una allowlist explícita. Verificación: cada macrofunción tiene al menos una referencia OpenSpec resoluble.
- [x] 2.3 Redactar en español los propósitos, entradas, resultados, reglas y fallos esperados sin nombres técnicos en la capa ejecutiva. Verificación: revisión de vocabulario y snapshots de contratos.
- [x] 2.4 Añadir referencias opcionales a implementación, tests y estado de verificación, manteniéndolas separadas del contrato normativo. Verificación: una evidencia ausente se muestra como pendiente y no como aprobada.
- [x] 2.5 Implementar el verificador de referencias OpenSpec, ambigüedades y fuentes archivadas no vigentes. Verificación: referencias inexistentes, duplicadas o prohibidas hacen fallar el comando.

## 3. Generación del segundo gráfico

- [x] 3.1 Crear un generador determinístico que produzca un HTML autocontenido desde la fuente contractual. Verificación: dos generaciones consecutivas sin cambios producen el mismo hash.
- [x] 3.2 Implementar el recorrido visual principal y las rutas alternativas de duplicado, error recuperable y corrección. Verificación: todos los nodos y relaciones del JSON aparecen una sola vez en el HTML.
- [x] 3.3 Implementar el panel de contrato con divulgación progresiva para OpenSpec y evidencia técnica. Verificación: la vista inicial no expone nombres de archivos, funciones, puertos ni protocolos.
- [x] 3.4 Añadir temas claro/oscuro, diseño adaptable y modo de presentación sin dependencias de red. Verificación: el artefacto funciona con red bloqueada en los tamaños de pantalla acordados.
- [x] 3.5 Generar `documentador-business-contracts.html` en la ubicación servida y comprobar que el SHA-256 del gráfico técnico no cambió. Verificación: ambas URLs responden y muestran títulos inequívocos.

## 4. Pruebas de contrato, accesibilidad y privacidad

- [x] 4.1 Añadir tests unitarios del esquema, recorrido, completitud de contratos y resolución OpenSpec. Verificación: casos válidos e inválidos pasan con mensajes identificables.
- [x] 4.2 Añadir smoke de navegador local para apertura, selección, cierre, enlaces y secciones desplegables. Verificación: cero errores de consola y contenido esperado por macrofunción.
- [x] 4.3 Verificar navegación con teclado, foco visible, nombres accesibles, contraste y comportamiento adaptable. Verificación: auditoría automática y recorrido manual Given/When/Then.
- [x] 4.4 Escanear fuente, HTML y exportaciones con canarios y patrones sensibles. Verificación: una fuga sintética deliberada bloquea la generación.
- [x] 4.5 Ejecutar pruebas de regresión del gráfico técnico y de la aplicación. Verificación: el artefacto original conserva su hash y el harness completo permanece verde.

## 5. Revisión y publicación

- [ ] 5.1 Presentar la vista a una persona no técnica y registrar si puede explicar el recorrido y tres contratos sin asistencia técnica. Verificación: checklist de comprensión con observaciones sanitizadas.
- [ ] 5.2 Ajustar terminología aprobada, incluida la decisión `Cargar base de Leads` versus `Cargar BD`, sin alterar las referencias normativas. Verificación: glosario y snapshots actualizados.
- [ ] 5.3 Ejecutar format, lint, tests, generación reproducible, smoke, privacidad y `openspec validate --changes`. Verificación: todos los gates obligatorios devuelven código cero.
- [ ] 5.4 Actualizar Graphify, presentar ambas URLs y solicitar aprobación antes de commit o publicación. Verificación: evidencia final, `git status` revisado y autorización explícita.
