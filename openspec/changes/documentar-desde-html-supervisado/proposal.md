# Propuesta: documentar intentos en Salesforce desde el HTML, con supervisión

## Problema

`documentador_predictivo.html` ya contiene todo lo necesario para documentar cada
Lead: el Lead ID, los intentos parseados de `HISTORY_TEL` y el texto listo para
pegar en `Otra información`. Hoy el operador hace a mano, por cada Lead (57 en la
BD actual): abrir el Lead, bajar hasta `Otra información`, leer el último `N INT`,
ajustar el número en el HTML, copiar, editar el campo y pegar.

El runner `run_comment_assisted.py` (cambio `escritura-asistida-salesforce`) ya
abre el Lead, encuentra el campo, lee el historial y calcula el próximo INT, pero
su contrato acepta **un solo intento**, sin número, tipeado como ruta de archivo.
No sirve para consumir lo que genera el HTML.

## Objetivo

Que el bot tome la cola de Leads pendientes directamente desde el HTML y, por cada
Lead, ejecute de forma automática los pasos 1 a 4 y se detenga en el 5:

```text
1) abrir el Lead en Salesforce
2) bajar hasta "Otra información" y leer el último N INT real
3) preparar el texto: historial + intentos renumerados desde SF en líneas siguientes
4) cargarlo en el editor de "Otra información" (sin guardar)
5) detenerse: el operador revisa y pulsa Guardar o Cancelar a mano
```

## Decisiones confirmadas

| Tema | Decisión |
|---|---|
| Fuente de los intentos | El HTML exporta una cola local (JSON en `automation_salesforce/queues/`) con Lead ID e intentos de los Leads **no marcados como documentados** |
| Contenido exportado | Solo Lead ID, resultado, fecha, hora y call ID por intento. Sin nombre, teléfono ni número INT |
| Numeración | **Salesforce manda.** El bot lee el último `N INT` del campo real y numera desde ahí; el campo "Último N° en SF" del HTML deja de ser necesario para el bot |
| Portapapeles | No se usa. `next_attempt_number()` ya hace lo mismo que "Leer N° del portapapeles" leyendo el DOM |
| Formato de cada intento | Idéntico al que hoy genera el HTML: `N INT<TAB>resultado<TAB>fecha<TAB>hora<TAB>callId`, una línea por intento |
| Separación del historial | El primer intento nuevo va en la línea inmediatamente siguiente al historial, sin línea vacía (convención observada en los registros reales) |
| Escritura en el editor | Por JavaScript sobre el `textarea` (preserva tabuladores). `send_keys` de un TAB movería el foco y rompería el texto |
| Guardar | Nunca automático. El runner se detiene y espera Enter; el operador decide |
| Ritmo | Un Lead por vez, con pausa obligatoria entre Leads. Primera prueba: 1 Lead; luego lote controlado |
| Autenticación | Login y 2FA manuales, perfil Edge dedicado |
| Privacidad | Consola y logs: Lead ID enmascarado, conteos e INT. Nunca el texto del comentario ni datos del cliente |

## No objetivos

- Pulsar Guardar, Cancelar, cerrar, reasignar, convertir o cambiar estado.
- Automatizar credenciales o 2FA.
- Marcar Leads como documentados en el HTML de forma automática (se evalúa en un
  cambio posterior con el archivo de resultados que este runner genera).
- Leer el portapapeles del sistema.
- Enviar datos fuera de la PC.

## Resultado esperado

El operador exporta la cola desde el HTML, ejecuta el runner, se autentica y, Lead
por Lead, ve el editor de `Otra información` ya cargado con el historial intacto y
los intentos nuevos correctamente numerados. Decide Guardar o Cancelar, presiona
Enter y el bot pasa al siguiente. Al terminar queda un archivo local de resultados
por Lead (preparado / omitido / error) sin datos de clientes.
