"""CLI del workflow Archify de contratos de negocio."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from .generator import (
    generate_candidate,
    publish_archify_artifact,
    verify_archify_artifacts,
)
from .paths import PUBLISHED_OUTPUT_PATH, SOURCE_PATH
from .smoke import smoke_html
from .validator import ContractValidationError, load_contracts, validate_contracts


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Workflow de contratos de negocio")
    parser.add_argument(
        "command", choices=("validate", "candidate", "publish", "smoke", "verify")
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command in {"validate", "verify"}:
            validate_contracts(
                load_contracts(SOURCE_PATH),
                published_output_path=PUBLISHED_OUTPUT_PATH,
            )
            print("[business-contracts] Contratos válidos.")
        if args.command in {"candidate", "verify"}:
            candidate = generate_candidate()
            print(f"[business-contracts] Candidato Archify generado: {candidate}")
        if args.command == "publish":
            output = publish_archify_artifact()
            print(f"[business-contracts] Workflow publicado: {output}")
        if args.command == "verify":
            verify_archify_artifacts()
            print("[business-contracts] Recibos Archify válidos.")
        if args.command in {"smoke", "verify"}:
            smoke_html()
            print("[business-contracts] Smoke local correcto.")
    except (ContractValidationError, OSError, ValueError) as exc:
        print(f"[business-contracts] ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
