---
name: tdd
description: Vía TDD (rojo → verde → refactor) para cambios chicos clasificados TDD por la checklist de la Fase 0.5 de AGENTS.md. Usar cuando el usuario pide un bugfix puntual, un ajuste de regla/validación o un refactor cubierto por tests.
license: MIT
metadata:
  based_on: obra/superpowers skill test-driven-development (MIT) — https://github.com/superpowers
---

# TDD — vía rápida para cambios chicos

Adaptado del skill `test-driven-development` de
[obra/superpowers](https://github.com/superpowers) (licencia MIT) al español
y al stack de este repo (`unittest` + `ruff` + `harness.py`).

## Iron Law

**Ningún código productivo sin un test que falle primero.**

No hay excepciones: ni "es muy simple", ni "lo testeo después", ni "ya lo
probé a mano". Si escribiste código productivo antes del test, borralo y
empezá de nuevo. Un test escrito después no prueba nada: puede pasar sin
importar si el fix funciona.

## Clasificación (Fase 0.5 de AGENTS.md)

Va por TDD solo si TODAS se cumplen:

1. Es un bugfix, un ajuste de regla o validación puntual, o un refactor
   con el comportamiento cubierto por tests.
2. Toca como máximo 3 archivos productivos, en un solo módulo o capa.
3. No agrega endpoints, vistas de UI, formatos de cola/resultado/snapshot
   ni contratos nuevos.
4. No cambia la mecánica de Salesforce (selectores, flujo de pickup o
   reasignación), seguridad ni privacidad.
5. El comportamiento esperado se puede escribir en una sola frase sin
   ambigüedad.
6. Se puede verificar con un test determinístico (sin navegador ni
   Salesforce en vivo).

Si alguna falla → **SDD** (Fases 1–7 de AGENTS.md). El agente propone la
vía y el usuario confirma.

## Ciclo T1–T5

Correr los comandos desde `automation_salesforce/`.

### T1 — Clasificar

Aplicar la checklist, proponer la vía al usuario y esperar su
confirmación. Después `gantt start <id>` (o `add` si la tarea no existe).

### T2 — RED

Escribir el test mínimo que expresa el comportamiento esperado y correr:

```
python harness.py tdd-red <test_id>
```

ej. `python harness.py tdd-red tests.test_queue_loader`. Solo pasa si el
test **falla**. Si el harness avisa que falla por error
(import/nombre/sintaxis) y no por aserción, verificá que el fallo sea por
la funcionalidad faltante antes de seguir.

### T3 — GREEN

Escribir el código mínimo que haga pasar el test y correr:

```
python harness.py tdd-green <test_id>
```

Exige que el test pase, después corre la suite completa (`unit`) y
`ruff check .`. Nada de código extra "por las dudas".

### T4 — REFACTOR

Limpieza opcional (nombres, duplicación), volviendo a correr
`python harness.py tdd-green <test_id>` después de cada toque.

### T5 — Cierre

- Entrada en `CHANGELOG.md` bajo `[Sin publicar]` (`Corregido` o
  `Cambiado`) que nombra el test-regla.
- `gantt log <id> "..."` + `gantt stop <id>`.
- `graphify update .`.
- Pedir confirmación al usuario para commitear.

## Test-regla permanente

El test que prueba el cambio queda como regla permanente. **No se borra
ni se debilita** (ni skips, ni asserts relajados, ni umbrales bajados)
sin autorización explícita del usuario.

## Racionalizaciones frecuentes

| Excusa | Respuesta |
| --- | --- |
| "Es muy simple para testear" | Simple no es excusa: el test toma 2 minutos y fija el comportamiento para siempre. |
| "Lo testeo después" | Un test escrito después puede pasar aunque el fix esté mal. Primero el test que falla. |
| "Ya lo probé a mano" | La prueba manual no sobrevive al próximo refactor; el test sí. |
| "Borrar el código que ya escribí es desperdicio" | El desperdicio es un fix sin regla que lo proteja. Borrá y hacelo bien. |
| "El refactor no cambia comportamiento" | Entonces el test ya existente tiene que seguir verde: corrés `tdd-green` igual. |

## Cuándo escalar a SDD

Si durante el ciclo aparece alcance nuevo (otro módulo, un contrato, una
vista, mecánica de Salesforce), frenar y escalar: `/opsx:propose` con la
metodología SDD (Fases 1–7). No estirar la vía TDD para cubrir una
feature.

## Checklist final

- [ ] Test escrito antes del código y `tdd-red` lo vio fallar por el
      motivo correcto.
- [ ] `tdd-green` OK (test + suite + lint).
- [ ] El test queda en la suite como regla permanente.
- [ ] Entrada en `CHANGELOG.md` `[Sin publicar]` nombrando el test.
- [ ] `log`/`stop` en Gantt + `graphify update .`.
