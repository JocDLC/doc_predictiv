# Graph Report - C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo  (2026-09-15)

## Corpus Check
- 24 files · ~116,618 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 201 nodes · 375 edges · 34 communities detected
- Extraction: 63% EXTRACTED · 37% INFERRED · 0% AMBIGUOUS · INFERRED: 137 edges (avg confidence: 0.78)
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

## God Nodes (most connected - your core abstractions)
1. `main()` - 19 edges
2. `ReportReaderTests` - 18 edges
3. `VisibleLead` - 17 edges
4. `read_visible_unassigned_leads()` - 17 edges
5. `main()` - 15 edges
6. `main()` - 14 edges
7. `FakeRow` - 13 edges
8. `report_structure_summary()` - 12 edges
9. `CommentReaderTests` - 12 edges
10. `FakeTable` - 11 edges

## Surprising Connections (you probably didn't know these)
- `find_other_information()` --calls--> `main()`  [INFERRED]
  C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\comment_reader.py → C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\run_comment_assisted.py
- `find_other_information()` --calls--> `main()`  [INFERRED]
  C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\comment_reader.py → C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\run_comment_read_only.py
- `other_information_structure_summary()` --calls--> `main()`  [INFERRED]
  C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\comment_reader.py → C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\run_comment_read_only.py
- `next_attempt_number()` --calls--> `main()`  [INFERRED]
  C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\comment_reader.py → C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\run_comment_assisted.py
- `next_attempt_number()` --calls--> `main()`  [INFERRED]
  C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\comment_reader.py → C:\Users\ax24611\Downloads\_dev\Docuentar_predictivo\automation_salesforce\run_comment_read_only.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (11): VisibleLead, LocalReportTests, FakeCell, FakeDriver, FakeFrame, FakeFrameDriver, FakeLink, FakeRow (+3 more)

### Community 1 - "Community 1"
Cohesion: 0.11
Nodes (15): field_result_in_any_frame(), Busca el campo visible en el documento principal y en iframes accesibles., compose_other_information(), find_edit_control(), find_editor_control(), find_element_in_any_frame(), load_draft_body(), prepare_other_information() (+7 more)

### Community 2 - "Community 2"
Cohesion: 0.14
Nodes (19): create_driver(), detect_browser(), build_record_url(), capture_failure(), create_logger(), mask_lead_id(), main(), main() (+11 more)

### Community 3 - "Community 3"
Cohesion: 0.16
Nodes (24): deduplicate_visible_leads(), extract_created_at(), extract_lead_id(), find_elements(), find_header_index(), find_owner_header_index(), find_report_rows(), find_report_table() (+16 more)

### Community 4 - "Community 4"
Cohesion: 0.14
Nodes (10): field_result_if_found(), field_result_with_text(), find_other_information(), next_attempt_number(), normalize_label(), other_information_structure_summary(), Devuelve solo metadatos del DOM; nunca texto del comentario., text_without_field_label() (+2 more)

### Community 5 - "Community 5"
Cohesion: 0.28
Nodes (4): confirm_preparation(), print_preparation_summary(), queue_directory_from_config(), AssistedRunnerTests

### Community 6 - "Community 6"
Cohesion: 0.83
Nodes (3): available_report_path(), report_payload(), write_unassigned_leads_report()

### Community 7 - "Community 7"
Cohesion: 0.67
Nodes (0):

### Community 8 - "Community 8"
Cohesion: 1.0
Nodes (0):

### Community 9 - "Community 9"
Cohesion: 1.0
Nodes (0):

### Community 10 - "Community 10"
Cohesion: 1.0
Nodes (0):

### Community 11 - "Community 11"
Cohesion: 1.0
Nodes (0):

### Community 12 - "Community 12"
Cohesion: 1.0
Nodes (1): Devuelve un único control visible y deja el driver en su contexto.

### Community 13 - "Community 13"
Cohesion: 1.0
Nodes (1): Devuelve solo metadatos del DOM; nunca texto del comentario.

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (1): Elimina representaciones DOM repetidas sin descartar filas sin ID.

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (1): Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): Prioriza filas HTML y elimina contenedores ARIA que duplican registros.

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Elimina representaciones DOM repetidas sin descartar filas sin ID.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Devuelve metadatos estructurales sin leer valores de filas ni encabezados.

## Knowledge Gaps
- **30 isolated node(s):** `Busca el campo visible en el documento principal y en iframes accesibles.`, `Devuelve solo metadatos del DOM; nunca texto del comentario.`, `Devuelve un único control visible y deja el driver en su contexto.`, `Elimina representaciones DOM repetidas sin descartar filas sin ID.`, `Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.` (+25 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 8`** (2 nodes): `verify-setup.ps1`, `Test-Requirement()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 9`** (1 nodes): `_analyze.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 10`** (1 nodes): `install.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 11`** (1 nodes): `setup-project.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 12`** (1 nodes): `Devuelve un único control visible y deja el driver en su contexto.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 13`** (1 nodes): `Devuelve solo metadatos del DOM; nunca texto del comentario.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 14`** (1 nodes): `Elimina representaciones DOM repetidas sin descartar filas sin ID.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (1 nodes): `Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (1 nodes): `Prioriza filas HTML y elimina contenedores ARIA que duplican registros.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Elimina representaciones DOM repetidas sin descartar filas sin ID.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Inspecciona contextos DOM sin extraer textos, celdas ni identificadores.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Busca elementos sin mutar el DOM, incluyendo Shadow DOM abierto cuando existe.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Devuelve metadatos estructurales sin leer valores de filas ni encabezados.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `Community 2` to `Community 3`, `Community 6`?**
  _High betweenness centrality (0.172) - this node is a cross-community bridge._
- **Why does `main()` connect `Community 2` to `Community 1`, `Community 4`, `Community 5`?**
  _High betweenness centrality (0.151) - this node is a cross-community bridge._
- **Why does `read_visible_unassigned_leads()` connect `Community 3` to `Community 0`, `Community 2`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `main()` (e.g. with `load_config()` and `create_logger()`) actually correct?**
  _`main()` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `VisibleLead` (e.g. with `LocalReportTests` and `FakeCell`) actually correct?**
  _`VisibleLead` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `read_visible_unassigned_leads()` (e.g. with `main()` and `.test_reader_includes_date_position_and_status_in_local_report_data()`) actually correct?**
  _`read_visible_unassigned_leads()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `main()` (e.g. with `load_config()` and `create_logger()`) actually correct?**
  _`main()` has 13 INFERRED edges - model-reasoned connections that need verification._