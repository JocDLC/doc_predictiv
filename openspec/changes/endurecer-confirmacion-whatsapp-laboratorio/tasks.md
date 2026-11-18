## 1. Preparación y baseline

- [x] Leer PLAN.md, design.md, specs y diagnóstico; iniciar Gantt `wo-laboratorio-whatsapp-age`, conservar cambios sin commit.
- [x] Respaldar journal con SQLite backup y colas/resultados; verificar versión/config sin imprimir secretos; comprobar que no hay runner/Monitor activo.
- [x] Reproducir baseline y sondas; corregir format-check en los archivos indicados sin cambios funcionales ajenos; verificar harness/CI y separar Node de OpenSpec del usado por agent-browser.
- [x] Convertir los seis fallos reproducidos en regresiones dentro de los tests existentes; documentar FAIL antes del fix.
- [x] Investigar discrepancia del hash protegido de `.archify` que bloquea business-contracts; resolver por el flujo autorizado o declarar el gate pendiente, sin cambiar expectativas para aprobar.

## 2. Identidad, historial y reservas

- [x] Exigir origen/objeto/ID válido en lectura, antes de guardar, después de reload y justo antes del clic; probar IDs 15/18 y navegación concurrente.
- [x] Leer valores por estructura DOM sin filtrar texto legítimo; probar campo vacío/ausente, label repetido y edición concurrente preservando historial.
- [x] Implementar reserva transaccional por origen/lead/canal entre campañas; migrar bloqueos históricos conservadoramente sin borrar operaciones.
- [x] Probar reservas con dos conexiones, cambio de campaña/motor y crashes en cada checkpoint; reanudar con cero clics duplicados.

## 3. Observación y confirmación

- [x] Definir contexto y evidencia estructurada en contratos del laboratorio; clasificador puro que rechace negativos, genéricos, previos y ajenos.
- [x] Implementar baseline y observer previo al clic con buffer acotado; cubrir nodo insertado/modificado/removido, shadow roots y frames soportados.
- [x] Proteger clic con identidad y actionability; controlar deadline incluyendo CLI, pérdida de target y desconexión; no usar fallback a pestaña ajena.
- [x] Integrar evidencia con runner y commit terminal; conservar no_confirmado/indeterminado y distinguir aceptación de entrega.
- [x] Adaptar SeleniumLabBrowser al contrato del laboratorio sin cambiar silenciosamente el Monitor; probar cierre seguro del toast y limpieza de observadores.

## 4. Fixture adversarial y regresiones

- [x] Crear/reutilizar fixture local controlada con contadores independientes de escritura, clic y efecto; perfil/puerto exclusivos.
- [ ] 4.2 Ejecutar matriz A01–A24 de PLAN.md con ambos motores; tres repeticiones para casos temporales, sin skips críticos.
- [x] Verificar tabs de usuario intactas, sesiones propias liberadas y ausencia de tráfico/mutaciones Salesforce durante tests locales.
- [x] Integrar tests determinísticos en CI con Node fijado; separar smoke Windows/Edge/CLI y reportar versiones/capas.

## 5. Persistencia, auditoría y comparación

- [x] Conservar JSONL/métricas por run y alias activo compatible; probar iniciar otra corrida/reanudar/reiniciar sin borrar resultados históricos.
- [x] Extender APIs existentes con run_id validado y doc/send/evidence; probar token, traversal y aislamiento entre corridas.
- [ ] 5.3 Mostrar selección de corrida y ejes separados en UI; no representar intento calculado como documentación escrita.
- [x] Agregar auditoría de solo lectura de línea reservada (exactamente una ocurrencia), guardando resultados por motor sin alterar envíos.
- [x] Calcular métricas pareadas por modo/estado; separar cold start, descartados y button_check; registrar orden A/B y B/A.

## 6. Puertas de validación y piloto

- [ ] 6.1 Ejecutar suite completa, format-check, lint, compile, checks JS, contratos de negocio y OpenSpec; adjuntar evidencia y diferenciar fallos previos de regresiones.
- [ ] 6.2 Ejecutar auditoría real de solo lectura sobre muestra de operaciones confirmadas/no_confirmadas, con identidad y línea del journal, sin repetir envíos.
- [ ] 6.3 Preparar lista explícita de leads de prueba nuevos, sin reservas, con grupos distintos por motor; si no existe selección adecuada, dejar piloto bloqueado con motivo.
- [ ] 6.4 Tras puertas aprobadas, ejecutar un lead por motor, capturar evidencia real redactada, auditar documentación con ambos; detener ampliación ante ambigüedad.
- [ ] 6.5 Solo si el lote inicial es íntegro, ampliar a tres leads por motor; informar aceptación/no confirmado/entrega desconocida y métricas, sin declarar fiabilidad general.

## 7. Entrega

- [ ] 7.1 Actualizar CHANGELOG, MEMORY (path correcto y límites), VERSIONS si corresponde; excluir debug/fixtures/datos reales del paquete.
- [ ] 7.2 Generar y verificar ZIP con `python packaging/build_zip.py --sync-dist`, conservar config/journal/perfil y comprobar código servido.
- [ ] 7.3 Actualizar Graphify y Gantt; entregar reporte PASS/FAIL/pendiente y decisión por operación, manteniendo bloqueados los casos ambiguos.
- [ ] 7.4 Sincronizar/archivar OpenSpec solo con implementación y gates completos; solicitar aprobación para commit/push según AGENTS.md.
