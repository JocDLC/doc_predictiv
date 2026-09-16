# Piloto de lectura Salesforce

Este módulo usa Selenium para validar acceso de solo lectura a Salesforce.

## Alcance actual

- Detecta Edge y Chrome; Edge es el valor predeterminado.
- Abre un perfil de navegador dedicado.
- Permite login y 2FA manual.
- Comprueba que Salesforce esté accesible después de la autenticación.
- Lee las filas visibles del reporte y filtra el propietario exacto configurado.
- Extrae IDs Salesforce de 15/18 caracteres sin fijar su prefijo; el objeto se
  define con `record_object_api_name` (`Lead` por defecto).

No escribe campos, no guarda, no cierra registros y no automatiza 2FA.

## Primera ejecución

1. Copiar `config.example.json` a `config.json`.
2. Ejecutar `python -m pip install -r requirements.txt`.
3. Ejecutar `python run_read_only.py`.
4. En Edge, iniciar sesión en Salesforce y completar 2FA manualmente.
5. Volver a la terminal y presionar Enter.
6. Confirmar que el resultado indica autenticación correcta.

Usar Ctrl+C para detener. No compartir la carpeta de perfil, `config.json`, logs ni capturas.

## Lectura del reporte

Ejecutar `python run_report_read_only.py`, completar login y 2FA manualmente y
presionar Enter. El runner crea una instantánea JSON local en `queues/` con ID,
fecha de creación, posición visible y estado `SIN_GESTION`. Ese directorio está
ignorado por Git y no debe compartirse fuera del entorno autorizado.

## Lectura de “Otra información”

Ejecutar `python run_comment_read_only.py`, completar login y 2FA manualmente e
ingresar un único Lead ID. El runner abre la página individual del registro, lee
“Otra información” y muestra solo el estado del campo, la cantidad de caracteres
y el próximo `INT`. No imprime el comentario, no activa edición y no guarda
cambios en Salesforce.

## Preparación asistida de Otra información

La preparación asistida trata un único Lead y nunca guarda automáticamente. Crear
primero un archivo UTF-8 dentro de `queues/`, por ejemplo
`queues/borrador.txt`, con **solo el cuerpo** de un nuevo intento. No incluir el
prefijo `N INT`, porque el runner lo calcula según el historial real del Lead.

Ejecutar `python run_comment_assisted.py`, completar login y 2FA manualmente e
ingresar el Lead ID y la ruta del borrador local. El runner muestra únicamente
métricas y exige escribir `PREPARAR` antes de abrir el editor. Después carga el
borrador en “Otra información” y se detiene: el usuario debe revisar y pulsar
**Guardar** o **Cancelar** directamente en Salesforce. El runner no automatiza
ninguno de esos botones.
