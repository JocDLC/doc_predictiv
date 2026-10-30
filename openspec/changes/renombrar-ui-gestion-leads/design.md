## Context

La UI es un único archivo `documentador_predictivo.html` (~3800 líneas): un `<style>`, el markup de las vistas (Home, Preparar, Documentar, Monitor, Distribuir) y un único `<script>`. Los tests de UI extraen el script con la regex `/<script>([\s\S]*)<\/script>/` y lo ejecutan en Node `vm` con stubs de DOM. Por eso dependen de los IDs y del JS, no del CSS. El monitor corre ciclos en segundo plano mientras la página está abierta, y el usuario pidió explícitamente que la visual nueva no agregue carga de CPU.

## Goals / Non-Goals

**Goals:**
- Nombre "Automatización Gestión de Leads" en `<title>` y `<h1>`; marca "RENAULT GROUP · GBS REC".
- Base clara con fondo `#f6f7f9`, tarjetas blancas y acento `#486581` en reposo. Tras probarla, el usuario pidió recuperar el header azul-violeta y los colores originales del Monitor, y usar azul intenso `#1d4ed8` al pasar el mouse por las tarjetas.
- Cambios concentrados en el `<style>`, salvo los mínimos del markup del header y de Home.

**Non-Goals:**
- Renombrar archivos, carpetas, ZIP, `INICIAR.bat` o scripts Python (queda pendiente en MEMORY.md).
- Layout con sidebar (pendiente: se hace después de documentar todo).
- Cualquier mención de IA.
- Cambios en el JS, endpoints o comportamiento.

## Decisions

1. **Solo CSS + markup mínimo.** Se redefinen las variables `:root` (`--accent`, `--bg`, `--border`, radios, sombras) y se ajustan los selectores existentes. Alternativa descartada: reescribir el layout, porque tiene más riesgo con los tests y está fuera de alcance.
2. **Números y colores de las tarjetas.** Se mantienen números e IDs. En reposo son claras; hover y foco de teclado aplican fondo `#1d4ed8` con texto e iconos blancos, sin desplazamiento. El foco conserva contorno visible.
3. **Header.** Se restaura el degradado `#1d4ed8` a `#6d28d9`, con marca, logo y textos blancos.
4. **Rendimiento.** Fuentes del sistema (`Segoe UI`). Sin `backdrop-filter`, `blur`, `@import` ni animaciones infinitas. Las transiciones existentes se limitan a elementos interactivos (`.module-card`, `.btn`). Se mantiene la animación puntual `monitorFlash` (4 s, una vez). Se agrega un bloque `@media (prefers-reduced-motion: reduce)` que anula transiciones y animaciones.
5. **Un único `<script>`.** No se agrega ningún `<script>` adicional: la regex greedy de los tests capturaría HTML intermedio.
6. **Monitor.** Se restauran los fondos y bordes originales: verde activo, ámbar en espera, rojo requiere atención y gris apagado. También los avisos, switch verde y tabla. Las variables originales se aplican dentro de `#viewMonitor` para conservar el resto de la muestra. Se mantiene el espacio y legibilidad mejorados.
7. **Sin librerías nuevas.** El usuario pospuso shadcn. Este ajuste se limita a CSS, mantiene fuentes del sistema y no agrega trabajo de JavaScript.

## Risks / Trade-offs

- [El JS genera HTML con clases (`badge`, `st-*`, `monitor-table`) cuyo contraste cambia] → Se conservan las clases y solo se ajustan colores manteniendo el contraste. Se verifica visualmente cada vista.
- [Un selector con colores hardcodeados (`#12304a`, `#0a4f93`) queda desalineado con la paleta nueva] → Se reemplazan por variables (`--heading`, `--accent-hover`).
- [El dist queda desincronizado] → Una tarea copia el HTML a `dist/DocumentadorPredictivo/app/` y verifica con `diff`.

## Migration Plan

Copiar el HTML al dist y refrescar la página (F5); no hace falta reiniciar el servidor. Rollback: `git checkout` del HTML y volver a copiarlo.

## Open Questions

- Pendientes posteriores (registrados en MEMORY.md): renombre completo del proyecto (archivos, carpetas, ZIP, scripts) y migración a layout con sidebar.
