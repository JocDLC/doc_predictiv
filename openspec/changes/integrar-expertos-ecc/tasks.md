## 1. Baseline confiable del harness

- [ ] 1.1 Mapear estas tareas contra `multi-ide-harness` y `auditar-calidad-integral`, asignar una sola fuente de implementación por control y validar con `openspec validate --changes`.
- [ ] 1.2 Escribir primero pruebas de regresión para comandos ausentes, versiones incompatibles y verificadores que solo comprueban presencia; ejecutar `python -m unittest discover -s automation_salesforce/tests -p "test_*harness*.py"`.
- [ ] 1.3 Crear una fuente de versiones legible por máquina y un gate que compare `VERSIONS.md`, bootstrap, setup, verificadores y CI; probar el caso de drift intencional.
- [ ] 1.4 Hacer que `verify-setup.ps1` y `verify-setup.sh` comprueben ruta y versión efectivas de cada herramienta y propaguen errores; ejecutar ambos smokes en sus plataformas.
- [ ] 1.5 Completar el comando canónico `python automation_salesforce/harness.py verify` para formato, lint, compile/build, tests por capa, cobertura, OpenSpec, configuraciones multi-IDE y Graphify, reportando explícitamente cualquier omisión.
- [ ] 1.6 Definir umbrales versionados de líneas y ramas con un ratchet inicial y prueba que falle si un módulo productivo desaparece del reporte; ejecutar el gate de cobertura.
- [ ] 1.7 Endurecer CI para Linux y Windows, dependencias fijadas, permisos mínimos y cero gates blandos; verificar el workflow con linter y una ejecución de ambas matrices.
- [ ] 1.8 Añadir gates de drift para Graphify y configuraciones multi-IDE; comprobar que un cambio sintético no sincronizado hace fallar cada gate.
- [ ] 1.9 Implementar terminación real de OpenSpec y manifiesto sanitizado de evidencia; probar que `openspec validate` exitoso con una tarea pendiente no permita cerrar.
- [ ] 1.10 Ejecutar el comando canónico, registrar el commit base y conservar la evidencia de la variante A antes de incorporar ECC.

## 2. Contrato de evaluación

- [ ] 2.1 Versionar al menos tres casos A/B: exploración transversal, corrección TDD y revisión con riesgo de seguridad.
- [ ] 2.2 Fijar antes de ejecutar el piloto la rúbrica, umbrales de adopción, repeticiones, límites de tiempo/tokens y reglas de descalificación.
- [ ] 2.3 Preparar fixtures sintéticos y una política de sanitización y retención que excluya secretos, PII y datos operativos de clientes.
- [ ] 2.4 Registrar modelo, configuración, briefing congelado, responsable de adjudicación y formato de evidencia; validar que una corrida incompleta sea rechazada.

## 3. Aislamiento y procedencia de ECC

- [ ] 3.1 Crear scripts reversibles para preparar y retirar un worktree de piloto y un `CODEX_HOME` dedicado, sin tocar el árbol ni el perfil habitual.
- [ ] 3.2 Implementar un preflight que resuelva rutas reales y aborte ante el worktree principal, el `CODEX_HOME` global o una ruta no autorizada; cubrir los tres casos con tests.
- [ ] 3.3 Resolver ECC `v2.2.3` a un commit inmutable y registrar repositorio, tag, commit, licencia y hashes de los archivos candidatos.
- [ ] 3.4 Revisar y copiar únicamente los cuatro perfiles y cinco prácticas aprobadas, conservando atribución y una lista de diferencias locales.
- [ ] 3.5 Añadir un gate que demuestre la ausencia de hooks, MCP, Memory Vault, referencias móviles y configuración global en el piloto.
- [ ] 3.6 Ejecutar el smoke de instalación y rollback aislados y comprobar mediante `git status` y hashes que no hubo mutaciones externas.

## 4. Expertos y routing

- [ ] 4.1 Definir el esquema de contrato de experto y su validador para identidad, responsabilidad, triggers, entradas, salidas, herramientas, prohibiciones, presupuesto, verificaciones y fallback.
- [ ] 4.2 Implementar contratos mínimos para `explorer`, `reviewer`, `security-reviewer` y `test-reviewer`, con permisos de solo lectura salvo ejecuciones no destructivas declaradas.
- [ ] 4.3 Implementar reglas versionadas de routing y pruebas para coincidencia, ausencia de coincidencia y conflicto entre reglas.
- [ ] 4.4 Implementar el contrato de handoff y rechazar transferencias sin alcance, evidencia, verificaciones o riesgos residuales.
- [ ] 4.5 Implementar timeout, validación de salida y fallback seguro sin permitir que un error marque la tarea como exitosa.
- [ ] 4.6 Exigir revisión independiente del implementador y bloquear el cierre cuando exista un hallazgo bloqueante abierto.
- [ ] 4.7 Ejecutar smokes de descubrimiento, identidad, permisos, routing, handoff y fallo seguro para los cuatro expertos.

## 5. Adaptación selectiva de prácticas ECC

- [ ] 5.1 Adaptar `tdd-workflow` al ciclo local eliminando commits, pushes y cambios de fase automáticos; comprobar RED, GREEN y refactor con un fixture.
- [ ] 5.2 Adaptar `verification-loop` a PowerShell y shell usando exclusivamente el comando canónico y preservando códigos de salida.
- [ ] 5.3 Adaptar `security-review` para producir hallazgos localizables sin leer secretos ni ampliar permisos; verificarlo con fixtures seguros y prohibidos.
- [ ] 5.4 Adaptar `agent-eval` para evaluar evidencia sin autoaprobar expertos y `architecture-decision-records` para enlazar ADR con OpenSpec.
- [ ] 5.5 Añadir pruebas de precedencia que demuestren que una instrucción ECC no puede contradecir sistema, usuario, `AGENTS.md`, OpenSpec ni un gate fallido.
- [ ] 5.6 Añadir un control de procedencia y drift que obligue a revisar hashes y diferencias antes de actualizar cualquier componente importado.

## 6. Continuous learning gobernado

- [ ] 6.1 Definir y documentar ubicación, responsable, retención y esquema de candidatos antes de habilitar su captura.
- [ ] 6.2 Implementar los estados `observed`, `candidate`, `approved`, `rejected`, `promoted` y `rolled-back` con historial append-only y transiciones validadas.
- [ ] 6.3 Implementar captura en modo observación y demostrar que crear un candidato no modifica prompts, reglas, skills, memoria, permisos ni configuración activa.
- [ ] 6.4 Implementar sanitización, detección de secretos/PII, deduplicación y detección de conflictos con las fuentes de verdad.
- [ ] 6.5 Implementar decisión humana explícita con responsable, fecha, justificación, evidencia y alcance; tratar la ausencia de decisión como rechazo operativo.
- [ ] 6.6 Implementar promoción exclusivamente mediante un cambio OpenSpec verificable que enlace candidato, aprobación, pruebas, archivos y rollback.
- [ ] 6.7 Implementar y probar rollback de un aprendizaje promovido sin borrar su historial ni reactivar automáticamente candidatos rechazados.
- [ ] 6.8 Añadir pruebas de regresión para autoactivación, prompt injection, datos sensibles, duplicados, conflictos, promoción incompleta y reversión.

## 7. Ejecución y decisión A/B

- [ ] 7.1 Implementar un runner que congele entradas, alterne el orden A/B y registre commit, entorno, snapshot ECC, métricas e incidentes sin datos sensibles.
- [ ] 7.2 Ejecutar la variante A y la variante B sobre cada caso y repetición definidos, conservando resultados determinísticos y costes comparables.
- [ ] 7.3 Adjudicar a ciegas cuando sea viable defectos reales, falsos positivos, duplicados, calidad de handoffs y violaciones de proceso.
- [ ] 7.4 Calcular calidad, defectos escapados, tiempo, tokens, coste y estabilidad; invalidar cualquier corrida con metadatos o gates incompletos.
- [ ] 7.5 Decidir por separado adoptar, readaptar o rechazar cada experto y práctica usando únicamente los umbrales fijados antes del piloto.
- [ ] 7.6 Ejecutar el rollback de los componentes rechazados y confirmar que la variante A continúa funcionando sin ECC.

## 8. Documentación y cierre

- [ ] 8.1 Documentar instalación aislada, uso, routing, aprendizaje, seguridad, actualización y rollback sin declarar soporte multi-IDE no probado.
- [ ] 8.2 Ejecutar `python automation_salesforce/harness.py verify` y corregir la causa raíz de cualquier gate fallido sin debilitar tests.
- [ ] 8.3 Ejecutar `openspec validate --changes` y comprobar que tareas, criterios, evidencia, bloqueos y riesgos aceptados reflejen el estado real.
- [ ] 8.4 Ejecutar `graphify update .`, verificar el diff y actualizar `MEMORY.md` solo con decisiones aprobadas y sanitizadas.
- [ ] 8.5 Presentar el resultado del piloto al usuario y solicitar aprobación antes de promover componentes al entorno habitual o pasar a otro IDE.
