# Diseño: laboratorio-agent-browser-hang

## Context

El motor `agent_browser` del laboratorio delega en un daemon
(`agent-browser`, puerto propio ~9333) que el 17/11 colgó una corrida real
de 43 leads tras 9 `apto`. No hay timeout por lead ni heartbeat: el worker
quedó vivo 70 min bloqueando la UI. El motor `selenium` funciona y es el
recomendado hasta resolver esto.

## Goals / Non-Goals

**Goals:**
- Ninguna corrida puede quedar colgada indefinidamente.
- El operador ve progreso real y puede detectar un worker sin avance.
- El flag de corrida se recupera solo si el worker muere.
- Diagnóstico concreto del punto del hang.

**Non-Goals:**
- No se mejora el motor `selenium` (ya estable).
- No se agrega UI nueva de monitoreo en tiempo real (basta staleness del
  estado).
- No se cambia la semántica de `prueba`/`real` ni la documentación.

## Decisions

1. **Timeout por lead con presupuesto por etapa**, no un solo timeout
   global: cada sub-llamada al daemon (nav/leer/documentar/enviar) recibe
   su límite; el lead entero también tiene techo. Alternativa: timeout
   global de corrida — rechazada, un lead no puede cortar el lote.
2. **Cancelación real al cortar**: al vencer el timeout, se aborta la
   operación del daemon (cerrar sesión/pestaña del engine) para no dejar
   un llamado zombie que luego confunda al siguiente lead.
3. **Heartbeat = escritura incremental del resultado por lead** ya
   existente + un `updated_at`/archivo de progreso si el runner no escribe
   al final. Preferido sobre thread extra de progreso.
4. **Flag autoliberable**: el estado de corrida se deriva del proceso vivo
   + actividad reciente, no solo del flag — un flag sin proceso y sin
   heartbeat se considera obsoleto.
5. **Diagnóstico con sonda mínima**: script que ejercita cada llamada del
   engine con timeout, antes de tocar código productivo.

## Risks / Trade-offs

- [Timeout corta una escritura que sí llegó a Salesforce] → el lead queda
  `error` y NO se reenvía WhatsApp (fail-safe, como ya hace el flujo de
  documentación); se verifica a mano.
- [El daemon ignora el abort] → además del timeout lógico, el engine se
  cierra/reinicia para el siguiente lead.
- [Sobre-ingeniería para un motor quizá retirado] → el watchdog es genérico
  (sirve también al motor selenium); si el diagnóstico confirma que
  `agent_browser` no tiene arreglo barato, la decisión puede ser retirarlo
  en vez de arreglarlo.

## Migration Plan

Aditivo: campos nuevos en el resultado por lead y límites internos.
Rollback = revert; el motor selenium sigue siendo el default operativo.
