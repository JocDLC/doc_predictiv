"""Favicons autocontenidos y publicación segura de páginas locales."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote


FAVICON_SVGS = {
    "business-flow": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#0f172a"/><circle cx="8" cy="16" r="4" fill="#22d3ee"/><circle cx="24" cy="9" r="4" fill="#5eead4"/><circle cx="24" cy="23" r="4" fill="#22d3ee"/><path d="M12 16h5m3-4v8" stroke="#e0f2fe" stroke-width="2" stroke-linecap="round"/></svg>""",
    "architecture": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#0f172a"/><path d="M7 9h18v5H7zm3 9h15v5H10z" fill="#60a5fa"/><path d="M7 22h18" stroke="#dbeafe" stroke-width="2" stroke-linecap="round"/></svg>""",
    "productivity": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#1e1b4b"/><path d="M7 24V9m0 15h18" stroke="#ddd6fe" stroke-width="2" stroke-linecap="round"/><path d="m10 20 5-5 4 3 6-8" fill="none" stroke="#c4b5fd" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="M22 10h3v3" fill="none" stroke="#f5f3ff" stroke-width="2" stroke-linecap="round"/></svg>""",
}


def favicon_link(identity: str) -> str:
    """Devuelve un enlace favicon SVG sin dependencias de red."""

    try:
        svg = FAVICON_SVGS[identity]
    except KeyError as exc:
        raise ValueError(f"Identidad de página desconocida: {identity}.") from exc
    href = f"data:image/svg+xml,{quote(svg, safe='')}"
    return (
        f'<link rel="icon" type="image/svg+xml" data-favicon="{identity}" '
        f'href="{href}">'
    )


def decorate_html(html: str, identity: str) -> str:
    """Inserta un único favicon antes de cerrar el head y conserva el body."""

    if "</head>" not in html:
        raise ValueError("El HTML publicado no contiene </head>.")
    if 'rel="icon"' in html:
        raise ValueError("El HTML publicado ya declara un favicon.")
    return html.replace("</head>", f"  {favicon_link(identity)}\n</head>", 1)


def body(html: str) -> str:
    """Extrae el cuerpo textual usado para comprobar una publicación decorada."""

    marker = "<body"
    position = html.lower().find(marker)
    if position < 0:
        raise ValueError("El HTML publicado no contiene <body>.")
    return html[position:]


def verify_decorated_html(source_html: str, published_html: str, identity: str) -> None:
    """Verifica que la decoración solo añadió el favicon esperado al head."""

    expected = favicon_link(identity)
    if expected not in published_html:
        raise ValueError(f"Falta el favicon esperado para {identity}.")
    if published_html.count('rel="icon"') != 1:
        raise ValueError("La publicación debe contener exactamente un favicon.")
    if body(source_html) != body(published_html):
        raise ValueError("La publicación modificó el cuerpo validado por Archify.")


def publish_decorated_html(
    source_path: Path, published_path: Path, identity: str
) -> Path:
    """Publica una copia decorada de un HTML base previamente validado."""

    source_html = source_path.read_text(encoding="utf-8")
    published_html = decorate_html(source_html, identity)
    verify_decorated_html(source_html, published_html, identity)
    published_path.parent.mkdir(parents=True, exist_ok=True)
    published_path.write_text(published_html, encoding="utf-8", newline="\n")
    return published_path
