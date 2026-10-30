"""Arma dist/DocumentadorPredictivo_v<version>.zip desde la fuente del repo.

Uso:  python packaging/build_zip.py [--sync-dist]

--sync-dist copia los mismos archivos a dist/DocumentadorPredictivo (la
instalacion local) sin tocar config.json, ui_output, logs ni queues.
"""

import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGING = ROOT / "packaging"
DIST = ROOT / "dist" / "DocumentadorPredictivo"
PYTHON_SRC = DIST / "python"

ROOT_FILES = ["INICIAR.bat", "LEEME.txt", "RECOGER_DIAGNOSTICO.bat", "VERIFICAR_PC.bat"]

REQUIRED_APP_PY = [
    "ui_server",
    "server_guardian",
    "open_persistent_browser",
    "verificar_pc",
    "lead_monitor",
    "browser_factory",
]

FORBIDDEN_FRAGMENTS = [
    "ui_output/",
    "queues/",
    "logs/",
    "screenshots/",
    "perfil/",
    "tests/",
    "__pycache__",
    "bot_session",
    "monitor_state",
    ".resultado",
    "_reset_backup",
]


def app_version() -> str:
    html = (ROOT / "documentador_predictivo.html").read_text(encoding="utf-8")
    match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', html)
    if not match:
        sys.exit("ERROR: no se encontro APP_VERSION en documentador_predictivo.html")
    return match.group(1)


def production_py_files() -> list[Path]:
    src = ROOT / "automation_salesforce"
    return sorted(
        p
        for p in src.glob("*.py")
        if p.name != "harness.py" and not p.name.startswith("test_")
    )


def python_portable_files() -> list[Path]:
    if not PYTHON_SRC.is_dir():
        sys.exit(
            f"ERROR: falta {PYTHON_SRC} (runtime portable). "
            "No se puede armar el paquete sin el Python portable."
        )
    files = []
    for p in sorted(PYTHON_SRC.rglob("*")):
        if not p.is_file():
            continue
        if "__pycache__" in p.parts or p.suffix == ".pyc":
            continue
        files.append(p)
    return files


def build_zip(version: str) -> Path:
    zip_path = ROOT / "dist" / f"DocumentadorPredictivo_v{version}.zip"
    if zip_path.exists():
        zip_path.unlink()

    entries: dict[str, Path] = {}
    for name in ROOT_FILES:
        entries[name] = PACKAGING / name
    entries["CHANGELOG.md"] = ROOT / "CHANGELOG.md"
    entries["app/CHANGELOG.md"] = ROOT / "CHANGELOG.md"
    entries["app/documentador_predictivo.html"] = ROOT / "documentador_predictivo.html"
    for py in production_py_files():
        entries[f"app/automation_salesforce/{py.name}"] = py
    entries["app/automation_salesforce/requirements.txt"] = (
        ROOT / "automation_salesforce" / "requirements.txt"
    )
    entries["app/automation_salesforce/config.json"] = (
        ROOT / "automation_salesforce" / "config.example.json"
    )
    for p in python_portable_files():
        entries[f"python/{p.relative_to(PYTHON_SRC).as_posix()}"] = p

    missing = [name for name, src in entries.items() if not src.is_file()]
    if missing:
        sys.exit("ERROR: faltan archivos fuente: " + ", ".join(missing))

    names = list(entries)
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        sys.exit("ERROR: entradas duplicadas: " + ", ".join(sorted(dupes)))

    required = (
        ROOT_FILES
        + ["CHANGELOG.md", "app/CHANGELOG.md", "app/documentador_predictivo.html"]
        + [f"app/automation_salesforce/{m}.py" for m in REQUIRED_APP_PY]
        + [
            "app/automation_salesforce/requirements.txt",
            "app/automation_salesforce/config.json",
            "python/python.exe",
            "python/python312._pth",
        ]
    )
    absent = [n for n in required if n not in entries]
    if absent:
        sys.exit("ERROR: entradas requeridas ausentes: " + ", ".join(absent))

    bad = [
        n
        for n in entries
        if not n.startswith("python/")
        and any(frag in n for frag in FORBIDDEN_FRAGMENTS)
    ]
    if bad:
        sys.exit("ERROR: entradas prohibidas en el paquete: " + ", ".join(bad[:10]))

    html = (ROOT / "documentador_predictivo.html").read_text(encoding="utf-8")
    if f'APP_VERSION = "{version}"' not in html:
        sys.exit(f"ERROR: APP_VERSION del html no es {version}")

    json.loads(entries["app/automation_salesforce/config.json"].read_text(encoding="utf-8"))

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for arcname, src in entries.items():
            zf.write(src, arcname)
    with zipfile.ZipFile(zip_path) as zf:
        bad_entry = zf.testzip()
        if bad_entry is not None:
            sys.exit(f"ERROR: testzip detecto un archivo corrupto: {bad_entry}")

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"ZIP: {zip_path}")
    print(f"Entradas: {len(entries)} | Tamano: {size_mb:.1f} MB | Version: {version}")
    return zip_path


def sync_dist() -> None:
    for name in ROOT_FILES:
        shutil.copy2(PACKAGING / name, DIST / name)
    shutil.copy2(ROOT / "CHANGELOG.md", DIST / "CHANGELOG.md")
    shutil.copy2(ROOT / "CHANGELOG.md", DIST / "app" / "CHANGELOG.md")
    shutil.copy2(
        ROOT / "documentador_predictivo.html",
        DIST / "app" / "documentador_predictivo.html",
    )
    botdir = DIST / "app" / "automation_salesforce"
    for py in production_py_files():
        shutil.copy2(py, botdir / py.name)
    print(f"Sync dist: {DIST} actualizado (config.json, ui_output, logs, queues intactos)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync-dist", action="store_true")
    args = parser.parse_args()
    version = app_version()
    build_zip(version)
    if args.sync_dist:
        sync_dist()


if __name__ == "__main__":
    main()
