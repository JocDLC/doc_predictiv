"""Smoke local y sin dependencias de red del workflow Archify publicado."""

from __future__ import annotations

import contextlib
import http.server
import re
import threading
import urllib.request
from pathlib import Path

from .paths import PUBLISHED_OUTPUT_PATH, TECHNICAL_GRAPH_PATH
from .validator import ContractValidationError

REQUIRED_MARKERS = (
    "Del contacto a la documentación",
    "1 · Salesforce → Wolkvox",
    "2 · Wolkvox → Salesforce",
    "CSV de Salesforce",
    "CSV con intentos",
    "Documentar en Salesforce",
    "Documentar manualmente",
    "Documentar con el bot",
    'data-favicon="business-flow"',
    "Qué recibe:",
    "Qué entrega:",
    "Regla principal:",
    "Si falla:",
)
EXTERNAL_DEPENDENCY = re.compile(
    r"<(?:script|link)\b[^>]*(?:src|href)=[\"']https?://", re.IGNORECASE
)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def smoke_html(output_path: Path = PUBLISHED_OUTPUT_PATH) -> None:
    if output_path.resolve() == TECHNICAL_GRAPH_PATH.resolve():
        raise ContractValidationError(
            "El smoke no admite el gráfico técnico como salida de negocio."
        )
    html = output_path.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED_MARKERS if marker not in html]
    if missing:
        raise ContractValidationError(
            f"HTML Archify incompleto; faltan marcadores: {', '.join(missing)}."
        )
    if EXTERNAL_DEPENDENCY.search(html):
        raise ContractValidationError(
            "El HTML Archify contiene una dependencia de red externa."
        )

    handler = lambda *args, **kwargs: QuietHandler(
        *args, directory=str(output_path.parent), **kwargs
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/{output_path.name}"
        with contextlib.closing(urllib.request.urlopen(url, timeout=5)) as response:
            body = response.read().decode("utf-8")
            if response.status != 200 or REQUIRED_MARKERS[0] not in body:
                raise ContractValidationError(
                    "El servidor local no devolvió el workflow esperado."
                )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
