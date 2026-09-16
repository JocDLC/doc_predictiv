# Propuesta: Módulo "Preparar archivo para predictivo" + selector de inicio

## Contexto

La app `documentador_predictivo.html` hoy cubre solo la mitad del ciclo:

```
[1] BD de leads → (manual, Excel) → archivo Wolkvox → predictivo corre
[2] resultado del predictivo → app actual → documentación en Salesforce
```

El paso [1] se hace hoy a mano con fórmulas de Excel (formateo de teléfonos,
mapeo de columnas al template de Wolkvox). Este cambio lo automatiza y agrega
una pantalla de inicio para elegir entre los dos módulos.

## Objetivos

1. Pantalla de inicio (selector) con dos módulos y branding corporativo Renault:
   - Módulo 1: preparación del archivo para el predictivo (nombre final pendiente de decisión).
   - Módulo 2: "Documentar predictivo" (la app existente, sin cambios funcionales).
2. Módulo 1: subir la BD de entrada → obtener el CSV listo para Wolkvox.
   - Formatea teléfonos según país: MX `9352`, CO `957`, AR `91549` + 10 dígitos.
   - Completa el template oficial de Wolkvox (51 columnas, separador `;`, UTF-8 con BOM, CRLF y sin comillas automáticas).
   - Valida obligatorios y sin duplicados: `ID` (col. D) y `TEL1` (col. X).
   - Genera reporte de registros excluidos/corregidos para revisión.
3. Mantener la restricción de privacidad: procesamiento 100% local en el navegador,
   sin servidores externos, un solo archivo HTML.

## Restricciones

- Sin backend, sin APIs externas, sin dependencias de CDN.
- Todo en un único `documentador_predictivo.html` (o archivos HTML hermanos si
  se decide separar módulos, ver design.md).
- Los datos de clientes nunca salen de la máquina del usuario.
- Íconos corporativos disponibles en `PREDICTIVOS/ICONOS/` (rombo Renault en
  blanco/negro PNG, logo Renault Group blanco/negro, favicon .ico y .svg).
  Deben incrustarse en el HTML como data-URI base64 para conservar el archivo único.

## Preguntas resueltas (respuestas del usuario, 2026-09-02)

| # | Respuesta |
|---|-----------|
| P1 | Entrada CSV **o** XLSX. Trae muchas columnas; se usan: Nombre, Apellido, Lead ID, E-mail, Vehículo, Concesionario. Los nombres exactos de cabecera pueden variar → el módulo debe permitir mapear columnas (autodetección + selección manual). |
| P2 | `TIPOID` = identificador libre de la campaña (responsable / fechas / evento), lo escribe el usuario al preparar. Vehículo, concesionario y email pueden ir en `SEXO`/`ZONA`/`DIRECCION` (convención actual) o en columnas `OPT`. **Decisión: mantener la convención actual** (SEXO=vehículo, ZONA=concesionario, DIRECCION=email) para no romper la lectura ya existente en el módulo Documentar; revisable a futuro. |
| P3 | Normalización: quitar espacios/guiones y todo lo no numérico → tomar los **últimos 10 dígitos** → anteponer el prefijo del país. Menos de 10 dígitos → excluido. |
| P4 | Solo `TEL1`. Si el lead tiene fijo y celular, se carga uno solo (preferir celular). |
| P5 | Excluir + reporte descargable. El reporte debe distinguir el **motivo** (sin ID / ID duplicado / teléfono inválido / teléfono duplicado) e indicar contra qué lead quedó duplicado. |
| P6 | Selector de país **visible**: México `9352`, Colombia `957`, Argentina `91549`. |
| P7 | `predictivo_{PAIS}_{YYYYMMDD}.csv` aprobado. |

| P8 | Nombre definitivo del módulo 1: **"Preparar campaña predictiva"** (confirmado 2026-09-02). |
| P9 | Formato de salida Wolkvox confirmado con archivo aceptado: `;`, UTF-8 BOM, CRLF y sin comillas. `TIPOID` admite solo letras ASCII y números (sin espacios, acentos ni símbolos). TEL1 solo números sin espacios. Mapeo: TIPOID=campaña, SEXO=vehículo, CIUDAD=vacío, ZONA=concesionario, DIRECCION=e-mail. |

## Fuera de alcance (non-goals)

- Integración por API con Wolkvox o Salesforce.
- Subida automática del archivo a Wolkvox.
- Persistencia compartida entre usuarios (cada navegador guarda lo suyo).
