# Propuesta: Automatizar lectura de Salesforce con Selenium

## Problema

La documentación de intentos se prepara en `documentador_predictivo.html`, pero
se aplica manualmente dentro de Salesforce. No existe API disponible. También se
necesita identificar desde la bandeja de Leads aquellos registros nuevos que no
han sido tomados por un asesor.

## Objetivo del piloto

Construir un proyecto Python **separado** de la app HTML que use Selenium para:

1. Detectar Microsoft Edge y, en una fase posterior, Google Chrome.
2. Abrir Salesforce mediante un perfil dedicado y permitir login/2FA manual.
3. Navegar al reporte de Leads proporcionado por el usuario.
4. Identificar los Leads sin gestión cuyo campo "Propietario del candidato" sea
   exactamente `AR_LEAD_QUALIF`.
5. Abrir un Lead por ID y localizar/leer el campo "Otra información".
6. Detectar el mayor número existente con el patrón `N INT` para calcular desde
   qué intento continuará una documentación futura.
7. Crear logs y capturas de diagnóstico únicamente en la PC local.

## URL de bandeja a validar

```text
https://renaultarca.lightning.force.com/lightning/r/Report/00O67000006cstjEAA/view?queryScope=userFolders
```

La bandeja está ordenada en forma descendente por "Fecha de creación". Un Lead
nuevo sin gestión se identifica cuando "Propietario del candidato" es
`AR_LEAD_QUALIF`.

## Decisiones confirmadas

| Tema | Decisión |
|---|---|
| Navegador inicial | Microsoft Edge |
| Navegador posterior | Chrome, después de validar Edge |
| Autenticación | Login y 2FA manual del analista; nunca guardar contraseñas/códigos |
| Perfil | Perfil de navegador dedicado para automatización, separado del uso diario |
| Sandbox | No disponible |
| Campo de comentarios | `Otra información` |
| Escritura inicial | Prohibida: el piloto es exclusivamente de lectura |
| Historial de comentarios | Una futura escritura agregará contenido al final dejando una línea en blanco |
| Fuente de leads a tratar | Reporte de Salesforce; propiedad `AR_LEAD_QUALIF` |
| Integración inicial con HTML | Ninguna: proyectos separados para el PoC |

## No objetivos del piloto

- Escribir, guardar, cerrar, reasignar o modificar Leads/actividades en Salesforce.
- Evitar o automatizar 2FA/SSO.
- Automatización masiva sin supervisión humana.
- Integrar aún Selenium dentro de `documentador_predictivo.html`.
- Reemplazar la futura API de Salesforce.

## Resultado esperado

El piloto entrega un reporte local verificable que permite responder:

```text
- ¿Edge puede entrar a Salesforce con un perfil dedicado y 2FA manual?
- ¿Se puede leer la bandeja y detectar AR_LEAD_QUALIF de forma confiable?
- ¿Se puede leer “Otra información” de un Lead sin modificarlo?
- ¿Se puede calcular correctamente el próximo número de INT?
```

Solo si las cuatro respuestas son afirmativas se propondrá una segunda fase de
escritura asistida, sin guardado automático.
