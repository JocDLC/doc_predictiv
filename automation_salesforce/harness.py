"""Comandos reproducibles del arnés de calidad.

Este módulo solo orquesta herramientas locales. No abre navegadores, no accede a
Salesforce y no ejecuta runners productivos.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parent

LAYER_MODULES: dict[str, tuple[str, ...]] = {
    "unit": ("discover", "-s", "tests", "-v"),
    "contract": (
        "tests.test_corrections",
        "tests.test_productivity_metrics",
        "tests.test_queue_loader",
        "tests.test_snapshot_store",
        "-v",
    ),
    "integration-local": (
        "tests.test_browser_factory",
        "tests.test_run_document_queue",
        "tests.test_ui_server",
        "-v",
    ),
    "security-privacy": (
        "tests.test_local_audit",
        "tests.test_local_report",
        "tests.test_run_comment_read_only",
        "tests.test_run_report_read_only",
        "-v",
    ),
    "browser-local": ("tests.test_harness_smoke", "-v"),
}

COVERAGE_EXCLUDED_FILES = frozenset({"harness.py"})
CRITICAL_COVERAGE_FILES = frozenset(
    {
        "comment_writer.py",
        "correction_loader.py",
        "local_audit.py",
        "local_report.py",
        "productivity_metrics.py",
        "queue_loader.py",
        "run_corrections.py",
        "salesforce_session.py",
        "snapshot_store.py",
        "ui_server.py",
    }
)


def run(command: Sequence[str], *, cwd: Path = ROOT) -> None:
    """Ejecuta un comando visible y detiene el arnés ante el primer fallo."""

    rendered = subprocess.list2cmdline(command)
    print(f"\n[harness] {rendered}", flush=True)
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode:
        raise SystemExit(completed.returncode)


def python_module(module: str, *arguments: str) -> list[str]:
    return [sys.executable, "-m", module, *arguments]


def resolve_executable(name: str) -> str:
    """Resuelve shims `.cmd`/`.ps1` y binarios POSIX sin invocar un shell."""

    executable = shutil.which(name)
    if executable is None:
        raise SystemExit(f"No se encontró el ejecutable requerido: {name}")
    return executable


def production_python_files() -> list[str]:
    files = sorted(path.name for path in ROOT.glob("*.py"))
    return [*files, "tests"]


def coverage_python_files() -> set[str]:
    """Devuelve todos los módulos productivos que deben aparecer en cobertura."""

    return {path.name for path in ROOT.glob("*.py")} - COVERAGE_EXCLUDED_FILES


def verify_coverage_scope(report_path: Path) -> None:
    """Impide que un reporte de cobertura omita módulos productivos."""

    root = ET.parse(report_path).getroot()
    reported_files = {Path(element.attrib["filename"]).name for element in root.findall(".//class")}
    missing_files = coverage_python_files() - reported_files
    if not missing_files:
        print(f"[harness] Cobertura incluye {len(reported_files)} módulos productivos.", flush=True)
        return

    missing_critical = missing_files & CRITICAL_COVERAGE_FILES
    details = f"Módulos productivos omitidos en cobertura: {', '.join(sorted(missing_files))}."
    if missing_critical:
        details += f" Críticos omitidos: {', '.join(sorted(missing_critical))}."
    raise SystemExit(details)


def run_layer(layer: str) -> None:
    run(python_module("unittest", *LAYER_MODULES[layer]))


def run_coverage() -> None:
    run(python_module("coverage", "erase"))
    run(python_module("coverage", "run", "-m", "unittest", "discover", "-s", "tests", "-v"))
    run(python_module("coverage", "report"))
    report_path = ROOT / "coverage.xml"
    run(python_module("coverage", "xml", "-o", str(report_path)))
    verify_coverage_scope(report_path)


def run_business_contract_graph() -> None:
    """Verifica el artefacto local sin abrir Salesforce ni usar red externa."""

    package = "business_contract_graph"
    run(python_module("ruff", "format", "--check", package), cwd=REPOSITORY_ROOT)
    run(python_module("ruff", "check", package), cwd=REPOSITORY_ROOT)
    run(python_module("compileall", "-q", package), cwd=REPOSITORY_ROOT)
    run(
        python_module("unittest", "discover", "-s", f"{package}/tests", "-v"),
        cwd=REPOSITORY_ROOT,
    )
    # CI valida y genera el candidato determinista. La finalización visual usa
    # Archify localmente y deja recibos que se comprueban con el comando verify.
    run(python_module(package, "validate"), cwd=REPOSITORY_ROOT)
    run(python_module(package, "candidate"), cwd=REPOSITORY_ROOT)


def run_tdd_red(test_id: str) -> None:
    """Verifica que el test nuevo falle antes de implementar (fase RED)."""

    completed = subprocess.run(
        python_module("unittest", test_id, "-v"),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="", flush=True)
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr, flush=True)
    if completed.returncode == 0:
        raise SystemExit("[tdd-red] El test pasa: no prueba comportamiento nuevo. Ajustá el test antes de implementar.")
    output = completed.stdout + completed.stderr
    if "failures=" in output:
        print("[tdd-red] OK: el test falla como se esperaba. Pasá a GREEN.")
    else:
        print(
            "[tdd-red] AVISO: el test falla por error (import/nombre/sintaxis), "
            "no por aserción. Verificá que falle por la funcionalidad faltante."
        )


def run_tdd_green(test_id: str) -> None:
    """Verifica que el test pase y que la suite y el lint sigan en verde."""

    run(python_module("unittest", test_id, "-v"))
    run_layer("unit")
    run(python_module("ruff", "check", "."))
    print("[tdd-green] OK: test, suite y lint en verde.")


def run_named_command(command: str, test_id: str | None = None) -> None:
    if command == "tdd-red":
        run_tdd_red(test_id)
    elif command == "tdd-green":
        run_tdd_green(test_id)
    elif command == "format-check":
        run(python_module("ruff", "format", "--check", "."))
    elif command == "lint":
        run(python_module("ruff", "check", "."))
    elif command == "compile":
        run(python_module("compileall", "-q", *production_python_files()))
    elif command == "test":
        run_layer("unit")
    elif command == "coverage":
        run_coverage()
    elif command in LAYER_MODULES:
        run_layer(command)
    elif command == "business-contracts":
        run_business_contract_graph()
    elif command == "verify":
        for step in ("format-check", "lint", "compile", "coverage"):
            run_named_command(step)
        run_business_contract_graph()
        run([resolve_executable("openspec"), "validate", "--changes"], cwd=REPOSITORY_ROOT)
    else:  # protegido también por argparse; mantiene segura la API programática.
        raise ValueError(f"Comando de arnés desconocido: {command}")


TDD_COMMANDS = ("tdd-red", "tdd-green")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    choices = (
        "format-check",
        "lint",
        "compile",
        "test",
        "coverage",
        "business-contracts",
        "verify",
        *TDD_COMMANDS,
        *LAYER_MODULES,
    )
    parser = argparse.ArgumentParser(description="Arnés no destructivo de automation_salesforce")
    parser.add_argument("command", choices=choices)
    parser.add_argument("test_id", nargs="?")
    args = parser.parse_args(argv)
    if args.command in TDD_COMMANDS and not args.test_id:
        parser.error(f"el comando {args.command} requiere un test_id (ej. tests.test_modulo)")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    run_named_command(args.command, args.test_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
