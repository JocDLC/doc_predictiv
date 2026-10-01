## Why

El diagrama de arquitectura actual explica componentes y conexiones técnicas, pero no permite que una persona no técnica entienda con rapidez qué funciones de negocio ofrece el sistema ni bajo qué reglas operan. Los requisitos OpenSpec ya contienen esa semántica, por lo que pueden convertirse en una vista ejecutiva trazable sin reemplazar ni simplificar artificialmente el gráfico técnico existente.

## What Changes

- Crear un segundo gráfico HTML independiente, orientado a macrofunciones de negocio y accesible desde una URL distinta.
- Conservar sin modificaciones el gráfico técnico `documentador-architecture.html`.
- Representar el recorrido de negocio desde la carga de la base hasta los resultados, productividad y correcciones, evitando nombres de archivos o funciones Python como etiquetas principales.
- Mostrar al seleccionar cada macrofunción un contrato comprensible: propósito, entradas, resultados, reglas, fallos esperados y referencias OpenSpec.
- Permitir desplegar trazabilidad técnica opcional hacia requisitos, escenarios, implementación y pruebas, sin recargar la vista ejecutiva.
- Verificar de forma determinística que cada macrofunción y contrato procede de requisitos OpenSpec existentes y que los enlaces internos son válidos.

## Capabilities

### New Capabilities

- `business-contract-graph`: visualización independiente y trazable de las macrofunciones del Documentador Predictivo mediante contratos de negocio derivados de OpenSpec.

### Modified Capabilities

Ninguna. El gráfico técnico y los requisitos funcionales existentes permanecen sin cambios.

## Impact

- Nuevo artefacto HTML junto al diagrama Archify existente, con nombre y URL independientes.
- Fuente estructurada versionada para mantener macrofunciones, relaciones y contratos sin editar manualmente un HTML monolítico.
- Lectura de requisitos activos en `openspec/specs/` y `openspec/changes/*/specs/`; los requisitos archivados solo se usarán cuando sigan vigentes en specs principales.
- Nuevas verificaciones de esquema, cobertura de requisitos, enlaces, accesibilidad y smoke visual local.
- Sin cambios en la aplicación operativa, Salesforce, datos de clientes, APIs o comportamiento de automatización.
