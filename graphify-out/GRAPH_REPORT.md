# Graph Report - C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo  (2026-09-23)

## Corpus Check
- 41 files · ~241,952 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 412 nodes · 768 edges · 78 communities detected
- Extraction: 62% EXTRACTED · 38% INFERRED · 0% AMBIGUOUS · INFERRED: 291 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]

## God Nodes (most connected - your core abstractions)
1. `main()` - 29 edges
2. `read_visible_unassigned_leads()` - 27 edges
3. `ReportReaderTests` - 26 edges
4. `main()` - 23 edges
5. `VisibleLead` - 22 edges
6. `main()` - 20 edges
7. `CommentWriterTests` - 17 edges
8. `FakeRow` - 17 edges
9. `main()` - 16 edges
10. `main()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `find_other_information()` --calls--> `main()`  [INFERRED]
  C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\comment_reader.py → C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\run_comment_assisted.py
- `find_other_information()` --calls--> `main()`  [INFERRED]
  C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\comment_reader.py → C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\run_comment_read_only.py
- `main()` --calls--> `find_other_information()`  [INFERRED]
  C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\run_corrections.py → C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\comment_reader.py
- `find_other_information()` --calls--> `verify_saved_value()`  [INFERRED]
  C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\comment_reader.py → C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\run_document_queue.py
- `find_other_information()` --calls--> `main()`  [INFERRED]
  C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\comment_reader.py → C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\run_document_queue.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (43): create_driver(), debugger_is_listening(), detect_browser(), launch_persistent_browser(), Abre el navegador con el perfil dedicado y puerto de depuración; queda abierto a, Cierra el navegador solo si lo abrió este proceso; si está adjunto, lo deja abie, release_driver(), build_record_url() (+35 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (23): field_result_in_any_frame(), Busca el campo visible en el documento principal y en iframes accesibles., compose_attempts(), compose_other_information(), describe_editor_candidates(), find_edit_control(), find_editor_control(), find_element_in_any_frame() (+15 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (11): extract_lead_id(), record_route_pattern(), FakeCell, FakeDriver, FakeFrame, FakeFrameDriver, FakeLink, FakeRow (+3 more)

### Community 3 - "Community 3"
Cohesion: 0.1
Nodes (36): aligned_values(), column_offset(), deduplicate_visible_leads(), extract_created_at(), extract_row_details(), find_elements(), find_header_index(), find_owner_header_index() (+28 more)

### Community 4 - "Community 4"
Cohesion: 0.13
Nodes (13): available_columns(), lead_payload(), render_leads_ui(), source_value(), write_leads_ui(), available_report_path(), report_payload(), write_unassigned_leads_report() (+5 more)

### Community 5 - "Community 5"
Cohesion: 0.14
Nodes (10): field_result_if_found(), field_result_with_text(), find_other_information(), next_attempt_number(), normalize_label(), other_information_structure_summary(), Devuelve solo metadatos del DOM; nunca texto del comentario., text_without_field_label() (+2 more)

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (11): load_corrections(), Carga y valida colas de corrección generadas desde la UI local.  Cada corrección, Devuelve las correcciones válidas o lanza ValueError con el motivo., _valid_correction(), correction_entry(), Aplica correcciones locales de ``Otra información`` de forma segura.  Por cada c, content_hash(), CorrectionDecisionTests (+3 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (11): ask_lead_action(), normalize_persisted_text(), print_lead_summary(), Iguala diferencias de solo-forma entre el texto escrito y el mostrado.      En m, Confirma que Otra información quedó persistida tras el guardado.      La primera, Evita navegar al siguiente Lead mientras el editor actual siga abierto., Muestra solo métricas operativas; nunca imprime el comentario preparado., Obliga una elección explícita antes de abrir el editor del Lead. (+3 more)

### Community 8 - "Community 8"
Cohesion: 0.23
Nodes (4): load_queue(), _validate_attempt(), _validate_lead(), QueueLoaderTests

### Community 9 - "Community 9"
Cohesion: 0.28
Nodes (4): confirm_preparation(), print_preparation_summary(), queue_directory_from_config(), AssistedRunnerTests

### Community 10 - "Community 10"
Cohesion: 0.28
Nodes (6): UiServerTests, main(), make_handler(), Servidor local mínimo para que la UI dispare el bot sin usar la terminal.  Escuc, Publica puerto y token donde la UI puede leerlos (carpeta ya vinculada)., write_session_file()

### Community 11 - "Community 11"
Cohesion: 0.28
Nodes (2): BrowserFactoryTests, FakeDriver

### Community 12 - "Community 12"
Cohesion: 0.31
Nodes (5): `--completo` recorre toda la bandeja; por defecto solo lo cargado en pantalla., Lee la vista actual por defecto; el recorrido ampliado es explícito., read_report(), scan_mode(), LeadsUiRunnerTests

### Community 13 - "Community 13"
Cohesion: 0.4
Nodes (2): print_comment_summary(), CommentSummaryTests

### Community 14 - "Community 14"
Cohesion: 0.67
Nodes (0): 

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (0): 

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (0): 

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (0): 

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (0): 

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Abre el navegador con el perfil dedicado y puerto de depuración; queda abierto a

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Cierra el navegador solo si lo abrió este proceso; si está adjunto, lo deja abie

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Pulsa Guardar del formulario de edición activo y espera a que se cierre.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Mantiene los resultados junto a la cola, fuera del repositorio.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Persiste el último estado de cada Lead para poder reanudar la revisión.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Muestra solo métricas operativas; nunca imprime el comentario preparado.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Obliga una elección explícita antes de abrir el editor del Lead.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Reabre el registro y confirma que Otra información quedó persistida.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Evita navegar al siguiente Lead mientras el editor actual siga abierto.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Registra un fallo sin exponer el texto ni detener el resto de la cola.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Mantiene los resultados junto a la cola, fuera del repositorio.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Persiste el último estado de cada Lead para poder reanudar la revisión.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Muestra solo métricas operativas; nunca imprime el comentario preparado.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Obliga una elección explícita antes de abrir el editor del Lead.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Evita navegar al siguiente Lead mientras el editor actual siga abierto.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Registra un fallo sin exponer el texto ni detener el resto de la cola.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Devuelve un único control visible y deja el driver en su contexto.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Busca el campo visible en el documento principal y en iframes accesibles.

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Devuelve solo metadatos del DOM; nunca texto del comentario.

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Devuelve un único control visible y deja el driver en su contexto.

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Recorre la bandeja de arriba hacia abajo y de izquierda a derecha, sin abrir Lea

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): Conserva toda columna leída de la bandeja aunque no tenga alias configurado.

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Prioriza filas HTML y elimina contenedores ARIA que duplican registros.

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): Metadatos por fila para diagnóstico local; nunca incluye valores de celdas.

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): Usa los encabezados de la grilla o, si Lightning los separa, los del reporte vis

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Alinea celdas con encabezados usando la columna de propietario como referencia.

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): `--completo` recorre toda la bandeja; por defecto solo lo cargado en pantalla.

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): Lee la vista actual por defecto; el recorrido ampliado es explícito.

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): Devuelve un único control visible y deja el driver en su contexto.

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): `--completo` recorre toda la bandeja; por defecto solo lo cargado en pantalla.

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): Elimina representaciones DOM repetidas sin descartar filas sin ID.

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Prioriza filas HTML y elimina contenedores ARIA que duplican registros.

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): Devuelve un único control visible y deja el driver en su contexto.

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): Devuelve solo metadatos del DOM; nunca texto del comentario.

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): Elimina representaciones DOM repetidas sin descartar filas sin ID.

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (1): Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (1): Prioriza filas HTML y elimina contenedores ARIA que duplican registros.

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (1): Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (1): Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (1): Elimina representaciones DOM repetidas sin descartar filas sin ID.

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (1): Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (1): Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (1): Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (1): Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (1): Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

## Knowledge Gaps
- **94 isolated node(s):** `Abre el navegador con el perfil dedicado y puerto de depuración; queda abierto a`, `Cierra el navegador solo si lo abrió este proceso; si está adjunto, lo deja abie`, `Busca el campo visible en el documento principal y en iframes accesibles.`, `Devuelve solo metadatos del DOM; nunca texto del comentario.`, `Devuelve un único control visible y deja el driver en su contexto.` (+89 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 15`** (2 nodes): `verify-setup.ps1`, `Test-Requirement()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (1 nodes): `_analyze.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `install.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `setup-project.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Abre el navegador con el perfil dedicado y puerto de depuración; queda abierto a`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Cierra el navegador solo si lo abrió este proceso; si está adjunto, lo deja abie`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Pulsa Guardar del formulario de edición activo y espera a que se cierre.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Mantiene los resultados junto a la cola, fuera del repositorio.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Persiste el último estado de cada Lead para poder reanudar la revisión.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Muestra solo métricas operativas; nunca imprime el comentario preparado.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Obliga una elección explícita antes de abrir el editor del Lead.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Reabre el registro y confirma que Otra información quedó persistida.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Evita navegar al siguiente Lead mientras el editor actual siga abierto.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Registra un fallo sin exponer el texto ni detener el resto de la cola.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Mantiene los resultados junto a la cola, fuera del repositorio.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Persiste el último estado de cada Lead para poder reanudar la revisión.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Muestra solo métricas operativas; nunca imprime el comentario preparado.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Obliga una elección explícita antes de abrir el editor del Lead.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Evita navegar al siguiente Lead mientras el editor actual siga abierto.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Registra un fallo sin exponer el texto ni detener el resto de la cola.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Devuelve un único control visible y deja el driver en su contexto.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Busca el campo visible en el documento principal y en iframes accesibles.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Devuelve solo metadatos del DOM; nunca texto del comentario.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Devuelve un único control visible y deja el driver en su contexto.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Recorre la bandeja de arriba hacia abajo y de izquierda a derecha, sin abrir Lea`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `Conserva toda columna leída de la bandeja aunque no tenga alias configurado.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `Prioriza filas HTML y elimina contenedores ARIA que duplican registros.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `Metadatos por fila para diagnóstico local; nunca incluye valores de celdas.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `Usa los encabezados de la grilla o, si Lightning los separa, los del reporte vis`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `Alinea celdas con encabezados usando la columna de propietario como referencia.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): ``--completo` recorre toda la bandeja; por defecto solo lo cargado en pantalla.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `Lee la vista actual por defecto; el recorrido ampliado es explícito.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `Devuelve un único control visible y deja el driver en su contexto.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): ``--completo` recorre toda la bandeja; por defecto solo lo cargado en pantalla.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `Elimina representaciones DOM repetidas sin descartar filas sin ID.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Prioriza filas HTML y elimina contenedores ARIA que duplican registros.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `Devuelve un único control visible y deja el driver en su contexto.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `Devuelve solo metadatos del DOM; nunca texto del comentario.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `Elimina representaciones DOM repetidas sin descartar filas sin ID.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `Prioriza filas HTML y elimina contenedores ARIA que duplican registros.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `Elimina representaciones DOM repetidas sin descartar filas sin ID.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `Community 0` to `Community 8`, `Community 1`, `Community 5`, `Community 7`?**
  _High betweenness centrality (0.179) - this node is a cross-community bridge._
- **Why does `main()` connect `Community 0` to `Community 1`, `Community 5`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.120) - this node is a cross-community bridge._
- **Why does `read_visible_unassigned_leads()` connect `Community 3` to `Community 0`, `Community 2`, `Community 4`, `Community 12`?**
  _High betweenness centrality (0.120) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `main()` (e.g. with `load_config()` and `load_queue()`) actually correct?**
  _`main()` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `read_visible_unassigned_leads()` (e.g. with `read_report()` and `main()`) actually correct?**
  _`read_visible_unassigned_leads()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `main()` (e.g. with `load_config()` and `load_corrections()`) actually correct?**
  _`main()` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `VisibleLead` (e.g. with `LeadsUiTests` and `LocalReportTests`) actually correct?**
  _`VisibleLead` has 19 INFERRED edges - model-reasoned connections that need verification._