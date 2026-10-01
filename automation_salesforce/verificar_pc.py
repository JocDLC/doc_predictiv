"""Verificacion de una PC nueva para el Documentador Predictivo.

Archivo autosuficiente: no necesita la carpeta del proyecto. Comprueba lo que el
bot requiere en cada PC del equipo y deja un reporte de texto en el Escritorio.
No lee ni escribe datos de clientes; solo informacion tecnica del equipo.

Uso (PowerShell o CMD, desde la carpeta donde este el archivo):
    python verificar_pc.py
"""

from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import winreg
from pathlib import Path

SALESFORCE_URL = "https://renaultarca.lightning.force.com"
DEBUG_PORT = 9223  # distinto del 9222 real para no chocar con un navegador ya abierto
UI_PORT = 8765
EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Edge\Application\msedge.exe"),
]

REPORT: list[str] = []


def log(status: str, check: str, detail: str = "") -> None:
    line = f"[{status:5}] {check}" + (f" -> {detail}" if detail else "")
    print(line)
    REPORT.append(line)


def check_python() -> None:
    version = sys.version_info
    ok = version >= (3, 10)
    log(
        "OK" if ok else "FALLO",
        "Python >= 3.10",
        f"{platform.python_version()} ({'64 bits' if sys.maxsize > 2**32 else '32 bits'}) en {sys.executable}",
    )
    if "WindowsApps" in sys.executable or "PythonSoftwareFoundation" in sys.executable:
        log(
            "AVISO",
            "Python instalado desde Microsoft Store",
            "funciona, pero el paquete portable evitara esta dependencia",
        )


def check_pip_and_selenium() -> None:
    result = subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        log("FALLO", "pip disponible", result.stderr.strip().splitlines()[-1:] or "sin detalle")
        return
    log("OK", "pip disponible", result.stdout.strip())
    try:
        import selenium  # noqa: F401

        log("OK", "selenium ya instalado", getattr(selenium, "__version__", "?"))
        return
    except ImportError:
        pass
    print("       Instalando selenium (prueba el proxy corporativo, puede tardar 1-2 min)...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "selenium", "--quiet", "--disable-pip-version-check"],
            capture_output=True,
            text=True,
            timeout=240,
        )
    except subprocess.TimeoutExpired:
        log("FALLO", "pip install selenium (proxy)", "se agoto el tiempo: el proxy probablemente bloquea PyPI")
        return
    if result.returncode == 0:
        log("OK", "pip install selenium (proxy permite PyPI)")
    else:
        tail = (result.stderr.strip().splitlines() or ["sin detalle"])[-1]
        log("FALLO", "pip install selenium (proxy)", tail[:200])


def find_edge() -> str | None:
    for candidate in EDGE_CANDIDATES:
        if candidate and Path(candidate).is_file():
            return candidate
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"
        ) as key:
            path, _ = winreg.QueryValueEx(key, None)
            return path if Path(path).is_file() else None
    except OSError:
        return None


def edge_version(edge_path: str) -> str:
    app_dir = Path(edge_path).parent
    versions = sorted((p.name for p in app_dir.iterdir() if p.is_dir() and p.name[0].isdigit()), reverse=True)
    return versions[0] if versions else "desconocida"


def check_edge() -> str | None:
    edge = find_edge()
    if not edge:
        log("FALLO", "Microsoft Edge instalado", "no se encontro msedge.exe")
        return None
    log("OK", "Microsoft Edge instalado", f"version {edge_version(edge)}")
    return edge


def read_policy(hive, name: str):
    try:
        with winreg.OpenKey(hive, r"SOFTWARE\Policies\Microsoft\Edge") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except OSError:
        return None


def check_edge_policies() -> None:
    findings = []
    for hive_name, hive in (("HKLM", winreg.HKEY_LOCAL_MACHINE), ("HKCU", winreg.HKEY_CURRENT_USER)):
        for policy in ("RemoteDebuggingAllowed", "DeveloperToolsAvailability", "UserDataDir"):
            value = read_policy(hive, policy)
            if value is not None:
                findings.append(f"{hive_name}\\{policy}={value}")
    blocked = any("RemoteDebuggingAllowed=0" in f for f in findings)
    if blocked:
        log("FALLO", "Politica de Edge permite depuracion remota", "; ".join(findings))
    elif findings:
        log("AVISO", "Politicas de Edge presentes (revisar)", "; ".join(findings))
    else:
        log("OK", "Politicas de Edge", "sin restricciones de depuracion remota")


def check_local_dirs() -> None:
    base = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "RenaultPredictivo" / "_prueba"
    try:
        base.mkdir(parents=True, exist_ok=True)
        (base / "test.txt").write_text("ok", encoding="utf-8")
        shutil.rmtree(base, ignore_errors=True)
        log("OK", "Escritura en %LOCALAPPDATA% (perfil del navegador)", str(base.parent))
    except OSError as error:
        log("FALLO", "Escritura en %LOCALAPPDATA%", str(error))


def check_port(port: int, label: str) -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))
        log("OK", f"Puerto local {port} libre ({label})")
    except OSError as error:
        log("AVISO", f"Puerto local {port} ({label})", f"ocupado o bloqueado: {error}")


def check_salesforce_reachable() -> None:
    try:
        with urllib.request.urlopen(SALESFORCE_URL, timeout=20) as response:
            log("OK", "Acceso de red a Salesforce", f"HTTP {response.status}")
    except urllib.error.HTTPError as error:
        log("OK", "Acceso de red a Salesforce", f"HTTP {error.code} (responde; el login se hace a mano)")
    except Exception as error:  # noqa: BLE001 - diagnostico: cualquier fallo de red interesa
        log("FALLO", "Acceso de red a Salesforce", str(error)[:200])


def wait_for_debugger(port: int, seconds: int = 25) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2):
                return True
        except Exception:  # noqa: BLE001
            time.sleep(1)
    return False


def check_edge_remote_debugging(edge: str) -> None:
    profile = Path(tempfile.mkdtemp(prefix="edge_prueba_"))
    process = subprocess.Popen(
        [
            edge,
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--new-window",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if wait_for_debugger(DEBUG_PORT):
            log("OK", "Edge acepta depuracion remota local (lo que usa el bot)")
            check_selenium_attach()
        else:
            log(
                "FALLO",
                "Edge acepta depuracion remota local",
                "no respondio en el puerto; posible politica corporativa",
            )
    finally:
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(1)
        shutil.rmtree(profile, ignore_errors=True)


def check_selenium_attach() -> None:
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
    except ImportError:
        log("AVISO", "Selenium se adjunta a Edge", "omitido: selenium no instalado")
        return
    print("       Probando Selenium + descarga del driver de Edge (puede tardar 1 min)...")
    try:
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
        driver = webdriver.Edge(options=options)
        title = driver.title
        log(
            "OK",
            "Selenium se adjunta a Edge y el driver se descargo",
            f"pestaña activa leida ({len(title)} caracteres de titulo)",
        )
        try:
            driver.quit()
        except Exception:  # noqa: BLE001
            pass
    except Exception as error:  # noqa: BLE001
        log("FALLO", "Selenium se adjunta a Edge (driver msedgedriver)", str(error).splitlines()[0][:220])


def check_powershell_policy() -> None:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-ExecutionPolicy"], capture_output=True, text=True
    )
    log("INFO", "Politica de scripts PowerShell", result.stdout.strip() or "desconocida")


def save_report() -> Path:
    desktop = Path(os.environ.get("USERPROFILE", ".")) / "Desktop"
    target_dir = desktop if desktop.is_dir() else Path.cwd()
    target = target_dir / "reporte_verificacion_pc.txt"
    header = [
        "Reporte de verificacion - Documentador Predictivo",
        f"Equipo: {platform.node()} | {platform.platform()}",
        f"Fecha: {time.strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    target.write_text("\n".join(header + REPORT) + "\n", encoding="utf-8")
    return target


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    print("=== Verificacion de PC para el Documentador Predictivo ===\n")
    check_python()
    check_pip_and_selenium()
    edge = check_edge()
    check_edge_policies()
    check_local_dirs()
    check_port(UI_PORT, "servidor de la UI")
    check_port(DEBUG_PORT, "depuracion del navegador")
    check_salesforce_reachable()
    check_powershell_policy()
    if edge:
        check_edge_remote_debugging(edge)
    report = save_report()
    failures = sum(1 for line in REPORT if line.startswith("[FALLO"))
    print(f"\nResultado: {failures} fallo(s). Reporte guardado en:\n  {report}")
    print("Envia ese archivo a quien administra la app. No contiene datos de clientes.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
