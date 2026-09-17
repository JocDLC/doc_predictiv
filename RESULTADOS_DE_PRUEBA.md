# Resultados de prueba

Este documento registra validaciones operativas de la aplicación para medir el impacto de las mejoras y comparar resultados entre versiones.

## Prueba inicial — Documentación de leads

| Métrica | Resultado |
|---|---:|
| Registros documentados | 10 leads |
| Tiempo total | 3 min 50 s |
| Tiempo promedio por lead | 23 s |
| Rango de referencia operativo | 23–30 s por lead |
| Fuente de prueba | Predictivo 14 al 16 Argentina — José Manuel de la Colina |
| Método | Aplicación local, apertura manual de Salesforce y copiado/pegado del texto generado |
| Resultado | Flujo validado correctamente |

### Observaciones

- El principal tiempo de espera observado corresponde a la carga de Salesforce.
- La aplicación elimina la concatenación manual y prepara el texto de documentación para copiar y pegar.
- La métrica es una referencia obtenida en esta prueba; puede variar según el rendimiento de Salesforce, la red y las particularidades de cada lead.
- Pendiente de evaluación: apertura de leads por lotes para reducir el tiempo de espera percibido.

## Piloto Selenium — Lectura de Salesforce

| Validación | Resultado |
|---|---|
| Navegador | Microsoft Edge con perfil dedicado |
| Autenticación | Login y 2FA manuales validados |
| Reporte Salesforce | 29 filas visibles y 10 Leads con propietario exacto `AR_LEAD_QUALIF`, confirmados manualmente |
| Campo individual | "Otra información" localizado en un único Lead sin activar edición |
| Cálculo de intentos | Historial con `1 INT`: próximo intento calculado correctamente como `2` |
| Pruebas automáticas | 43/43 tests unitarios correctos |
| Escrituras o guardados | Ninguno |
| Datos en documentación | No se registraron Lead IDs, comentarios, teléfonos, emails, credenciales ni códigos 2FA |

### Observaciones de seguridad

- El lector de reporte se limita a las filas actualmente visibles; no recorre la grilla virtualizada.
- Logs, capturas, perfiles, configuración local y colas operativas están excluidos de Git.
- El piloto queda cerrado como validación de lectura. Cualquier preparación o escritura asistida requiere un cambio OpenSpec separado y aprobación explícita.

## UI local de Leads QUALIF

| Validación | Resultado |
|---|---|
| Filtro de propietario | Validado manualmente: la UI vuelve a mostrar los Leads `AR_LEAD_QUALIF`. |
| Modo de lectura normal | Lee solo la grilla visible; el recorrido con scroll queda limitado a `--completo`. |
| Pruebas automáticas | 56/56 tests unitarios y Ruff correctos. |
| Privacidad | El HTML local de prueba permanece ignorado por Git. |
