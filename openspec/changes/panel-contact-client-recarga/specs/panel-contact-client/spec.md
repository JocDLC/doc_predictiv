## ADDED Requirements

### Requirement: Reintento del panel tras recarga

Cuando el panel "Contact Client" no aparece tras las ventanas de espera
existentes, el Monitor MUST esperar una pausa breve (≤3 s), recargar la página
del Lead y volver a buscar el panel una vez. Si el panel aparece, MUST pulsar
su Save. El reintento MUST NOT ejecutarse más de una vez por toma y MUST NOT
alterar Pick Up, cobertura, reasignación ni envío de WhatsApp.

#### Scenario: panel renderiza tras recarga
- **WHEN** el panel no se detecta en la ficha y, tras recargar la página, sí aparece
- **THEN** el Monitor pulsa su Save y registra `panel_tras_reload` en la finalización

#### Scenario: panel ausente tras recarga
- **WHEN** el panel sigue sin detectarse después del reload
- **THEN** la toma conserva el diagnóstico `sin_panel` con sus evidencias y el lead no queda marcado como gestionado por un estado falso

#### Scenario: recarga no disponible
- **WHEN** el driver no puede recargar la página
- **THEN** el reintento se omite de forma segura y el outcome queda `sin_panel`

### Requirement: Marca re-verificada tras recarga

Si la página se recargó durante el reintento, el Monitor MUST re-verificar que
la documentación de `Otra información` haya quedado persistida, de forma
idempotente y sin duplicar líneas.

#### Scenario: edición inline abierta se perdió
- **WHEN** la recarga descartó una edición no guardada del campo
- **THEN** el Monitor reescribe la marca prevista y la confirma contra el valor persistido
