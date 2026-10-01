"""Smoke local y sin red del HTML de contratos."""

from __future__ import annotations

import contextlib
import http.server
import threading
import urllib.request
from pathlib import Path

from .paths import OUTPUT_PATH, TECHNICAL_GRAPH_PATH
from .validator import ContractValidationError

REQUIRED_MARKERS = (
    "Contratos de negocio",
    'id="business-contract-data"',
    'id="contract-dialog"',
    'id="theme-toggle"',
    'id="presentation-toggle"',
    "Cargar base de Leads",
    "Guardar y verificar la documentación",
)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def smoke_html(output_path: Path = OUTPUT_PATH) -> None:
    if output_path.resolve() == TECHNICAL_GRAPH_PATH.resolve():
        raise ContractValidationError(
            "El smoke no admite el gráfico técnico como salida de negocio."
        )
    html = output_path.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED_MARKERS if marker not in html]
    if missing:
        raise ContractValidationError(
            f"HTML incompleto; faltan marcadores: {', '.join(missing)}."
        )
    if any(
        token in html.lower()
        for token in ("https://", "http://", 'src="//', 'href="//')
    ):
        raise ContractValidationError(
            "El HTML contiene una dependencia de red externa."
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
            if response.status != 200 or "Contratos de negocio" not in body:
                raise ContractValidationError(
                    "El servidor local no devolvió el artefacto esperado."
                )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
