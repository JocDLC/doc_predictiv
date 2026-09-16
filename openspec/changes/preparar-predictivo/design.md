# Diseño técnico

## Arquitectura general

Se mantiene **un único archivo** `documentador_predictivo.html` con tres "vistas"
controladas por JavaScript (sin router, solo `show/hide` de secciones):

```
+--------------------------------------------------------------+
| HEADER corporativo (logo Renault Group + título)             |
+--------------------------------------------------------------+
| Vista HOME (selector)                                        |
|   [Tarjeta 1: Preparar archivo para predictivo]              |
|   [Tarjeta 2: Documentar predictivo]                         |
+--------------------------------------------------------------+
| Vista PREPARAR (nueva)      | Vista DOCUMENTAR (existente)   |
+--------------------------------------------------------------+
```

- La vista DOCUMENTAR es el contenido actual (dropzone + toolbar + lista).
  No se modifica su lógica; solo se envuelve en un contenedor `#viewDocumentar`.
- Botón "Inicio" persistente para volver al selector.
- La recuperación automática de sesión (`dp_activeSession`) debe llevar al usuario
  directamente a la vista DOCUMENTAR si había un CSV en curso.

## Módulo PREPARAR: pipeline de datos

```
archivo entrada (CSV o XLSX)
  └─ readInputFile()        CSV: detección de separador y encoding
                            XLSX: SheetJS minificado incrustado (sin CDN)
  └─ mapeo de columnas      autodetección por nombre de cabecera +
                            selectores manuales para: Nombre, Apellido,
                            Lead ID, E-mail, Vehículo, Concesionario, Teléfono(s)
  └─ input "Identificador de campaña" → TIPOID en todas las filas
         validar: solo letras ASCII y números, sin espacios, acentos ni símbolos
  └─ normalizePhone(raw, country)
         quitar todo lo no numérico → tomar los ÚLTIMOS 10 dígitos →
         anteponer prefijo país (AR 91549 | CO 957 | MX 9352)
         < 10 dígitos → null (excluido)
  └─ mapRowToTemplate(row)  convención actual: SEXO=vehículo, ZONA=concesionario,
                            DIRECCION=email, TIPOID=identificador de campaña
                            Solo TEL1 (si hay fijo y celular, preferir celular)
  └─ validateBatch(rows)
         ID obligatorio y único | TEL1 obligatorio y único
         excluidos con motivo + referencia al lead que quedó (duplicados)
  └─ buildWolkvoxCSV(rows)  separador ';', sin comillas, CRLF, UTF-8 con BOM
  └─ descarga Blob + a[download]  → predictivo_{PAIS}_{YYYYMMDD}.csv
  └─ reporte de excluidos: tabla en pantalla + CSV descargable
```

### Template Wolkvox (fuente de verdad)

Cabecera exacta (51 columnas, `PREDICTIVOS/PREPARAR_PREDICTIVO/Template predictivo Wolkvox.csv`):

```
NOMBRE;APELLIDO;TIPOID;ID;EDAD;SEXO;PAIS;DEPARTAMENTO;CIUDAD;ZONA;DIRECCION;
OPT1..OPT12;TEL1..TEL10;OTROSTEL;EMAIL;RECALL-INFO;AGENTE;RESULTADOREG;
FECHAFINREG;LLAMADAS;IDCALL;COD01;DESC1;COD02;DESC2;COMENTARIOSACUMULADOS;
DATE_RECALL;COUNT_RECALL;TEL_RECALL;LAST_DIAL_TEL;HISTORY_TEL
```

Obligatorios sin duplicados: `ID` (lead ID de Salesforce) y `TEL1` (con prefijo país).

## Branding

- Favicon Renault incrustado como data-URI SVG y rombo Renault incrustado como
  SVG inline en el header (blanco sobre `--accent #0b5cab`).
- No se referencian los archivos de `PREDICTIVOS/ICONOS/` por ruta: el HTML
  sigue siendo portable como archivo único.

## Decisiones

| Decisión | Elección | Motivo |
|---|---|---|
| ¿Un HTML o varios? | Uno solo | Portabilidad (se comparte por Teams/SharePoint como archivo único) |
| ¿Framework? | Vanilla JS | Coherente con lo existente; sin dependencias |
| ¿Librería XLSX? | Sí: la entrada puede ser XLSX → incrustar SheetJS minificado en el HTML (sin CDN, versión publicada hace más de 7 días) | Restricción sin red |
| Mapeo de columnas de entrada | Autodetección + selección manual (los exports traen muchas columnas y las cabeceras pueden variar) | Robustez ante cambios del export |
| Columnas "reutilizadas" del template | Mantener convención actual (SEXO=vehículo, ZONA=concesionario, DIRECCION=email, TIPOID=identificador de campaña) | Compatibilidad con el módulo Documentar y procesos existentes |
| Formato de salida Wolkvox | `;`, sin comillas automáticas, CRLF, UTF-8 BOM | Réplica del archivo validado por Wolkvox (`plantilla leads arg.csv`) |
| Estado del módulo 1 | Sin persistencia (transformación pura) | No hay progreso que guardar |

## Testing

Sin framework de test instalado, la verificación es por script Python de
contraste (mismo enfoque usado hasta ahora):

1. **Golden file**: correr el módulo con la BD de ejemplo (P1) y comparar
   contra un archivo preparado a mano validado por el usuario.
2. **Casos de teléfono** (tabla en tasks.md): entrada → salida esperada.
3. **Duplicados**: dataset sintético con ID y TEL1 repetidos → verificar exclusión y reporte.
4. **Round-trip**: el CSV generado debe poder abrirse en el módulo DOCUMENTAR
   sin errores una vez que Wolkvox lo devuelva (mismas columnas).
5. Validación HTML: `python -c "from html.parser import ..."` como smoke test.
