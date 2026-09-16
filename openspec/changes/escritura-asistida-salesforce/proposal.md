# Propuesta: Escritura asistida de Otra información en Salesforce

## Problema

El piloto de solo lectura ya confirmó que se puede obtener el texto existente de
`Otra información` y calcular el próximo número `N INT` por Lead. La carga sigue
siendo manual y el número generado por la aplicación HTML puede no coincidir con
el historial específico del registro.

## Objetivo

Crear una prueba asistida, visible y de un único Lead que:

1. Mantenga login y 2FA exclusivamente manuales.
2. Lea el valor actual de `Otra información` y calcule el próximo `N INT`.
3. Reciba localmente el cuerpo del nuevo intento, sin un prefijo `N INT`.
4. Abra el editor del campo, agregue una línea en blanco y el texto con el número
   calculado.
5. Se detenga sin pulsar `Guardar`; la revisión, guardado o cancelación quedan
   bajo control explícito del usuario en Salesforce.

## Decisiones confirmadas

| Tema | Decisión |
|---|---|
| Alcance | Un único Lead por ejecución durante la prueba |
| Edición | Abrir mediante lápiz o doble clic, según el control Lightning disponible |
| Numeración | El runner calcula `máximo N INT + 1` por Lead |
| Texto de entrada | Cuerpo local sin `N INT`; el runner agrega el prefijo correcto |
| Guardado | Nunca automatizado; el usuario pulsa `Guardar` o `Cancelar` manualmente |
| Evidencia | Logs y capturas locales, sin contenido completo ni PII en logs |
| Autenticación | Login y 2FA manuales con perfil dedicado |

## No objetivos

- Pulsar `Guardar`, `Cancelar`, cerrar, reasignar o alterar otros campos.
- Procesar varios Leads, usar scroll masivo o ejecutar sin supervisión.
- Registrar el cuerpo del comentario, teléfonos, emails, cookies o credenciales.
- Integrar todavía la app HTML con Selenium; la exportación de cola será otro cambio.

## Resultado esperado de la prueba

Con un Lead que ya contiene `1 INT ...`, al ingresar un cuerpo de intento válido,
el editor visible debe mostrar una nueva entrada que comience por `2 INT `. El
usuario verifica el borrador y decide manualmente si lo guarda o lo cancela.
