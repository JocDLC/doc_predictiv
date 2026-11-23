# lectura-reporte-tolerante-stale Specification

## Purpose
La lectura del reporte de Salesforce extrae los datos dentro del navegador
(materializados en la misma evaluación JS) y tolera handles que mueren, en
lugar de propagar `StaleElementReferenceException` y abortar el ciclo.

## ADDED Requirements

### Requirement: REQ-1030: Extracción materializada en el navegador

La lectura de cada fila del reporte SHALL obtener texto/ids/atributos
dentro de la misma evaluación JS que la localiza, devolviendo valores
primitivos — no `WebElement` que se lean en llamadas posteriores.

#### Scenario: Fila leída sin exportar handles
- **WHEN** el scan localiza una fila del reporte
- **THEN** nombre, id del lead y campos usados llegan como
  strings/números ya materializados de una sola evaluación

### Requirement: REQ-1031: Reintento acotado del scan

Un scan que falla por elemento/frame muerto SHALL reintentarse un número
acotado de veces antes de declarar `bandeja_error`, registrando el intento.

#### Scenario: Stale transitorio se recupera solo
- **WHEN** la primera lectura falla por una fila stale y la segunda
  evaluación encuentra el DOM estable
- **THEN** el scan devuelve las filas sin `bandeja_error`

#### Scenario: Stale persistente marca error con contexto
- **WHEN** todos los reintentos fallan por stale
- **THEN** el resultado marca `bandeja_error` indicando bandeja, excepción
  y cantidad de intentos — sin lanzar la excepción al ciclo

### Requirement: REQ-1032: Tolerancia extendida en helpers de frames

`execute_in_any_frame` y `find_*_in_any_frame` SHALL tratar una excepción
de frame/documento muerto (stale, frame detached) en un frame como "seguir
con el siguiente", nunca como abort total.

#### Scenario: Un frame muere al serializar
- **WHEN** el primer frame lanza `StaleElementReferenceException` al
  devolver el resultado y un frame posterior tiene el elemento
- **THEN** el helper devuelve el resultado del frame posterior
