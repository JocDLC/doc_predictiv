## Context

La aplicación combina un HTML local, archivos JSON operativos, un servidor HTTP en `127.0.0.1`, procesos Python, Selenium, Edge y Salesforce Lightning. La suite actual tiene 118 pruebas y Ruff en verde, pero está concentrada en unidades con objetos simulados; no mide cobertura y deja sin comprobar varios límites entre componentes. Además, los cambios funcionales principales aún contienen tareas manuales pendientes.

La auditoría debe ser repetible por una persona distinta de quien implementó la aplicación, no debe usar datos reales en fixtures o artefactos versionados y debe impedir que una prueba automática escriba en Salesforce accidentalmente.

## Goals / Non-Goals

**Goals:**

- Medir cobertura de líneas y ramas, no solo cantidad de casos.
- Probar contratos completos entre UI, archivos, servidor y runners con datos sintéticos.
- Validar robustez, recuperación, idempotencia, seguridad y privacidad.
- Añadir un protocolo E2E supervisado para navegador y Salesforce reales.
- Relacionar cada requisito y riesgo crítico con evidencia verificable.
- Integrar los controles no destructivos en CI y mantener los E2E reales fuera de CI.

**Non-Goals:**

- Automatizar credenciales, login o 2FA.
- Ejecutar escrituras reales sin confirmación explícita y Leads autorizados.
- Cambiar reglas de negocio o ampliar los botones que Selenium puede pulsar.
- Usar datos de clientes en tests, fixtures, capturas, logs o reportes versionados.
- Corregir silenciosamente defectos hallados; cada corrección funcional requerirá causa raíz, regresión y trazabilidad.

## Decisions

### 1. Pirámide de pruebas con gates separados

El arnés tendrá suites `unit`, `contract`, `integration-local`, `security-privacy`, `browser-local` y `e2e-supervised`. Las cinco primeras serán determinísticas y no tocarán Salesforce; `e2e-supervised` requerirá variables de habilitación, confirmación humana y un manifiesto local de Leads autorizados.

Se descarta una única suite monolítica porque ocultaría qué tipo de evidencia falló y aumentaría el riesgo de ejecutar escrituras reales desde CI.

### 2. Cobertura de líneas y ramas con umbrales explícitos

Se añadirá `coverage.py` con branch coverage. El gate objetivo será al menos 85% de líneas y 75% de ramas en el paquete, y al menos 90% de líneas y 80% de ramas para componentes críticos de escritura, correcciones, servidor local, persistencia y privacidad. Antes de activar el gate se registrará la línea base; no se excluirán archivos críticos para alcanzar el porcentaje.

Se descarta usar el conteo de tests como métrica principal porque varios casos pueden recorrer la misma ruta y dejar ramas de fallo sin probar.

### 3. Fixtures sintéticos y adaptadores observables

Los contratos JSON y fragmentos de DOM se representarán con fixtures ficticios, pequeños y revisables. Los tests observarán llamadas, archivos y estados públicos; evitarán afirmar detalles internos salvo para controles de seguridad esenciales. Los temporales se crearán fuera de carpetas operativas reales.

Cuando una dependencia externa impida una prueba determinística, se introducirá el seam mínimo y explícito; no se hará un refactor amplio durante la auditoría.

### 4. Navegador local real sin Salesforce

El HTML principal y el servidor local se probarán con un navegador real en modo controlado, usando datos sintéticos y un runner inocuo. Esta capa comprobará selección, exportación, importación de resultados, snapshots, métricas, token y disparo del proceso sin navegar a Salesforce.

Se prefiere este enfoque frente a probar únicamente funciones JavaScript aisladas porque los fallos relevantes incluyen DOM, eventos, permisos de archivo y HTTP.

### 5. Seguridad mediante invariantes y listas permitidas

Las pruebas comprobarán que el servidor solo escucha en loopback, exige token, limita rutas y comandos, rechaza payloads inválidos o excesivos y no permite path traversal. También comprobarán que logs, excepciones, resultados y artefactos versionables no contienen texto de comentarios, PII, credenciales, cookies o 2FA.

El escaneo usará canarios sintéticos únicos para detectar fugas sin introducir datos reales.

### 6. E2E real como protocolo con doble control

Las pruebas contra Salesforce se dividirán en lectura, escritura mínima, conflicto y recuperación. La escritura exigirá: entorno y sesión visibles, lista local de IDs autorizados, copia previa del campo, confirmación textual del operador, máximo de registros por corrida y evidencia de relectura. Si existe sandbox se usará; en producción se limitará a Leads explícitamente autorizados y se definirá restauración antes de ejecutar.

El protocolo generará solo evidencia sanitizada. Capturas con datos visibles permanecerán locales y deberán revisarse o eliminarse según la política acordada.

### 7. Trazabilidad y criterio de liberación

Una matriz versionada relacionará `requirement_id`, riesgo, nivel, caso, comando, entorno, resultado y evidencia. El informe final no podrá declarar “listo” si existe un requisito crítico sin prueba, un test omitido sin justificación o un riesgo alto abierto.

### 8. Compatibilidad y CI

Python 3.12 será el entorno obligatorio porque es el configurado en CI. Python 3.14 se ejecutará inicialmente como compatibilidad informativa y se convertirá en gate solo después de resolver diferencias. CI ejecutará lint, compilación, suites no destructivas, cobertura y validación OpenSpec; nunca accederá a Salesforce ni a secretos productivos.

## Risks / Trade-offs

- **Los selectores reales de Lightning cambian con el tiempo** → mantener fixtures de variantes conocidas y reservar el E2E supervisado para confirmar el DOM vigente.
- **Un porcentaje alto de cobertura puede incentivar tests superficiales** → combinar cobertura con branch coverage, mutation testing selectivo y trazabilidad por riesgo.
- **Los tests de navegador pueden ser inestables** → usar esperas por condiciones, datos sintéticos, timeouts acotados y diagnóstico sanitizado; separar flakiness de defectos funcionales.
- **Una prueba real podría modificar un Lead incorrecto** → doble habilitación, allowlist local, máximo de registros y confirmación antes de cada clase de escritura.
- **La auditoría puede revelar defectos fuera del alcance** → documentar severidad y abrir cambios correctivos separados en vez de mezclar correcciones con el arnés.
- **Nuevas dependencias aumentan mantenimiento** → fijar versiones y limitarse a herramientas necesarias para cobertura, generación de casos y mutación selectiva.

## Migration Plan

1. Registrar línea base sin cambiar comportamiento ni umbrales.
2. Añadir dependencias y comandos del arnés con versiones fijadas.
3. Incorporar suites determinísticas por capas hasta cumplir los gates.
4. Activar los gates no destructivos en CI.
5. Ejecutar smoke local de navegador sin Salesforce.
6. Ejecutar el protocolo E2E supervisado únicamente tras aprobación separada.
7. Publicar el informe de auditoría y decidir liberación o cambios correctivos.

Rollback: retirar los nuevos jobs y dependencias de desarrollo mantiene intacta la aplicación productiva. Los fixtures y reportes no participan en tiempo de ejecución.

## Open Questions

- ¿Existe un sandbox de Salesforce o las pruebas de escritura deberán usar producción con Leads autorizados?
- ¿Qué política de conservación se aplicará a capturas locales que puedan contener datos visibles?
- ¿Python 3.14 debe convertirse en versión soportada o solo conservarse como comprobación informativa?

