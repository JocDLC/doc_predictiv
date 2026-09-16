# Diseño técnico: escritura asistida y supervisada

## Flujo controlado

```text
Login/2FA manual
  -> Lead ID ingresado localmente
  -> leer Otra información
  -> calcular próximo INT
  -> cuerpo de intento local
  -> vista previa de métricas (sin contenido)
  -> activar solo el editor de Otra información
  -> completar: historial + línea vacía + "N INT " + cuerpo
  -> detenerse: usuario revisa y pulsa Guardar o Cancelar manualmente
```

## Componentes

- `comment_writer.py`: construye el valor final, localiza el editor del campo y
  escribe únicamente en el `textarea` o control editable asociado.
- `run_comment_assisted.py`: punto de entrada visible, solicita Lead ID y la ruta
  de un borrador local UTF-8, coordina la lectura y mantiene la pausa final.
- `tests/test_comment_writer.py`: pruebas sin navegador para construcción del
  valor, validación de borrador y selección segura del control editable.

El cuerpo se lee desde un archivo local indicado por el usuario para evitar
exponerlo en consola o logs. Debe ser texto plano de una sola entrada y no puede
comenzar con `N INT`; el runner añade el valor calculado por Lead.

## Contrato de composición

Dados `historial`, `next_int` y `cuerpo`:

```text
si historial está vacío: "{next_int} INT {cuerpo}"
si historial existe:    "{historial}\n\n{next_int} INT {cuerpo}"
```

El historial se conserva íntegramente; no se reemplaza ni normaliza. La función
rechaza cuerpos vacíos, múltiples entradas o prefijos `N INT` para no duplicar ni
alterar la numeración.

## Seguridad y control humano

- No hay llamadas a `click` sobre un botón cuyo texto/atributo represente Guardar,
  Cancelar, cierre, reasignación o cambio de estado.
- Solo se habilita el control de edición asociado de forma inequívoca a la etiqueta
  `Otra información`; si hay ambigüedad, se toma captura local y no se escribe.
- Antes de editar, el runner imprime Lead ID local, longitud previa, siguiente INT
  y longitud final; nunca imprime el cuerpo ni el historial.
- Después de completar el control, el runner espera una confirmación local y no
  emite ninguna acción adicional. El usuario decide manualmente Guardar o Cancelar.
- Los logs usan ID enmascarado y métricas; las capturas quedan locales e ignoradas
  por Git.

## Errores y recuperación

| Situación | Acción |
|---|---|
| Campo o editor no visible | Captura local, log sin contenido y no escribir |
| Borrador inválido | Informar antes de abrir edición |
| DOM Lightning cambia durante la edición | No reintentar una escritura; captura y finaliza |
| Usuario cancela o guarda manualmente | El runner no infiere el resultado ni lo registra como éxito de guardado |

## Evolución posterior

Una integración de cola desde `documentador_predictivo.html` exportará Lead ID y
cuerpo de intento. El runner conservará este contrato y seguirá calculando el
prefijo `N INT` en tiempo de ejecución por Lead.
