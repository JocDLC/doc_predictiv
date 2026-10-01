## 1. Línea base y harness

- [x] 1.1 Registrar versiones, sistema, commit, estado del worktree, conteo actual de tests y lint sin modificar código productivo.
  - Verificación: `python --version`; `git status --short`; desde `automation_salesforce/`, `python -m unittest discover -s tests -v` y `python -m ruff check . --select E4,E7,E9,F`.
- [x] 1.2 Crear dependencias de desarrollo con versiones fijadas para cobertura, generación de casos y mutación selectiva, separadas de las dependencias de ejecución.
  - Verificación: instalar en un entorno limpio y ejecutar `python -m pip check`.
- [x] 1.3 Configurar comandos estándar para `format-check`, `lint`, `compile`, `test`, suites por capa, `coverage` y verificación completa.
  - Verificación: cada comando existe, devuelve código 0 en la línea base aplicable y falla deliberadamente ante una prueba rota temporal controlada.
- [x] 1.4 Añadir un smoke test del harness y documentar los comandos en el README sin incluir rutas o datos locales.
  - Verificación: ejecutar el smoke test desde una copia limpia del repositorio.

## 2. Cobertura y caracterización independiente

- [x] 2.1 Configurar cobertura de líneas y ramas sobre todos los módulos Python productivos y registrar la línea base por archivo.
  - Verificación: generar reporte de terminal y XML; confirmar que ningún módulo crítico está omitido.
- [x] 2.2 Añadir tests de caracterización para `salesforce_session.py`, incluyendo configuración, sesión autenticada/no autenticada, timeout y 2FA siempre manual.
  - Verificación: suite unitaria y cobertura del archivo en verde.
- [x] 2.3 Añadir tests de caracterización para `run_corrections.py`: éxito, conflicto, fallo, snapshot, resultado incremental y liberación del navegador.
  - Verificación: ningún caso usa navegador o datos reales; cobertura de ramas críticas en verde.
- [ ] 2.4 Añadir tests de caracterización para `ui_server.py` sobre `POST /api/run`, proceso ya activo, error de arranque, estado del proceso y método no permitido.
  - Verificación: servidor real en puerto efímero y `subprocess` controlado; cero procesos huérfanos.
- [ ] 2.5 Añadir tests de caracterización para `local_audit.py`, `open_persistent_browser.py`, runners de entrada y `verificar_pc.py` en rutas de éxito y fallo relevantes.
  - Verificación: suite completa y reporte de cobertura actualizado.
- [ ] 2.6 Eliminar los `ResourceWarning` de las pruebas HTTP sin ocultar warnings globalmente.
  - Verificación: `python -W error::ResourceWarning -m unittest discover -s tests -v`.

## 3. Contratos e integración local

- [ ] 3.1 Crear fixtures sintéticos mínimos para cola, resultado, snapshot, corrección, métricas y variantes seguras de DOM Lightning.
  - Verificación: escaneo de canarios confirma que no contienen patrones ni datos reales.
- [ ] 3.2 Probar el contrato UI → cola → `queue_loader` con selección total, parcial, vacía, campos faltantes, tipos inválidos y versión incompatible.
  - Verificación: los casos válidos conservan campos y los inválidos fallan sin volcar valores.
- [ ] 3.3 Probar el contrato runner → resultado/snapshot/métricas → UI, incluyendo `guardado`, `error`, `duplicado`, `omitido`, `corregido` y `conflicto`.
  - Verificación: conteos, estados, hashes, duraciones y visibilidad coinciden en ambos extremos.
- [ ] 3.4 Probar el servidor HTTP real con archivos temporales: GET, PUT y POST, token, CORS necesario, archivos ausentes y escrituras atómicas.
  - Verificación: ningún archivo se crea fuera del temporal permitido.
- [ ] 3.5 Probar el HTML principal en navegador local con fixtures sintéticos: selección, cola, exportación/importación, estados, snapshots, correcciones y clasificación de productividad.
  - Verificación: captura o reporte sintético del smoke, sin Salesforce y sin datos reales.
- [ ] 3.6 Probar compatibilidad de rutas Windows, UTF-8, separadores, nombres con espacios y límites de tamaño definidos.
  - Verificación: suite de contratos en Windows y CI Linux.

## 4. Robustez, propiedades y mutación

- [ ] 4.1 Añadir tests generativos para numeración `N INT`, normalización, validación de IDs, deduplicación, hashes y redondeo de métricas.
  - Verificación: semillas reproducibles y cero ejemplos con datos reales.
- [ ] 4.2 Probar JSON truncado, escritura parcial, archivo reemplazado durante lectura y conservación del último estado válido.
  - Verificación: el estado previo permanece intacto tras cada fallo inyectado.
- [ ] 4.3 Probar interrupción después de cada etapa crítica y reanudación sin duplicar resultados, snapshots ni escrituras confirmadas.
  - Verificación: repetir la misma cola produce un único resultado final por Lead.
- [ ] 4.4 Probar timeouts, reintentos acotados, errores WebDriver y liberación de recursos en lectura, edición, guardado y verificación.
  - Verificación: no quedan threads, servidores, procesos ni navegadores simulados abiertos.
- [ ] 4.5 Probar concurrencia: dos solicitudes de ejecución, acceso simultáneo a resultados y rechazo de runners incompatibles.
  - Verificación: exactamente un proceso permitido y archivos JSON siempre válidos.
- [ ] 4.6 Ejecutar mutation testing selectivo sobre composición, loaders, deduplicación, conflicto, persistencia y métricas; añadir casos para mutantes sobrevivientes relevantes.
  - Verificación: publicar mutation score y justificación de equivalentes; no debilitar asserts.

## 5. Seguridad y privacidad

- [ ] 5.1 Probar token ausente/incorrecto, endpoint desconocido, métodos no permitidos, path traversal, symlinks/reparse points y rutas fuera de allowlist.
  - Verificación: todas las solicitudes son rechazadas sin efectos laterales.
- [ ] 5.2 Probar payloads vacíos, malformados, excesivos y con contenido de inyección para argumentos de subprocess.
  - Verificación: el proceso permitido recibe una lista fija de argumentos y nunca una cadena evaluada por shell.
- [ ] 5.3 Introducir canarios sintéticos en comentarios, PII, credenciales, cookies y 2FA; escanear consola, logs, errores, resultados y reportes.
  - Verificación: cero canarios en canales prohibidos; cada fuga hace fallar la suite.
- [ ] 5.4 Auditar `.gitignore`, archivos rastreados y artefactos generados para impedir publicación de configuración, perfiles, colas, snapshots, logs y capturas reales.
  - Verificación: `git check-ignore` para cada categoría y escaneo del índice de Git.
- [ ] 5.5 Verificar que las suites automáticas bloquean dominios Salesforce y cualquier escritura real por defecto.
  - Verificación: una URL Salesforce inyectada causa fallo preventivo antes de abrir red o navegador.

## 6. CI y matriz de compatibilidad

- [ ] 6.1 Actualizar CI para instalar dependencias fijadas y ejecutar compile, lint, suites no destructivas, cobertura y OpenSpec.
  - Verificación: workflow válido y corrida completa en una rama/PR.
- [ ] 6.2 Añadir Python 3.12 como gate y Python 3.14 como job informativo inicialmente, conservando sus resultados visibles.
  - Verificación: una incompatibilidad simulada en 3.14 no oculta el resultado y 3.12 sigue siendo obligatorio.
- [ ] 6.3 Publicar artefactos de cobertura y reporte de tests sanitizados, con retención limitada y sin archivos operativos.
  - Verificación: descargar los artefactos de CI y ejecutar el escaneo de privacidad.
- [ ] 6.4 Activar umbrales de 85%/75% global y 90%/80% crítico después de cerrar brechas justificadas.
  - Verificación: bajar cobertura deliberadamente hace fallar CI.

## 7. Trazabilidad e informe

- [ ] 7.1 Inventariar requisitos activos y riesgos; asignar IDs estables y construir la matriz requisito-riesgo-prueba-evidencia.
  - Verificación: cero requisitos críticos sin caso o justificación explícita.
- [ ] 7.2 Registrar comandos, entorno, resultados y evidencia de cada gate sin contar omitidos como aprobados.
  - Verificación: una ejecución omitida aparece como `omitida` con causa y riesgo residual.
- [ ] 7.3 Clasificar hallazgos por severidad y abrir tareas o cambios separados para defectos funcionales confirmados.
  - Verificación: cada hallazgo tiene evidencia, impacto, decisión y test de regresión cuando corresponda.
- [ ] 7.4 Generar informe provisional automático con estado `no lista` mientras falten gates críticos o E2E obligatorio.
  - Verificación: el informe no puede declarar `lista` con una condición bloqueante inyectada.

## 8. Validación Salesforce supervisada

- [ ] 8.1 Resolver con el usuario sandbox/producción, política de capturas, versión Python soportada, allowlist local, máximo de Leads y restauración.
  - Verificación: decisiones registradas y confirmadas antes de ejecutar cualquier E2E real.
- [ ] 8.2 Implementar el guard de doble habilitación para E2E real y demostrar que la suite estándar nunca navega a Salesforce.
  - Verificación: sin flags y confirmación, el E2E termina sin acceso ni escritura.
- [ ] 8.3 Ejecutar smoke supervisado de Edge persistente, autenticación manual, lectura de bandeja y lectura de un Lead sin escritura.
  - Verificación: conteos y resultado sanitizados comparados visualmente.
- [ ] 8.4 Con autorización explícita separada, ejecutar un guardado mínimo y comprobar relectura, resultado, snapshot, métricas e importación UI.
  - Verificación: igualdad tras reabrir y evidencia sanitizada.
- [ ] 8.5 Con autorización explícita separada, ejecutar un duplicado y un conflicto controlado demostrando ausencia de escritura indebida.
  - Verificación: estados `duplicado`/`conflicto`, editor o Guardar no invocados.
- [ ] 8.6 Ejecutar interrupción y reanudación controladas; restaurar cualquier valor temporal que no deba conservarse.
  - Verificación: sin doble escritura y relectura del valor restaurado.
- [ ] 8.7 Revisar y sanear consola, logs, resultados y capturas locales de la corrida real.
  - Verificación: cero datos sensibles en evidencia versionada o compartida.

## 9. Cierre

- [ ] 9.1 Ejecutar todos los gates automáticos, `openspec validate --changes` y revisión de diferencias.
  - Verificación: todos los comandos obligatorios devuelven código 0.
- [ ] 9.2 Emitir dictamen `lista`, `lista con riesgos aceptados` o `no lista`, incluyendo omitidos y riesgos residuales.
  - Verificación: el dictamen satisface mecánicamente el criterio de liberación del spec.
- [ ] 9.3 Sincronizar specs, archivar el cambio aprobado y ejecutar `graphify update .`.
  - Verificación: OpenSpec y Graphify válidos y actualizados.
- [ ] 9.4 Presentar `git status` y solicitar autorización antes de commit o push.
  - Verificación: ninguna acción Git externa se realiza sin confirmación.
