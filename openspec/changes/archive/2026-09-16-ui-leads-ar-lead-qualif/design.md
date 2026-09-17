# Diseño técnico: UI local de Leads sin gestión

## Flujo

```text
Login y 2FA manuales
  -> Selenium abre el reporte configurado
  -> espera la grilla Lightning
  -> lee únicamente filas visibles
  -> identifica encabezados por texto/ARIA
  -> filtra Propietario del candidato = AR_LEAD_QUALIF
  -> crea instantánea local temporal con los campos disponibles
  -> genera HTML local con tarjetas por Lead
  -> abre la UI en el navegador
```

No hay escritura en Salesforce. La única acción opcional desde la UI será abrir
la URL de vista de un Lead individual.

## Componentes

- `report_reader.py`: se amplía para extraer valores de filas mediante encabezados
  normalizados, no por índices fijos. Recibe un mapa de nombres de campos y
  alias configurables.
- `local_report.py`: persiste la instantánea de ejecución en un directorio local
  ignorado por Git. Debido a que contendrá datos personales, no registra su ruta
  ni los valores en logs.
- `leads_ui.py`: genera una página HTML local desde la instantánea, aplica escape
  HTML a todos los valores y abre el archivo local en el navegador.
- `run_leads_ui.py`: coordina autenticación manual, lectura, creación de UI y
  manejo seguro de errores.
- `tests/`: pruebas sintéticas de mapeo de columnas, filtrado, escape HTML,
  agrupación visual y ausencia de datos personales en logs.

## Mapa de campos

La configuración tendrá `lead_list_fields` con etiqueta principal y alias. El
lector busca la primera coincidencia de cada campo entre los encabezados visibles.
Los valores se extraen solo si existe una columna correspondiente.

| Sección | Campo local | Etiquetas previstas |
|---|---|---|
| Cliente | nombre | Nombre, First Name |
| Cliente | apellido | Apellido, Last Name |
| Cliente | lead_id | Lead ID, Id. del candidato |
| Cliente | email | Correo electrónico, Email |
| Cliente | telefono | Teléfono, Phone, Celular |
| Cliente | tipo_cliente | Tipo de cliente |
| General | tipo_interes | Tipo de interés |
| General | pais | País, Pais |
| General | codigo_fiscal | Código fiscal, Codigo fiscal, DNI |
| General | fecha_creacion | Fecha de creación, Created Date |
| General | estado_candidato | Estado de candidato, Estado |
| General | concesionario_interes | Concesionario de interés, Concesionario |
| General | propietario_candidato | Propietario del candidato, Propietario |
| Síntesis | vehiculo_interes | Vehículo de interés, Vehiculo de interes |
| Síntesis | numero_matricula | Número de matrícula, Numero de matricula |
| Síntesis | descripcion | Descripción, Descripcion |
| Cualificación | cualificacion | Cualificación, Cualificacion |
| Cualificación | sub_cualificacion | Sub-Cualificación, Sub-Cualificacion |
| Fuente | campana | Campaña, Campana |
| Fuente | contexto | Contexto |
| Fuente | origen_creacion | Origen de creación, Origen de creacion |
| Fuente | origen | Origen |
| Fuente | origen_candidato | Origen del candidato |
| Fuente | nombre_formulario_lead | Nombre del formulario lead |
| Fuente | otra_informacion | Otra información, Otra informacion |

El valor Fecha de creación puede venir como una celda única. La UI lo separa
visualmente en fecha y hora cuando reconoce ambos componentes; si no, conserva
el texto visible original sin inferir información.

## UI local

La UI será un único HTML generado bajo un directorio ignorado por Git. Tendrá:

- encabezado con fecha local de generación, contador de filas visibles y contador
  de Leads filtrados;
- buscador local por nombre, apellido y Lead ID;
- filtros locales construidos a partir de los valores presentes en las filas
  visibles para Estado de candidato, Vehículo de interés y País;
- tabla local de una fila por Lead, con solo las columnas que realmente aportó
  la bandeja en la lectura actual;
- encabezados basados en las etiquetas configuradas de esas columnas;
- sin marcador para columnas ausentes ni enlaces que abran el detalle del Lead.

Todos los textos de Salesforce se escapan antes de insertarse en HTML. El archivo
queda local y se abre mediante el navegador predeterminado; la lectura de los
Leads seguirá usando el perfil dedicado de Selenium.

## Privacidad y seguridad

- La instantánea y el HTML generado se guardan solo en directorios ignorados por
  Git, por ejemplo `automation_salesforce/ui_output/`.
- Consola y logger muestran solo conteos y Lead IDs enmascarados.
- No se incluyen datos personales en capturas de diagnóstico. Si falla la UI, la
  captura se limita al reporte original ya visible para el usuario.
- La UI no usa JavaScript de terceros, red, analítica ni dependencias CDN.
- Si una fila no permite extraer Lead ID válido, puede visualizarse como dato
  incompleto, pero no tendrá enlace de apertura.

## Verificación manual

1. Ejecutar `run_leads_ui.py` desde PowerShell.
2. Completar login/2FA manualmente.
3. Comparar el contador de la UI con las filas visibles `AR_LEAD_QUALIF` del
   reporte.
4. Comprobar algunos valores visibles contra la misma fila de Salesforce.
5. Abrir un Lead desde la UI y confirmar que solo navega a su vista, sin cambios.
6. Confirmar que archivos locales con datos personales no aparecen en `git status`.
