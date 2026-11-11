## 1. Implementación

- [x] 1.1 `_save_contact_panel_after_reload`: espera ≤3 s, `driver.refresh()`,
      `wait_for_lightning_ready`, nueva ventana de búsqueda del panel; devuelve
      `(outcome, reloaded)` con `panel_tras_reload` cuando el Save sale tras
      la recarga.
- [x] 1.2 `finalize_pick_up` invoca el reintento cuando el outcome es
      `sin_panel` tras las ventanas existentes.
- [x] 1.3 Re-verificación de la marca de `Otra información` cuando la página
      se recargó (idempotente, solo cuando hay `mark_text`).
- [x] 1.4 Regresiones: panel tras reload → `panel_tras_reload`; reload sin
      panel → `sin_panel` con diagnóstico; refresh no disponible → sin
      recarga; marca re-verificada en la rama WhatsApp.

## 2. Verificación

- [ ] 2.1 Suite completa + lint + openspec validate.
- [ ] 2.2 Piloto: confirmar en el log que `panel_tras_reload` aparece y el
      lead pasa a "En curso".
