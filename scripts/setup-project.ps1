# Setup por proyecto (ejecutar una vez al crear un proyecto desde la plantilla).
# Inicializa OpenSpec para todos los IDEs y construye el grafo inicial con Graphify.

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

$openspecCommand = Get-Command openspec -ErrorAction SilentlyContinue
$openspec = if ($openspecCommand) { $openspecCommand.Source } else { $null }
if (-not $openspec) {
    $npmBin = Join-Path $env:APPDATA "npm"
    $openspec = Join-Path $npmBin "openspec.cmd"
}
if (-not (Test-Path $openspec)) {
    Write-Error "OpenSpec no esta instalado. Corre primero scripts/bootstrap.ps1"
    exit 1
}

Write-Host "==> Inicializando OpenSpec para Antigravity, Windsurf y Codex..." -ForegroundColor Cyan
& $openspec init $projectRoot --tools 'antigravity,windsurf,codex'

Write-Host "==> Construyendo grafo inicial con Graphify..." -ForegroundColor Cyan
& graphify update $projectRoot

Write-Host ""
Write-Host "Listo. Los archivos generados (openspec/, AGENTS.md, .windsurf/, etc.)" -ForegroundColor Green
Write-Host "deben commitearse al repo para que esten disponibles en todos tus computadores." -ForegroundColor Green
