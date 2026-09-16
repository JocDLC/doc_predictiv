# Tareas: automatizar-lectura-salesforce

> Objetivo del cambio: piloto **solo lectura**. No introducir escritura, clicks de
> edición, guardado, cierre de Leads ni automatización de 2FA. Cada agente debe
> marcar una tarea inmediatamente al completarla y ejecutar la verificación
> indicada antes de continuar.

## Fase 0 — Seguridad y preflight

- [x] 0.1 Revisar `proposal.md`, `design.md` y `specs/lectura-salesforce/spec.md`.
      Confirmado: el alcance se limita a lectura.
- [x] 0.2 Crear `automation_salesforce/` y actualizar `.gitignore` para excluir:
      `automation_salesforce/logs/`, `automation_salesforce/screenshots/`,
      `automation_salesforce/profiles/`, `automation_salesforce/config.json`,
      `automation_salesforce/queues/` y cualquier `.csv`/`.json` operativo.
- [x] 0.3 Crear `requirements.txt` con `selenium==4.48.0`; instalar mediante
      `python -m pip install -r automation_salesforce/requirements.txt`.
      Verificado: Selenium 4.48.0.
- [x] 0.4 Crear `config.example.json` sin credenciales con: `browser`,
      `profile_directory`, `report_url`, `timeouts` y `screenshot_directory`.
      Crear `config.json` local a partir del ejemplo; nunca commitearlo.
- [x] 0.5 Definir `README.md` de operación: alcance solo lectura, login/2FA
      manual, no compartir perfiles, ubicación de logs y forma de detener con
      Ctrl+C.

## Fase 1 — Fábrica de navegador y login manual

- [x] 1.1 Crear `browser_factory.py` con `detect_browser(browser_name)`:
      - Edge: `%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe`,
        `%ProgramFiles%\Microsoft\Edge\Application\msedge.exe`,
        `%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe`.
      - Chrome: rutas equivalentes de `Google\Chrome\Application\chrome.exe`.
      - `auto`: Edge primero, Chrome como fallback.
      - En el piloto, valor predeterminado `edge`. Verificado Edge en esta PC.
- [x] 1.2 Crear `create_driver(config)` que abre el navegador **visible**, con
      ventana maximizada, `--user-data-dir` del perfil dedicado y WebDriver
      gestionado por Selenium Manager. No usar el perfil habitual del navegador.
      Smoke test: Edge abrió y cerró correctamente con el perfil dedicado.
- [x] 1.3 Crear `run_read_only.py` que abre la URL raíz de Salesforce y muestra
      instrucciones de login/2FA manual. Esperar que el usuario confirme por
      terminal cuando ya vea Salesforce autenticado.
- [x] 1.4 Validar autenticación comprobando URL/contenido de Lightning; si sigue
      en login, informar y finalizar. No intentar leer MFA, passwords o cookies.
      Validado manualmente el 2026-09-09.
- [x] 1.5 Prueba manual: abrir Edge, completar 2FA, cerrar runner y repetir.
      Confirmar que el perfil dedicado conserva sesión solo si Salesforce lo permite.
      Login y 2FA manuales confirmados exitosamente el 2026-09-09.

## Fase 2 — Infraestructura de auditoría y selectores

- [x] 2.1 Crear `local_audit.py`: `mask_lead_id()`, `create_logger()` y
      `capture_failure()`. El log almacena timestamp, etapa, resultado y Lead ID
      enmascarado; nunca contenido de comentario, teléfono o email.
- [x] 2.2 Usar constantes de timeout desde `config.json` con `WebDriverWait`;
      no se utiliza `sleep()` como mecanismo principal de sincronización.
- [~] 2.3 Crear helper `wait_for_lightning_ready(driver)`. Implementado con
      `document.readyState`; falta validarlo contra elementos visibles reales de
      Salesforce Lightning durante la prueba manual de reporte.
- [~] 2.4 `TimeoutException` ya toma captura y deja log en el runner inicial.
      Falta extender el manejo a `NoSuchElementException` y otros errores en el
      próximo runner de escaneo.
- [~] 2.5 Test unitario de `mask_lead_id()` creado y aprobado (2/2). Falta crear
      los tests del parser `N INT` cuando se implemente `comment_reader.py`.

## Fase 3 — Lectura de bandeja de Leads

- [x] 3.1 Crear `report_reader.py`; la URL de reporte está en `config.json`,
      nunca hardcodeada en código.
- [x] 3.1a Crear tests unitarios sin navegador para encabezados normalizados,
      propietario `AR_LEAD_QUALIF`, celdas `td`/`gridcell` y extracción segura
      de Lead ID; incluir una prueba de que el resumen muestra el ID solamente
      en la consola local, según la decisión operativa aprobada.
- [x] 3.2 Implementar `find_report_table()` y `read_visible_unassigned_leads()`
      para navegar/esperar la grilla. El diagnóstico real confirmó que el reporte
      está en el primer `iframe`; el lector ya cambia a ese contexto y selecciona
      la grilla de mayor cantidad de filas. Validado contra la sesión real.
- [x] 3.2a Crear `run_report_read_only.py`: login y 2FA manuales, navegación al
      reporte, espera Lightning, lectura visible, salida local con IDs y
      captura local ante `TimeoutException`. Ejecutado contra Salesforce; los
      intentos de diagnóstico agotaron el timeout sin modificar datos.
- [x] 3.3 Selectores genéricos implementados por encabezado visible/ARIA para
      "Propietario del candidato", su alias Lightning "Propietario" y "Fecha de
      creación", no por índice fijo. Validado contra el DOM real de Lightning.
      El timeout registra diagnóstico estructural de Shadow DOM
      abierto y frames, sin guardar valores de filas ni encabezados. Se agregó un
      fallback exacto por celda/línea para grillas que no exponen encabezados y
      se excluyen filas DOM ocultas mediante `is_displayed()`. Tras detectar 9
      falsos positivos, se priorizan filas HTML reales y se descartan
      contenedores ARIA con filas descendientes.
- [x] 3.4 El lector se limita explícitamente a filas visibles y devuelve el
      conteo; no implementa scroll ni lectura de filas virtualizadas.
- [~] 3.5 Filtrar coincidencia exacta `AR_LEAD_QUALIF` y crear reporte local
      mínimo: Lead ID, fecha de creación, posición en grilla y estado
      `SIN_GESTION`. El filtro exacto y la salida local de IDs están
      implementados y validados. La extracción no fija un prefijo de ID: usa el
      objeto Salesforce configurable, enlaces o atributos de la fila y elimina
      duplicados por ID. Se genera una instantánea JSON local con los cuatro
      campos; falta verificar manualmente fecha, posición y contenido del archivo
      contra la bandeja real.
- [x] 3.6 Prueba manual: se compararon 29 filas visibles y 10 Leads detectados
      con la pantalla de Salesforce; el usuario confirmó que el resultado es
      correcto. No se hicieron cambios en la bandeja.

## Fase 4 — Lectura de Otra información y próximo INT

- [x] 4.1 Crear `comment_reader.py` con `find_other_information(driver)` que
      abre un Lead ID ingresado localmente por terminal y busca la etiqueta
      accesible "Otra información" sin activar edición. Implementado mediante
      inspección de DOM y Shadow DOM abierto, sin `click` ni escritura.
- [x] 4.2 Crear `next_attempt_number(comment)` con regex que reconoce
      `N INT` al inicio de línea, calcula el máximo y retorna máximo + 1; sin
      coincidencias retorna 1.
- [x] 4.3 Tests unitarios mínimos:
      - vacío → 1;
      - `1 INT ...` → 2;
      - `1 INT`, `2 INT`, `3 INT` → 4;
      - texto no relacionado + `12 INT` → 13;
      - números repetidos/desordenados → máximo + 1.
- [x] 4.4 Ejecutar sobre un único Lead elegido por el usuario. Mostrar solamente:
      Lead ID en consola local, campo encontrado sí/no, cantidad de caracteres y
      próximo INT. No imprimir el comentario completo. Runner implementado;
      validado manualmente el 2026-09-09: 35 caracteres y próximo INT 2.
- [x] 4.5 Prueba manual: comparar el próximo INT informado con el contenido
      visible de "Otra información" en Salesforce. Confirmado contra un campo
      existente con un único intento `1 INT`; el lector calculó correctamente 2.

## Fase 5 — Verificación y cierre del piloto

- [x] 5.1 Ejecutar tests unitarios Python. Verificado el 2026-09-12: 43/43 OK.
- [x] 5.2 Ejecutar prueba de bandeja y prueba de un Lead sin modificar Salesforce.
      Validaciones manuales registradas: reporte con 29 filas visibles/10 Leads y
      "Otra información" en un Lead, con próximo INT calculado como 2.
- [x] 5.3 Revisar `logs/` y `screenshots/`: confirmar que no contienen comentarios
      completos, teléfonos, emails, cookies, contraseñas o códigos 2FA. Revisión
      realizada el 2026-09-12 sin coincidencias de datos sensibles en logs.
- [x] 5.4 Registrar resultados y tiempos en `RESULTADOS_DE_PRUEBA.md` sin incluir
      datos de clientes. Actualizado el 2026-09-12.
- [x] 5.5 Ejecutar `graphify update .` y `openspec validate --changes` si la CLI
      está disponible. Graphify actualizado el 2026-09-12; `openspec` no está
      disponible en el PATH de la sesión del agente, por lo que quedó pendiente
      validarlo desde una terminal con la CLI instalada.
- [~] 5.6 Revisar `git status`, confirmar que datos operativos están ignorados y
      solicitar confirmación explícita antes de commit/push. Verificado:
      `config.json`, logs y colas están ignorados. No hay autorización de
      commit/push todavía.

## Fase 6 — Propuesta posterior, no ejecutar en este cambio

- [ ] 6.1 Solo tras aprobación del usuario: nueva propuesta `escritura-asistida-
      salesforce`, donde Selenium agrega intentos al final de "Otra información"
      con una línea vacía y no presiona Guardar.
- [ ] 6.2 Nueva propuesta de integración: HTML exporta una cola local de
      documentación y el runner Selenium la consume desde archivo seleccionado.
- [ ] 6.3 Tras disponibilidad de API: nueva propuesta para reemplazar el adaptador
      Selenium por integración API manteniendo la cola y la UI.
