# Tareas: escritura-asistida-salesforce

> Cambio supervisado: el runner puede completar el editor de `Otra información`,
> pero no puede pulsar `Guardar` ni otras acciones de negocio. Cada ejecución
> trata un único Lead y requiere autenticación manual.

## Fase 0 — Preflight y seguridad

- [x] 0.1 Confirmar que el cambio de lectura mantiene Fase 4 validada y que
      `config.json`, perfiles, colas, logs y capturas continúan ignorados por Git.
- [x] 0.1a Completar el harness Python del módulo: `ruff` con versión fijada y
      job de CI que instala dependencias, ejecuta lint y suite de tests.
- [x] 0.2 Definir el contrato del borrador local UTF-8: un solo cuerpo, no vacío,
      sin prefijo `N INT` y sin registrarlo en consola o logs.
- [x] 0.3 Crear pruebas que impidan automatizar `Guardar`, `Cancelar`, cierre,
      reasignación y cambios de estado.

## Fase 1 — Composición y selectores

- [x] 1.1 Crear `comment_writer.py` y tests para conservar el historial y
      agregar el `N INT` calculado en la línea siguiente.
- [x] 1.2 Implementar validación de borrador y ruta local, sin emitir contenido
      sensible en excepciones ni logs.
- [~] 1.3 Localizar el editor únicamente dentro del campo visible `Otra
      información`; soportar los controles Lightning disponibles sin depender de
      un índice fijo. Implementado; falta validación manual contra el DOM real.

## Fase 2 — Runner supervisado

- [x] 2.1 Crear `run_comment_assisted.py`: perfil Edge, login/2FA manuales,
      Lead ID y ruta de borrador solicitados localmente.
- [x] 2.2 Reutilizar el lector validado para obtener el historial y calcular el
      próximo INT antes de abrir edición.
- [~] 2.3 Activar y completar solo el editor de `Otra información`; detenerse
      inmediatamente antes de cualquier acción de guardado. Implementado; falta
      prueba manual.
- [x] 2.4 Tomar capturas y logs locales ante errores, con ID enmascarado y sin
      contenido del comentario.

## Fase 3 — Verificación

- [x] 3.1 Ejecutar pruebas unitarias, compilación y escaneo estático que confirme
      ausencia de automatización de botones de negocio.
- [ ] 3.2 Ejecutar una prueba manual de un Lead: verificar visualmente el número,
      separación y cuerpo del borrador antes de decidir Guardar o Cancelar.
- [ ] 3.3 Revisar logs/capturas y confirmar que no contienen comentarios, datos
      personales, cookies, contraseñas ni 2FA.
- [ ] 3.4 Actualizar documentación, validar OpenSpec y actualizar Graphify.
