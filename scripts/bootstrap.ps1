# Setup por maquina (ejecutar una sola vez en cada computador).
# Instala las herramientas globales: OpenSpec CLI y el skill Graphify.

$ErrorActionPreference = "Stop"

function Assert-Command {
    param([string]$Name, [string]$InstallHint)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Error "'$Name' no esta instalado. $InstallHint"
    }
}

function Get-PythonCommand {
    foreach ($candidate in @("python", "py")) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) { return $candidate }
    }
    Write-Error "Python no esta instalado. Instala Python 3.10+ desde https://python.org"
}

Write-Host "==> Verificando requisitos..." -ForegroundColor Cyan
Assert-Command "node" "Instala Node.js 18+ desde https://nodejs.org"
Assert-Command "git" "Instala Git desde https://git-scm.com"
$python = Get-PythonCommand

$openSpecVersion = "1.6.0"
$graphifyVersion = "0.10.0"
$uvVersion = "latest"

Write-Host "==> Instalando OpenSpec CLI (global) v$openSpecVersion..." -ForegroundColor Cyan
npm install -g "@fission-ai/openspec@$openSpecVersion"

Write-Host "==> Instalando Graphify v$graphifyVersion (via pipx para manejar el PATH)..." -ForegroundColor Cyan
& $python -m pip install --user pipx
& $python -m pipx ensurepath
& $python -m pipx install "graphifyy==$graphifyVersion"

Write-Host "==> Instalando el skill de Graphify para los agentes..." -ForegroundColor Cyan
& $python -m pipx run --spec "graphifyy==$graphifyVersion" graphify install

Write-Host "==> Instalando uv (necesario para el servidor MCP de Graphify)..." -ForegroundColor Cyan
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    if ($uvVersion -eq "latest") {
        & $python -m pipx install uv
    } else {
        & $python -m pipx install "uv==$uvVersion"
    }
}

Write-Host "==> Configurando el servidor MCP de Graphify en Antigravity..." -ForegroundColor Cyan
$mcpDir = Join-Path $env:USERPROFILE ".gemini\antigravity"
$mcpFile = Join-Path $mcpDir "mcp_config.json"
New-Item -ItemType Directory -Force -Path $mcpDir | Out-Null

if (Test-Path $mcpFile) {
    $config = Get-Content $mcpFile -Raw | ConvertFrom-Json
} else {
    $config = [PSCustomObject]@{}
}
if (-not $config.PSObject.Properties["mcpServers"]) {
    $config | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue ([PSCustomObject]@{})
}

if ($config.mcpServers.PSObject.Properties["graphify"]) {
    Write-Host "El servidor MCP 'graphify' ya estaba configurado. Sin cambios." -ForegroundColor Yellow
} else {
    $graphifyServer = [PSCustomObject]@{
        command = "uv"
        args    = @("run", "--with", "graphifyy", "--with", "mcp", "-m", "graphify.serve", '${workspace.path}/graphify-out/graph.json')
    }
    $config.mcpServers | Add-Member -NotePropertyName "graphify" -NotePropertyValue $graphifyServer
    $config | ConvertTo-Json -Depth 10 | Set-Content $mcpFile -Encoding UTF8
    Write-Host "Servidor MCP 'graphify' agregado a $mcpFile" -ForegroundColor Green
}

Write-Host ""
Write-Host "==> Verificacion final del harness..." -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "verify-setup.ps1")
