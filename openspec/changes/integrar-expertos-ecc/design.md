## Context

El proyecto ya dispone de un harness gobernado por OpenSpec, Graphify y `AGENTS.md`. OpenSpec define el objetivo, los requisitos, el diseño, las tareas y el criterio de terminación; Graphify aporta contexto estructural del codebase; `AGENTS.md` fija las fases, las confirmaciones humanas y las restricciones operativas. `MEMORY.md`, los scripts de verificación y CI complementan esas fuentes. Esta integración no debe crear una autoridad paralela ni permitir que una recomendación de un experto cambie esas reglas.

ECC 2.2.3 ofrece procedimientos y perfiles especializados útiles, pero su catálogo completo, sus hooks, sus MCP y su configuración global aumentarían la superficie ejecutable y no ofrecen paridad idéntica entre harnesses. Además, los agentes publicados por ECC no se convierten automáticamente en roles nativos de Codex. Por ello se evaluará una selección pequeña mediante adaptadores controlados por el proyecto.

El piloto se ejecutará fuera del entorno habitual: un worktree dedicado contendrá el cambio experimental y un `CODEX_HOME` dedicado aislará roles, skills, cachés y configuración. La fuente ECC quedará fijada a la versión `v2.2.3` y a su commit resuelto. No se habilitarán hooks, MCP, memoria ECC ni configuración global durante esta etapa.

Antes del piloto deben corregirse los controles del harness capaces de producir falsos positivos. Una comparación A/B no sería válida si la línea base omite versiones, no comprueba la terminación OpenSpec o ejecuta solo una fracción de los gates en CI.

Los interesados son quienes mantienen el harness, los desarrolladores que ejecutan los cambios y las personas que revisan seguridad, pruebas y promociones de aprendizaje. Los resultados deben ser auditables por alguien distinto de quien realizó la ejecución.

## Goals / Non-Goals

**Goals:**

- Evaluar de forma reproducible cuatro expertos: `explorer`, `reviewer`, `security-reviewer` y `test-reviewer`.
- Adaptar selectivamente las prácticas `tdd-workflow`, `verification-loop`, `security-review`, `agent-eval` y `architecture-decision-records` de ECC 2.2.3.
- Mantener OpenSpec, Graphify y `AGENTS.md` como autoridades y hacer explícita la precedencia ante conflictos.
- Ejecutar una comparación A/B con tareas equivalentes, mismas restricciones y evidencia determinística.
- Medir calidad, defectos detectados, falsos positivos, cumplimiento del proceso, tiempo, tokens y coste estimado.
- Introducir aprendizaje continuo gobernado con el ciclo `observe → candidate → human review → promote/reject → rollback`.
- Aplicar mínimo privilegio, trazabilidad de procedencia y una reversión que no dependa de ECC.
- Permitir que una adopción posterior sea incremental y que cada experto o skill pueda habilitarse o retirarse por separado.

**Non-Goals:**

- Sustituir OpenSpec, Graphify, `AGENTS.md`, `MEMORY.md`, las siete fases o los gates existentes.
- Instalar el catálogo completo de ECC o intentar reproducir sus 68 agentes.
- Instalar hooks, MCP, Memory Vault, continuous learning automático o configuración global de ECC durante el piloto.
- Permitir que un experto modifique código productivo, haga commits, publique cambios o altere reglas por iniciativa propia.
- Alcanzar paridad entre todos los IDE en esta fase; primero se validará el flujo aislado de Codex.
- Adoptar automáticamente una nueva versión de ECC o usar referencias móviles como `latest`.
- Evaluar o integrar Ruflo dentro de este cambio.
- Usar el piloto para implementar funcionalidades de producto no necesarias para la evaluación.

## Decisions

### 1. Aislamiento doble y versión inmutable

El tratamiento B se ejecutará en un worktree creado expresamente para el piloto. El proceso recibirá un `CODEX_HOME` cuya ruta esté dentro de un directorio temporal o de evaluación identificado, nunca el perfil habitual del usuario. Un preflight verificará ambas rutas y abortará si detecta el worktree principal o el `CODEX_HOME` global.

ECC se resolverá desde el tag `v2.2.3`; se registrarán repositorio, tag, commit, licencia y hash de cada archivo importado. Los experimentos conservarán el mismo snapshot durante toda la comparación. Una actualización de ECC requerirá otro cambio o una revisión explícita de procedencia.

**Alternativas consideradas:** instalar el plugin nativo en el perfil normal facilitaría la puesta en marcha, pero mezclaría caché, configuración y catálogo con el entorno diario. Clonar la rama principal o usar `latest` reduciría trabajo inicial, pero impediría reproducir resultados. Ambas alternativas se descartan.

### 2. Adaptación selectiva en lugar de instalación completa

Solo se incorporarán los cinco procedimientos seleccionados y las instrucciones mínimas necesarias para los cuatro roles. Cada elemento tendrá un registro de procedencia y un adaptador local que traduzca comandos, permisos y criterios de salida al harness del proyecto.

Las adaptaciones obligatorias incluyen:

- eliminar commits automáticos y cualquier recomendación de push de `tdd-workflow`;
- sustituir comandos POSIX específicos de `verification-loop` por los comandos estándar del proyecto o sus equivalentes PowerShell/shell;
- hacer que `security-review` produzca hallazgos trazables sin acceder a secretos;
- usar `agent-eval` para evaluar evidencia y no para autoaprobar agentes;
- registrar decisiones arquitectónicas duraderas mediante ADR, manteniendo OpenSpec como fuente del alcance y de los requisitos.

Los archivos adaptados no se actualizarán directamente desde upstream. Una actualización repetirá comparación, revisión de diferencias y verificaciones.

**Alternativas consideradas:** cargar el catálogo completo mediante el plugin simplificaría las actualizaciones, pero añadiría capacidades no evaluadas, ruido de descubrimiento y superficie ejecutable. Copiar los archivos sin adaptarlos preservaría fidelidad upstream, pero entraría en conflicto con confirmaciones, comandos y gates locales. Se descartan ambas opciones.

### 3. Jerarquía de autoridad y resolución de conflictos

La precedencia operativa será:

1. instrucciones del sistema y del usuario;
2. `AGENTS.md` y las restricciones de seguridad del entorno;
3. artefactos aprobados del cambio OpenSpec;
4. verificadores determinísticos, Graphify y documentación gobernada del proyecto;
5. instrucciones de los expertos y skills adaptados.

Los expertos son asesores. Si una instrucción inferior contradice una superior, el agente debe detener esa acción, registrar el conflicto y escalarlo; no debe reconciliarlo silenciosamente. Una salida narrativa nunca invalida un fallo de test, lint, build, validación OpenSpec o verificación del harness.

**Alternativas consideradas:** fusionar las reglas ECC con `AGENTS.md` daría una sola superficie de lectura, pero ocultaría procedencia y haría difícil revertir. Permitir precedencia contextual a cada experto aumentaría autonomía, pero volvería ambiguas las restricciones. Se mantiene una jerarquía única y explícita.

### 4. Roles pequeños, de mínimo privilegio y con contratos de handoff

Los roles tendrán responsabilidades no solapadas:

- `explorer`: consulta Graphify y artefactos existentes, delimita componentes afectados, dependencias, incertidumbres y evidencia; no modifica archivos.
- `reviewer`: contrasta diff, requisitos, diseño y gates; clasifica hallazgos por severidad y evidencia; no corrige lo revisado.
- `security-reviewer`: analiza límites de confianza, secretos, permisos, dependencias y operaciones destructivas; trabaja en modo de solo lectura.
- `test-reviewer`: comprueba cobertura de criterios, calidad de casos, resultados y omisiones del harness; puede ejecutar comandos no destructivos aprobados, pero no modificar tests ni implementación.

El agente coordinador conserva la implementación. Cada invocación recibe objetivo, alcance, fuentes permitidas, restricciones, presupuesto y formato de salida. Cada handoff devuelve como mínimo: identificador de tarea, artefactos consultados, hallazgos con evidencia, severidad o prioridad, confianza, comandos ejecutados, resultado y preguntas abiertas. La revisión final debe ejecutarse en un contexto independiente del implementador.

El routing será explícito: `explorer` antes de cerrar impacto y diseño; `reviewer` tras una unidad implementada; `security-reviewer` cuando cambien entradas, secretos, permisos, red, dependencias o comandos; `test-reviewer` antes de aceptar los gates. Si ninguna condición aplica, no se invoca el experto.

**Alternativas consideradas:** un swarm autónomo reduciría routing manual, pero elevaría coste, dificultaría la atribución y podría saltar fases. Un único experto generalista sería más barato, pero mezclaría responsabilidades y reduciría independencia. Se eligen roles acotados con routing determinístico.

### 5. Evaluación A/B emparejada y con gates de adopción

La variante A será el harness corregido sin capacidades ECC. La variante B será ese mismo harness más los roles y skills seleccionados. Ambas usarán el mismo modelo y configuración, el mismo briefing congelado, límites equivalentes de tiempo/tokens, dependencias fijadas y worktrees limpios derivados del mismo commit.

El conjunto incluirá al menos tres casos representativos: exploración y diseño de impacto transversal, corrección con TDD y revisión de un cambio con riesgo de seguridad. Se alternará el orden A/B entre casos para reducir sesgo de aprendizaje y se conservarán las entradas de evaluación. Quien puntúe los resultados no verá la etiqueta de la variante cuando sea viable.

Métricas primarias:

- cumplimiento de criterios de aceptación y gates determinísticos;
- defectos reales detectados y defectos escapados;
- violaciones de alcance, permisos o fases;
- precisión de hallazgos revisada humanamente.

Métricas secundarias:

- tiempo total y tiempo de revisión;
- tokens, invocaciones y coste estimado;
- número de falsos positivos y duplicados;
- calidad y completitud de los handoffs;
- estabilidad entre repeticiones.

La variante B no será adoptada si empeora un gate determinístico, introduce una violación de seguridad/proceso o no puede revertirse limpiamente. La adopción de cada componente será independiente: una skill puede rechazarse aunque otro experto resulte útil. Los umbrales cuantitativos se fijarán en los specs o tareas antes de ejecutar el primer caso, para evitar ajustarlos a los resultados.

**Alternativas consideradas:** comparar una tarea realizada una sola vez sería más barato, pero confundiría variación del modelo con efecto del harness. Comparar el ECC completo contra el harness actual impediría atribuir beneficios y riesgos. Se adopta un diseño emparejado, selectivo y repetible.

### 6. Aprendizaje continuo como flujo gobernado

El piloto no activará el mecanismo automático de continuous learning de ECC. La observación generará candidatos inertes con un esquema mínimo: ID, fecha, origen, evidencia sanitizada, problema recurrente, regla o práctica propuesta, alcance, confianza, conflictos conocidos, responsable, estado y referencia de rollback.

Los estados permitidos serán `observed`, `candidate`, `approved`, `rejected`, `promoted` y `rolled-back`. Pasar de `candidate` a `approved` exige revisión humana explícita. La promoción se realiza mediante un cambio normal y revisable sobre la fuente apropiada (`AGENTS.md`, una skill, `MEMORY.md`, un ADR o un spec); el registro candidato por sí mismo nunca modifica comportamiento.

Cada promoción debe definir la señal de éxito, su vigencia y la reversión exacta. Si produce regresiones, conflicto con una autoridad superior o ruido repetido, se restaura la versión anterior mediante un cambio trazable y el candidato pasa a `rolled-back`. Los candidatos rechazados o revertidos no pueden ser reactivados sin nueva evidencia y otra aprobación.

No se guardarán razonamientos internos, credenciales, PII, datos de clientes ni contenido innecesario de sesiones. La evidencia se reducirá a decisiones, comandos, resultados y referencias verificables.

**Alternativas consideradas:** promover automáticamente patrones frecuentes aceleraría el aprendizaje, pero permitiría contaminación, prompt injection y degradación acumulativa. Guardar toda la conversación facilitaría análisis posteriores, pero aumentaría riesgos de privacidad y contexto. Se adopta promoción humana y minimización de datos.

### 7. Seguridad, observabilidad y terminación del piloto

La fuente ECC se tratará como dependencia externa ejecutable. Antes de importar archivos se revisarán licencia, procedencia, hashes, instrucciones de shell, acceso a red y permisos solicitados. Hooks y MCP permanecerán ausentes; los roles no recibirán credenciales y las ejecuciones se harán con el sandbox y la aprobación normal del proyecto.

Cada corrida A/B producirá un registro sanitizado con: caso, variante, commit base, versión/configuración del modelo, snapshot ECC, roles/skills habilitados, comandos y resultados, métricas, incidentes y decisión humana. No se capturará contenido secreto ni cadena de pensamiento. Un resultado sin metadatos suficientes se considerará inválido.

El piloto termina cuando los casos planeados tienen evidencia completa, los gates pasan en ambos entornos o sus fallos están explicados, existe una revisión independiente y se ha tomado una decisión por componente: adoptar, adaptar nuevamente o rechazar. Ninguna mejora subjetiva sustituye este criterio.

**Alternativas consideradas:** habilitar hooks permitiría automatizar observación y routing, pero ampliaría la superficie de confianza antes de demostrar valor. Registrar solo una conclusión reduciría artefactos, pero impediría auditar costes, fallos y atribución. Se priorizan invocación explícita y evidencia mínima reproducible.

## Risks / Trade-offs

- **Las instrucciones importadas pueden contradecir el proceso local** → usar adaptadores, jerarquía explícita, pruebas de conflicto y revisión antes de cada promoción.
- **El worktree o `CODEX_HOME` aislado podría apuntar por error al entorno habitual** → ejecutar un preflight que compare rutas resueltas y aborte ante coincidencias o ubicaciones no autorizadas.
- **Un experto podría parecer activo sin ser un rol nativo real de Codex** → añadir un smoke test de identidad, permisos, entrada y handoff para cada rol; no inferir capacidad desde el catálogo ECC.
- **La variabilidad del modelo puede sesgar el A/B** → usar casos emparejados, configuración congelada, orden alternado, repeticiones y evaluación ciega cuando sea posible.
- **La revisión independiente aumenta tokens y latencia** → invocar roles solo por reglas de routing y medir el coste marginal por defecto útil detectado.
- **La selección local crea una bifurcación respecto de ECC** → conservar procedencia y hashes, limitar adaptaciones y revisar upstream mediante cambios explícitos.
- **No usar hooks reduce la automatización** → usar comandos explícitos y gates del harness durante el piloto; reconsiderar hooks solo en otro cambio y con análisis de seguridad propio.
- **Los hallazgos pueden generar falsos positivos o duplicados** → exigir evidencia localizable, severidad, confianza y adjudicación humana; medir precisión.
- **El aprendizaje puede consolidar una observación errónea o maliciosa** → mantener candidatos inertes, exigir evidencia repetible y revisión humana, y definir rollback antes de promoción.
- **Los registros pueden filtrar datos sensibles** → usar fixtures sintéticos, sanitización, allowlists de campos y revisión antes de versionar evidencia.
- **Reparar primero el harness puede ampliar el calendario** → tratar esas correcciones como prerrequisito verificable; sin una línea base confiable no se ejecutará el A/B.
- **Una adopción parcial puede producir experiencias distintas entre IDE** → documentar el soporte real y posponer la distribución multi-IDE hasta demostrar el flujo de Codex.

## Migration Plan

1. **Establecer la línea base:** corregir y ejecutar los verificadores de versiones, finalización OpenSpec, tests, lint, build y CI. Registrar resultados y commit base.
2. **Congelar la evaluación:** definir casos, fixtures, rúbrica, métricas, umbrales, presupuesto y responsables antes de observar resultados.
3. **Preparar el aislamiento:** crear el worktree de piloto y el `CODEX_HOME` dedicado; ejecutar preflight y confirmar que el perfil global y el worktree principal permanecen sin cambios.
4. **Registrar la procedencia:** resolver ECC `v2.2.3` a un commit, verificar licencia y hashes, e inventariar únicamente los roles y skills seleccionados.
5. **Adaptar y probar componentes:** aplicar mínimo privilegio, comandos locales y contratos de handoff; ejecutar smokes de descubrimiento, routing, permisos, conflictos y terminación.
6. **Ejecutar A/B:** correr las variantes sobre los casos emparejados, alternar orden, recopilar registros sanitizados y repetir los casos definidos por la rúbrica.
7. **Revisar de forma independiente:** adjudicar hallazgos, calcular métricas y revisar seguridad, coste, mantenibilidad y cumplimiento de las fuentes de verdad.
8. **Decidir por componente:** adoptar, volver a adaptar o rechazar cada rol y skill. La aprobación del piloto no habilita hooks, MCP, memoria ECC ni configuración global.
9. **Promover de forma controlada:** cualquier componente aprobado entrará al repositorio principal mediante tareas OpenSpec, pruebas, revisión y CI propias. Los aprendizajes seguirán el flujo humano definido y no se promoverán como efecto lateral del piloto.
10. **Cerrar y limpiar:** documentar el resultado, eliminar el `CODEX_HOME` y el worktree experimentales cuando ya no se necesiten y confirmar que el entorno habitual no conserva estado ECC.

**Rollback del piloto:** detener ejecuciones, conservar solo evidencia sanitizada necesaria y eliminar el worktree y el `CODEX_HOME` aislados. Como el piloto no modifica configuración global ni habilita hooks/MCP, el harness principal continúa sin ECC.

**Rollback después de una adopción:** deshabilitar el routing del componente afectado, restaurar mediante un cambio revisable el manifiesto y los adaptadores anteriores, ejecutar la suite completa y marcar como `rolled-back` los aprendizajes relacionados. Los artefactos OpenSpec, Graphify y `AGENTS.md` siguen siendo válidos durante la reversión.

## Open Questions

- ¿Qué tres o más tareas concretas formarán el corpus A/B y cuántas repeticiones necesita cada una?
- ¿Qué mejora mínima en defectos útiles o calidad justifica el coste adicional, y cuál será el límite máximo aceptable de tokens y tiempo?
- ¿Qué persona o rol adjudicará los hallazgos y aprobará la promoción de cada candidato de aprendizaje?
- ¿Dónde se conservarán los registros A/B y candidatos, y cuál será su política de retención y sanitización?
- ¿Los ADR vivirán en una carpeta nueva controlada por el proyecto o se incorporarán al mecanismo documental ya existente?
- ¿Con qué frecuencia se revisará una nueva versión de ECC y qué pruebas de regresión serán obligatorias antes de actualizar los archivos adaptados?
- Si el piloto Codex es exitoso, ¿qué IDE será el siguiente y qué grado de equivalencia funcional se exigirá antes de declararlo soportado?
