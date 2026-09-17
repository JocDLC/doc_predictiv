# Propuesta: UI local de Leads sin gestión

## Problema

El reporte de Salesforce contiene los Leads nuevos o pendientes de gestión, pero
la validación actual solo genera una instantánea local técnica. El equipo necesita
una interfaz de prueba que muestre, agrupada por secciones, únicamente las filas
visibles cuyo "Propietario del candidato" sea exactamente `AR_LEAD_QUALIF`.

## Objetivo

Crear una interfaz HTML local y temporal que, después de una lectura Selenium
visible y autenticada manualmente del reporte configurado, muestre en una tabla
solo las columnas efectivamente visibles de los Leads pendientes de gestión, sin
abrir registros individuales ni modificar Salesforce.

La fuente inicial es el reporte:

```text
https://renaultarca.lightning.force.com/lightning/r/Report/00O67000006cstjEAA/view?queryScope=userFolders
```

## Información presentada por Lead

### Información cliente

- Nombre y apellido, mostrados juntos.
- Lead ID.
- Correo electrónico.
- Teléfono.
- Tipo de cliente, por ejemplo `PERSONAL` o `PROFESIONAL`.

### Información general

- Tipo de interés.
- País.
- Código fiscal/DNI.
- Fecha y hora de creación.
- Estado de candidato.
- Concesionario de interés.
- Propietario del candidato.

### Síntesis

- Vehículo de interés.
- Número de matrícula.
- Descripción: texto operativo visible para la red de concesionarios antes de la
  conversión a HOT.

### Cualificación

- Cualificación.
- Sub-Cualificación.

### Información sobre la fuente de lead

- Campaña.
- Contexto.
- Origen de creación.
- Origen.
- Origen del candidato.
- Nombre del formulario lead.
- Otra información: historial de intentos de contacto e interacciones.

Los valores y las opciones disponibles de Estado de candidato, Vehículo de
interés, Cualificación, Sub-Cualificación y cualquier otro campo se extraen
dinámicamente de las filas visibles del reporte. No se fijan listados de valores
en el código.

## Decisiones confirmadas

| Tema | Decisión |
|---|---|
| Fuente | Reporte Salesforce configurado, no la URL de grupo/cola |
| Filtro | Coincidencia exacta de propietario: `AR_LEAD_QUALIF` |
| Alcance de lectura | Solo filas visibles, sin scroll automatizado de grillas virtualizadas |
| UI | HTML local generado en la PC, sin backend ni servicios externos |
| Datos personales | Visibles solo en la UI local autorizada; prohibidos en consola, logs, capturas y Git |
| Columnas no disponibles | No se muestran; la UI refleja únicamente columnas existentes en la bandeja |
| Acceso al Lead | No se abre ningún Lead individualmente en este cambio |
| Autenticación | Login y 2FA manuales con perfil dedicado |

## No objetivos

- Editar, guardar, reasignar, cerrar o alterar Leads.
- Automatizar credenciales o 2FA.
- Leer filas no cargadas mediante scroll masivo o paginación automática.
- Copiar información de clientes a logs, repositorio o servicios externos.
- Consultar campos de Lead que no estén expuestos por el reporte durante esta
  primera UI.

## Resultado esperado

Tras completar el login manual, el usuario ve una pantalla local con el conteo y
las tarjetas de los Leads visibles filtrados. Puede buscar por Lead ID, revisar
las opciones distintas visibles para Estado de candidato y Vehículo de interés, y
abrir un Lead individual en Salesforce sin modificarlo.
