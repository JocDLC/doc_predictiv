# Tasks: laboratorio-agent-browser-hang

## 1. Diagnóstico del hang

- [ ] 1.1 Reproducir el hang con una sonda mínima que llame al daemon `agent-browser` lead por lead (sin el runner completo) y registrar en qué llamada se congela (handshake CDP / navegación / selector / lectura).
- [ ] 1.2 Documentar la causa raíz y la decisión: arreglar el motor o retirarlo.

## 2. Timeout por lead

- [ ] 2.1 `laboratory_browser.py`: presupuesto de tiempo por etapa (nav/leer/documentar/enviar) con el engine `agent_browser`.
- [ ] 2.2 Al vencer: abortar la operación del daemon (cerrar sesión/pestaña del engine), marcar el lead `error` con motivo `timeout:<etapa>` y continuar con el siguiente.
- [ ] 2.3 Techo por lead (suma de etapas) además del timeout individual.
- [ ] 2.4 Tests del timeout con el daemon mockeado que no responde.

## 3. Progreso y flag autoliberable

- [ ] 3.1 Runner: escribir el resultado parcial por lead (o un archivo de progreso con `updated_at`) al terminar cada lead.
- [ ] 3.2 Estado de corrida = proceso vivo + actividad reciente; un flag sin proceso ni heartbeat se considera obsoleto y permite nueva corrida.
- [ ] 3.3 UI/estado: exponer "sin progreso" cuando la corrida está activa pero sin heartbeat reciente.
- [ ] 3.4 Tests de liberación del flag y del indicador de staleness.

## 4. Cierre

- [ ] 4.1 Suite completa + lint + format-check + compileall.
- [ ] 4.2 Verificación in situ: corrida corta en `prueba` con `agent_browser` (o la decisión de retirarlo).
- [ ] 4.3 CHANGELOG `[Sin publicar]`, `graphify update .`, log en Gantt, `openspec validate --changes`.
