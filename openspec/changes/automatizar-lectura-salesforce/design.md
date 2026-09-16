# Diseño técnico: piloto de lectura Salesforce

## Separación de responsabilidades

```text
┌───────────────────────────────────┐
│ documentador_predictivo.html       │
│ - Procesa export Wolkvox           │
│ - Genera texto de intentos         │
│ - Usuario copia/pega hoy           │
└───────────────────────────────────┘
                 │
                 │ No hay integración en el piloto
                 ▼
┌───────────────────────────────────┐
│ automation_salesforce/             │
│ - Script Python + Selenium         │
│ - Navega Salesforce en Edge        │
│ - Lee reporte y “Otra información” │
│ - Registra evidencias locales      │
└───────────────────────────────────┘
                 │
                 ▼
┌───────────────────────────────────┐
│ Salesforce Lightning               │
│ - Login/2FA manual                 │
│ - Solo lectura en este piloto      │
└───────────────────────────────────┘
```

La app HTML no puede lanzar ni controlar Selenium: los navegadores bloquean que
una página local ejecute procesos Python por seguridad. La primera integración
viable será posterior y desacoplada: el HTML exportará una cola de trabajo local
(CSV/JSON) y el runner Python la seleccionará desde disco.

## Estructura propuesta

```text
automation_salesforce/
├── README.md                 # operación local y límites de seguridad
├── requirements.txt          # selenium==4.48.0
├── config.example.json       # configuración sin credenciales ni datos reales
├── run_read_only.py          # punto de entrada interactivo
├── browser_factory.py        # detección/lanzamiento Edge y Chrome
├── salesforce_pages.py       # navegación y selectores de Lightning
├── report_reader.py          # lectura del reporte y filtro AR_LEAD_QUALIF
├── comment_reader.py         # lectura de “Otra información” y próximo INT
├── local_audit.py            # logs y capturas locales
└── tests/
    ├── test_comment_parser.py
    └── test_phone_or_report_data.py  # solo datos sintéticos; nunca datos reales
```

`logs/`, `screenshots/`, perfiles de navegador, colas con Lead IDs y archivos de
datos deben estar excluidos de Git mediante `.gitignore`.

## Perfil de navegador y 2FA

Ruta sugerida, configurable localmente:

```text
%LOCALAPPDATA%\RenaultPredictivo\edge-profile
```

El runner abre Edge con `--user-data-dir` en dicha ruta. En la primera ejecución:

1. El script abre el navegador en modo visible.
2. El analista inicia sesión y completa 2FA desde su teléfono.
3. El script espera explícitamente una señal del usuario (`Enter`) y comprueba
   que la página Salesforce está disponible.
4. La cookie de sesión, si Salesforce la mantiene, queda en el perfil local y
   protegida por Windows; nunca se registra en logs o Git.

Cada analista debe utilizar su propio perfil. No usar el perfil de Edge habitual
ni copiar perfiles/cookies entre usuarios.

## Detección de navegador

`browser_factory.py` debe buscar ejecutables conocidos en este orden:

1. Edge: rutas de `Program Files (x86)`, `Program Files` y `%LOCALAPPDATA%`.
2. Chrome: mismas ubicaciones equivalentes.

La configuración permite `browser: "edge" | "chrome" | "auto"`. Durante el
piloto, `edge` es el valor por defecto. `auto` elige Edge y luego Chrome si Edge
no está disponible. El ejecutable y versión se escriben en el log local.

## Lectura del reporte de Leads

Flujo:

```text
Abrir URL de reporte
  → esperar Lightning y grilla de resultados
  → identificar columnas por encabezado visible, no por índice fijo
  → localizar “Propietario del candidato” y “Fecha de creación”
  → leer filas visibles
  → filtrar valor exacto: AR_LEAD_QUALIF
  → guardar Lead ID + fecha + estado localmente
```

El nombre API del objeto de registro se configura mediante
`record_object_api_name` (`Lead` por defecto). La extracción valida la ruta del
objeto y el formato Salesforce de 15/18 caracteres, pero no fija prefijos como
`00Q`; esto permite reutilizar el lector si otra implementación usa un objeto
estándar o personalizado diferente.

El runner crea una instantánea JSON por ejecución en el directorio local
configurable `queue_directory` (`queues` por defecto). Cada registro contiene
solamente `lead_id`, `created_at`, `grid_position` y `status`; el directorio está
ignorado por Git y no se transmite a ningún servicio externo.

Salesforce Lightning puede virtualizar filas. La primera versión debe trabajar
solo con las filas visibles y reportar claramente esa limitación. Una fase
posterior añadirá scroll incremental, deduplicación por Lead ID y final de grilla.

## Lectura de “Otra información” y próximo INT

Para un Lead ID seleccionado por el usuario:

```text
Abrir /{LeadID}
  → esperar carga
  → buscar etiqueta accesible “Otra información”
  → leer el texto sin activar edición
  → regex: /(^|\n)\s*(\d+)\s+INT\b/gi
  → máximo N encontrado + 1 = próximo INT
```

Ejemplo:

```text
1 INT Cliente no contesta ...
2 INT Envío WhatsApp ...
3 INT Llamada no conecta ...

Resultado: próximo INT = 4
```

Si no hay coincidencias, el resultado es `1`. Si el campo no se encuentra, el
script toma una captura local, registra error y no intenta ninguna acción.

## Guardrails de seguridad

- Ejecución visible: nunca headless para el piloto.
- Ningún método Selenium de escritura (`send_keys`, click de editar o Guardar)
  dentro de los módulos del piloto.
- Un solo Lead leído por ejecución para la prueba inicial.
- Timeout explícito y captura de pantalla ante errores.
- Consola local con Lead ID completo para validación operativa. Los logs, si
  incluyen un Lead ID, deben enmascararlo; nunca deben incluir comentarios
  completos, teléfonos, emails, contraseñas, cookies o códigos 2FA.
- Pausa y confirmación del usuario antes de cada navegación a Salesforce.

## Evolución posterior, no implementada

1. HTML exporta `cola_documentacion.csv`: Lead ID, texto de intentos, motivo
   homologado opcional.
2. Selenium abre cada Lead y prepara “Otra información” sin guardar.
3. Usuario revisa y guarda.
4. Luego de pruebas graduadas, guardar/verificar con auditoría local.
5. Cuando exista API Salesforce, sustituir el adaptador Selenium por un cliente
   API sin alterar la interfaz ni la cola de trabajo.
