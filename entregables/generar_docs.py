# -*- coding: utf-8 -*-
"""Genera los dos entregables Word (Manual e Informe) con tono ligero.

Ejecutar desde la carpeta del repo:
    python entregables/generar_docs.py
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor, Inches

AQUI = Path(__file__).resolve().parent
DIAGRAMA = AQUI / "diagrama_flujo.png"

AZUL = RGBColor(0x1F, 0x4E, 0x79)
AZUL_CLARO = RGBColor(0x2E, 0x74, 0xB5)
GRIS = RGBColor(0x59, 0x59, 0x59)
VERDE = RGBColor(0x1E, 0x7A, 0x46)


# ----------------------------------------------------------------------------
# Helpers de estilo
# ----------------------------------------------------------------------------
def set_base_style(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15


def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def portada(doc, titulo, subtitulo, etiqueta):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(etiqueta.upper())
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.color.rgb = AZUL_CLARO

    p = doc.add_paragraph()
    run = p.add_run(titulo)
    run.font.size = Pt(30)
    run.font.bold = True
    run.font.color.rgb = AZUL

    p = doc.add_paragraph()
    run = p.add_run(subtitulo)
    run.font.size = Pt(14)
    run.font.color.rgb = GRIS

    p = doc.add_paragraph()
    run = p.add_run("Proyecto: Documentador Predictivo + Bot RPA (Salesforce / Wolkvox)")
    run.font.size = Pt(10)
    run.font.color.rgb = GRIS
    p = doc.add_paragraph()
    run = p.add_run("Fecha: 14 de octubre de 2026     |     Autor: ______________________")
    run.font.size = Pt(10)
    run.font.color.rgb = GRIS


def h1(doc, texto):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    run = p.add_run(texto)
    run.font.size = Pt(17)
    run.font.bold = True
    run.font.color.rgb = AZUL
    _borde_inferior(p)
    return p


def h2(doc, texto):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    run = p.add_run(texto)
    run.font.size = Pt(13)
    run.font.bold = True
    run.font.color.rgb = AZUL_CLARO
    return p


def _borde_inferior(p):
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), "D0D7E2")
    pbdr.append(bottom)
    pPr.append(pbdr)


def parrafo(doc, texto):
    p = doc.add_paragraph(texto)
    return p


def vinneta(doc, items):
    for it in items:
        doc.add_paragraph(it, style="List Bullet")


def pasos(doc, items):
    for it in items:
        doc.add_paragraph(it, style="List Number")


def callout(doc, titulo, cuerpo, color_fondo="EAF2FB", color_barra="2E74B5"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    shade(cell, color_fondo)
    # barra de color a la izquierda
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "28")
    left.set(qn("w:space"), "0")
    left.set(qn("w:color"), color_barra)
    borders.append(left)
    tcPr.append(borders)

    p = cell.paragraphs[0]
    r = p.add_run(titulo)
    r.font.bold = True
    r.font.size = Pt(11)
    r.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    p2 = cell.add_paragraph(cuerpo)
    p2.runs[0].font.size = Pt(10.5)
    doc.add_paragraph()
    return tbl


def tabla(doc, encabezados, filas, anchos=None):
    tbl = doc.add_table(rows=1, cols=len(encabezados))
    tbl.style = "Light Grid Accent 1"
    hdr = tbl.rows[0].cells
    for i, texto in enumerate(encabezados):
        hdr[i].paragraphs[0].add_run(texto).font.bold = True
    for fila in filas:
        celdas = tbl.add_row().cells
        for i, valor in enumerate(fila):
            celdas[i].text = str(valor)
    if anchos:
        for i, w in enumerate(anchos):
            for row in tbl.rows:
                row.cells[i].width = Inches(w)
    return tbl


# ============================================================================
# DOCUMENTO 1 — MANUAL DE OPERACION
# ============================================================================
def generar_manual(ruta):
    doc = Document()
    set_base_style(doc)

    portada(
        doc,
        "Manual de operación del Bot RPA",
        "Configuración y operación para la documentación y asignación de leads",
        "Guía paso a paso",
    )
    doc.add_page_break()

    h1(doc, "1. Propósito del sistema")
    parrafo(
        doc,
        "Cada día ingresan numerosos leads que deben documentarse en Salesforce: "
        "registrar el resultado de cada llamada, uno por uno. Realizada de forma "
        "manual, es una tarea repetitiva, lenta y propensa a errores. El "
        "asistente automatizado (en adelante, el bot) se encarga de esa carga "
        "operativa.",
    )
    parrafo(
        doc,
        "El funcionamiento es sencillo: el operador selecciona los leads a "
        "documentar y el sistema abre Salesforce, registra el historial de "
        "llamadas en el campo correspondiente, guarda y vuelve a leer el registro "
        "para confirmar que quedó correcto. Si detecta una inconsistencia, la "
        "señala para revisión. El sistema no modifica ni elimina información por "
        "fuera de lo indicado.",
    )
    callout(
        doc,
        "En síntesis",
        "El sistema reemplaza horas de registro manual por una operación "
        "automática y verificada. La decisión es del operador; la ejecución y la "
        "comprobación, del sistema.",
    )

    h1(doc, "2. Visión general del flujo")
    parrafo(
        doc,
        "El proceso completo se compone de dos recorridos complementarios: la "
        "preparación de una campaña de llamadas y el registro posterior de sus "
        "resultados en Salesforce.",
    )
    if DIAGRAMA.exists():
        doc.add_picture(str(DIAGRAMA), width=Inches(6.3))
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cap.add_run("Figura 1. Del contacto a la documentación: flujo completo del proceso.")
        r.font.size = Pt(9)
        r.font.italic = True
        r.font.color.rgb = GRIS
    h2(doc, "Cómo leer el diagrama")
    vinneta(
        doc,
        [
            "Recorrido 1 (superior): se exporta un archivo desde Salesforce, el "
            "sistema lo prepara y genera un archivo listo para cargar en la "
            "plataforma de llamadas (Wolkvox) e iniciar la campaña.",
            "Recorrido 2 (inferior): la plataforma de llamadas devuelve el "
            "resultado de cada intento. El sistema los ordena, el operador "
            "selecciona el lote y la documentación se realiza de forma manual o "
            "automática. Salesforce confirma el registro y, de ser necesario, se corrige.",
            "Referencia de colores: celeste indica pasos automáticos; ámbar, "
            "decisiones del operador; verde, controles y verificación. La línea "
            "punteada final solo interviene cuando corresponde una corrección.",
        ],
    )

    h1(doc, "3. Requisitos previos")
    vinneta(
        doc,
        [
            "Equipo con Windows y el navegador Microsoft Edge instalado.",
            "Paquete del sistema (la carpeta con INICIAR.bat incluye todos los "
            "componentes necesarios para su ejecución).",
            "Usuario y contraseña de Salesforce, y el dispositivo para el segundo "
            "factor de autenticación (el código de verificación de ingreso).",
            "Archivo de intentos descargado de la plataforma de llamadas, al "
            "momento de documentar.",
        ],
    )
    callout(
        doc,
        "Consideración de seguridad",
        "No se deben compartir la carpeta de perfil del navegador, el archivo de "
        "configuración, los registros de actividad ni las capturas, ya que pueden "
        "contener datos de clientes. Esa información permanece únicamente en el equipo.",
        color_fondo="FDEEEE",
        color_barra="C0392B",
    )

    h1(doc, "4. Configuración inicial (por única vez)")
    pasos(
        doc,
        [
            "Copiar el archivo de configuración de ejemplo y renombrarlo a config.json.",
            "Verificar en config.json que el propietario y el tipo de registro "
            "sean los correctos. Ante la duda, conservar los valores predeterminados.",
            "Ejecutar INICIAR.bat una vez: inicia la interfaz de trabajo y el "
            "navegador del sistema.",
            "Iniciar sesión en Salesforce dentro de ese navegador y completar el "
            "segundo factor de autenticación de forma manual. El sistema no "
            "automatiza este paso por razones de seguridad.",
            "A partir de ese momento, el navegador conserva la sesión y no vuelve "
            "a solicitar el ingreso en cada ejecución.",
        ],
    )
    callout(
        doc,
        "Recomendación práctica",
        "Conviene mantener abierta la ventana del navegador del sistema durante "
        "la jornada. Si se cierra, el sistema abrirá una nueva y volverá a "
        "solicitar el inicio de sesión.",
    )

    h1(doc, "5. Puesta en marcha diaria")
    parrafo(doc, "La rutina de inicio es breve:")
    pasos(
        doc,
        [
            "Ejecutar INICIAR.bat.",
            "Se abre la interfaz de trabajo en el navegador.",
            "En el primer uso del día, verificar que la sesión de Salesforce siga "
            "activa; de lo contrario, iniciar sesión nuevamente.",
        ],
    )

    h1(doc, "6. Proceso A — Documentación de leads")
    parrafo(
        doc,
        "Es la función principal del sistema. Admite dos modalidades: supervisada "
        "(el operador confirma cada guardado) y automática (el sistema guarda y "
        "verifica por sí mismo).",
    )
    h2(doc, "6.1. Preparar el lote")
    pasos(
        doc,
        [
            "En la interfaz, cargar el archivo de intentos descargado de la "
            "plataforma de llamadas.",
            "El sistema agrupa cada lead con sus llamadas pendientes.",
            "Seleccionar los leads a documentar mediante la casilla 'Cola' (la "
            "opción 'Seleccionar...' permite armar tandas con rapidez).",
            "Ingresar a 'Ir a cola del bot' para visualizar únicamente los leads elegidos.",
        ],
    )
    h2(doc, "6.2. Ejecutar la documentación")
    pasos(
        doc,
        [
            "Presionar 'Ejecutar bot' (o utilizar el comando de la cola activa "
            "desde la terminal, según se prefiera).",
            "Por cada lead, el sistema abre el registro, lee lo ya documentado y "
            "calcula el número de intento que corresponde.",
            "En modalidad automática: registra el historial, guarda el cambio, "
            "reabre el registro y lo relee para confirmar que coincide.",
            "Los leads confirmados se retiran automáticamente de la cola y quedan "
            "marcados como procesados por el sistema. Los que presentan algún "
            "problema quedan señalados para revisión.",
        ],
    )
    callout(
        doc,
        "Modalidad supervisada",
        "En esta modalidad el sistema deja el texto cargado en el campo y se "
        "detiene, para que el operador revise y confirme o cancele el guardado en "
        "Salesforce. Se escribe 'PREPARAR' para cargar, 's' para omitir un lead y "
        "'q' para finalizar.",
    )

    h1(doc, "7. Proceso B — Asignación y cierre de leads")
    parrafo(
        doc,
        "Además de documentar, el sistema facilita la gestión del estado de los "
        "leads: su toma desde la bandeja (asignación) y su cierre cuando corresponde.",
    )
    h2(doc, "7.1. Toma de leads desde la bandeja")
    vinneta(
        doc,
        [
            "La vista 'Monitor de Bandeja' supervisa la bandeja de Salesforce en "
            "una ventana dedicada.",
            "Al detectar un lead elegible, el sistema realiza la toma, guarda el "
            "panel de contacto y registra la marca de asignación en el campo de notas.",
            "Si el lead solicitó contacto por WhatsApp y la opción correspondiente "
            "está activada, envía el primer mensaje y espera la confirmación de envío.",
        ],
    )
    h2(doc, "7.2. Cierre de leads por lote")
    vinneta(
        doc,
        [
            "En la cola, cada lead dispone de la casilla 'Incluir en cierre' y un "
            "motivo (por ejemplo, ilocalizable o sin interacción).",
            "La opción 'Ejecutar cierre' solicita confirmación y, por cada lead, "
            "completa el motivo y la clasificación correspondiente, guarda y verifica.",
            "Solo una vez verificado todo, realiza la conversión y confirma que el "
            "lead quedó asignado al equipo que corresponde.",
            "Si algún dato no puede comprobarse, el lead queda pendiente y el "
            "sistema no fuerza la conversión.",
        ],
    )
    callout(
        doc,
        "Criterio de cierre",
        "La decisión de cerrar un lead corresponde al operador; no existe un "
        "mínimo de intentos obligatorio. El sistema ejecuta únicamente lo indicado.",
    )

    h1(doc, "8. Revisión y corrección de registros")
    parrafo(
        doc,
        "Si se detecta un registro incorrecto, puede corregirse de forma "
        "controlada sin editar Salesforce manualmente:",
    )
    pasos(
        doc,
        [
            "Editar el borrador local del lead en la interfaz y guardarlo (esta "
            "acción aún no modifica Salesforce).",
            "Presionar 'Exportar correcciones': se genera un archivo únicamente "
            "con lo que cambió.",
            "Ejecutar la corrección. El sistema reabre el lead y comprueba que no "
            "haya sido modificado por otra vía.",
            "Si coincide, reemplaza y verifica el registro. Si hubo un cambio "
            "externo, no escribe nada y lo señala como conflicto para su revisión.",
        ],
    )

    h1(doc, "9. Resultados de productividad")
    parrafo(doc, "Mediciones registradas en Salesforce con leads reales:")
    tabla(
        doc,
        ["Fecha", "Muestra", "Promedio por lead", "Leads por hora", "Verificación"],
        [
            ["28/09/2026", "10 leads", "15,8 s", "~227", "Sin controles adicionales"],
            ["02/10/2026", "20 leads", "18,9 s", "~190", "100% verificado"],
        ],
    )
    parrafo(
        doc,
        "Los aproximadamente 3 segundos adicionales de la segunda medición "
        "corresponden a los controles de calidad: el sistema lee el registro "
        "antes de escribir y vuelve a leerlo tras guardar. Para el operador, el "
        "tiempo dedicado por lead se reduce de manera significativa: su rol pasa a "
        "ser la revisión de resultados y la atención de los casos señalados.",
    )

    h1(doc, "10. Resolución de problemas frecuentes")
    tabla(
        doc,
        ["Situación", "Acción recomendada"],
        [
            ["El botón 'Ejecutar bot' no responde",
             "Cerrar y volver a abrir la interfaz con INICIAR.bat."],
            ["Solicita iniciar sesión en cada ejecución",
             "Mantener abierta la ventana del navegador del sistema entre tandas."],
            ["Un lead quedó señalado con error",
             "Abrirlo en Salesforce con la opción manual, revisarlo y volver a encolarlo."],
            ["El navegador permanece cargando",
             "Cerrar las pestañas adicionales del sistema y reiniciar desde INICIAR.bat."],
            ["Una corrección se reporta como conflicto",
             "El lead fue modificado por otra vía: revisarlo manualmente antes de reintentar."],
        ],
        anchos=[2.6, 3.8],
    )

    h1(doc, "11. Glosario")
    tabla(
        doc,
        ["Término", "Definición"],
        [
            ["Lead", "Contacto o posible cliente registrado en Salesforce."],
            ["Archivo CSV", "Archivo de datos tabulares, compatible con Excel."],
            ["Cola", "Conjunto de leads que el sistema procesará."],
            ["Segundo factor (2FA)", "Código de verificación adicional que solicita Salesforce al ingresar."],
            ["Documentar", "Registrar el resultado de las llamadas en el lead."],
            ["Supervisado / Automático", "El operador confirma el guardado, o el sistema guarda y verifica por sí mismo."],
        ],
        anchos=[2.2, 4.2],
    )

    doc.add_paragraph()
    cierre = doc.add_paragraph()
    r = cierre.add_run(
        "Con esta guía es posible operar el sistema de principio a fin. Como "
        "criterio general, el sistema no elimina ni genera información de forma "
        "autónoma: ante cualquier inconsistencia, señala el lead para su revisión."
    )
    r.font.italic = True
    r.font.color.rgb = GRIS

    doc.save(ruta)
    return ruta


# ============================================================================
# DOCUMENTO 2 — INFORME DE AVANCES
# ============================================================================
def generar_informe(ruta):
    doc = Document()
    set_base_style(doc)

    portada(
        doc,
        "Informe de avances",
        "Documentación y asignación de leads mediante el Bot RPA",
        "Reporte para la siguiente sesión",
    )
    doc.add_page_break()

    h1(doc, "Resumen ejecutivo")
    parrafo(
        doc,
        "El sistema de documentación y asignación de leads se encuentra operativo "
        "y documentado. En este período se consolidó la información en un manual "
        "de operación único, se actualizó el diagrama del flujo completo y se "
        "midió la productividad real en Salesforce. En síntesis, el proceso que "
        "antes se realizaba de forma manual hoy se ejecuta de manera automática y "
        "verificada, con el operador a cargo de las decisiones y el sistema de la "
        "ejecución y el control.",
    )
    callout(
        doc,
        "Dato destacado",
        "La documentación de un lead pasó de un registro manual extenso a "
        "aproximadamente 19 segundos verificados. El manual de operación queda "
        "disponible para el equipo.",
        color_fondo="EAF7EF",
        color_barra="1E7A46",
    )

    h1(doc, "1. Encargo recibido")
    vinneta(
        doc,
        [
            "Coordinar las conversaciones y recopilar la documentación del sistema.",
            "Presentar avances en los próximos 15 días para la siguiente sesión.",
            "Documentar el paso a paso para configurar y operar el sistema de "
            "documentación y asignación de leads.",
        ],
    )

    h1(doc, "2. Estado actual de las funcionalidades")
    tabla(
        doc,
        ["Funcionalidad", "Estado"],
        [
            ["Documentación de leads (modalidad supervisada)", "Operativa"],
            ["Documentación de leads (modalidad automática con verificación)", "Operativa"],
            ["Corrección controlada de registros", "Operativa"],
            ["Monitor de bandeja (toma y asignación de leads)", "Operativa; resta prueba final en operación"],
            ["Cierre de leads por lote con conversión", "Operativa; resta prueba final en operación"],
            ["Primer contacto por WhatsApp automático", "Implementada; pendiente de validación con un caso real"],
            ["Manual de operación para el equipo", "Entregado con este informe"],
            ["Diagrama del flujo completo", "Actualizado"],
        ],
        anchos=[4.2, 2.2],
    )

    h1(doc, "3. Indicadores de productividad")
    tabla(
        doc,
        ["Fecha", "Muestra", "Promedio por lead", "Leads por hora", "Verificación"],
        [
            ["28/09/2026", "10 leads", "15,8 s", "~227", "Sin controles adicionales"],
            ["02/10/2026", "20 leads", "18,9 s", "~190", "100% verificado"],
        ],
    )
    parrafo(
        doc,
        "El tiempo dedicado por el operador a cada lead se reduce de manera "
        "significativa: su rol pasa a concentrarse en la revisión de resultados y "
        "la atención de los casos señalados por el sistema.",
    )

    h1(doc, "4. Riesgos y temas pendientes")
    callout(
        doc,
        "Dependencia externa prioritaria",
        "Se encuentra pendiente, desde hace aproximadamente diez meses, la "
        "habilitación del acceso por interfaz de programación (API) de Salesforce. "
        "Contar con ese acceso permitiría que la lectura y la asignación dejen de "
        "depender del navegador, con mayor estabilidad y rapidez. Se recomienda "
        "escalar esta solicitud al área responsable.",
        color_fondo="FFF6E6",
        color_barra="D08B00",
    )
    vinneta(
        doc,
        [
            "Estabilidad del navegador: mitigada mediante sesión persistente, "
            "aunque sigue siendo el punto más sensible hasta disponer del acceso por API.",
            "Prueba final en operación del monitor de bandeja y del cierre por "
            "lote: pendiente de una ejecución real autorizada.",
            "Contacto por WhatsApp automático: pendiente de validación con el "
            "primer caso real que haya solicitado ese canal.",
        ],
    )

    h1(doc, "5. Plan para los próximos 15 días")
    tabla(
        doc,
        ["Objetivo", "Resultado esperado", "Fecha objetivo"],
        [
            ["Distribuir el manual y capacitar al equipo",
             "Operadores utilizando el sistema con la guía", "22/10/2026"],
            ["Prueba final del monitor de bandeja",
             "Toma y asignación verificadas en operación real", "24/10/2026"],
            ["Prueba final del cierre por lote",
             "Cierre y conversión verificados", "27/10/2026"],
            ["Validar el contacto por WhatsApp automático",
             "Primer contacto confirmado", "27/10/2026"],
            ["Escalar la solicitud de acceso por API",
             "Respuesta formal del área responsable", "29/10/2026"],
        ],
        anchos=[2.6, 2.8, 1.2],
    )

    h1(doc, "6. Requerimientos para avanzar")
    vinneta(
        doc,
        [
            "Autorización para las pruebas en operación real (monitor, cierre y WhatsApp).",
            "Un referente del área de Salesforce para gestionar el acceso por API.",
            "Disponibilidad del equipo para una sesión breve de capacitación con el manual.",
        ],
    )

    doc.add_paragraph()
    cierre = doc.add_paragraph()
    r = cierre.add_run(
        "Documento complementario entregado junto a este informe: 'Manual de "
        "operación del Bot RPA', con el paso a paso completo de configuración y operación."
    )
    r.font.italic = True
    r.font.color.rgb = GRIS

    doc.save(ruta)
    return ruta


if __name__ == "__main__":
    m = generar_manual(AQUI / "Manual_Bot_RPA.docx")
    i = generar_informe(AQUI / "Informe_Avances_Bot_RPA.docx")
    print("Generado:", m)
    print("Generado:", i)
