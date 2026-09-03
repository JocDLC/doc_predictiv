# Verifica que la maquina tenga todo el harness instalado y configurado.
# Se puede ejecutar en cualquier momento: ./scripts/verify-setup.ps1
# Sale con codigo 1 si falta algo, indicando exactamente que hacer.

$script:failures = 0

function Test-Requirement {
    param([string]$Name, [scriptblock]$Check, [string]$FixHint)
    if (& $Check) {
        Write-Host "[OK]    $Name" -ForegroundColor Green
    } else {
        Write-Host "[FALTA] $Name" -ForegroundColor Red
        Write-Host "        Solucion: $FixHint" -ForegroundColor Yellow
        $script:failures++
    }
}

$npmBin = Join-Path $env:APPDATA "npm"
$mcpFile = Join-Path $env:USERPROFILE ".gemini\antigravity\mcp_config.json"

Write-Host ""
Write-Host "=== Verificacion del harness de desarrollo ===" -ForegroundColor Cyan
Write-Host ""

Test-Requirement "Node.js 20.19.0+" `
    { (Get-Command node -ErrorAction SilentlyContinue) -and ([version]((node -v) -replace 'v','') -ge [version]'20.19.0') } `
    "Instala Node.js 20.19.0+ desde https://nodejs.org"

Test-Requirement "Python 3.10+" `
    { (Get-Command python -ErrorAction SilentlyContinue) -or (Get-Command py -ErrorAction SilentlyContinue) } `
    "Instala Python 3.10+ desde https://python.org"

Test-Requirement "Git" `
    { Get-Command git -ErrorAction SilentlyContinue } `
    "Instala Git desde https://git-scm.com"

Test-Requirement "OpenSpec CLI 1.6.0" `
    { (Get-Command openspec -ErrorAction SilentlyContinue) -or (Test-Path (Join-Path $npmBin "openspec.cmd")) } `
    "Ejecuta: npm install -g @fission-ai/openspec@1.6.0"

Test-Requirement "Graphify CLI 0.10.0" `
    { (Get-Command graphify -ErrorAction SilentlyContinue) -or (Test-Path (Join-Path $env:USERPROFILE ".local\bin\graphify.exe")) } `
    "Ejecuta: pipx install graphifyy==0.10.0 (o corre ./scripts/bootstrap.ps1)"

Test-Requirement "Skill de Graphify para agentes (~/.agents/skills)" `
    { Test-Path (Join-Path $env:USERPROFILE ".agents\skills\graphify\SKILL.md") } `
    "Ejecuta: graphify install"

Test-Requirement "uv (requerido por el servidor MCP de Graphify)" `
    { (Get-Command uv -ErrorAction SilentlyContinue) -or (Test-Path (Join-Path $env:USERPROFILE ".local\bin\uv.exe")) } `
    "Ejecuta: pipx install uv"

Test-Requirement "Servidor MCP 'graphify' en Antigravity ($mcpFile)" `
    { (Test-Path $mcpFile) -and ((Get-Content $mcpFile -Raw | ConvertFrom-Json).mcpServers.PSObject.Properties["graphify"]) } `
    "Corre ./scripts/bootstrap.ps1 (agrega el bloque automaticamente sin pisar otros servidores)"

Write-Host ""
if ($script:failures -eq 0) {
    Write-Host "Todo listo. Esta maquina tiene el harness completo." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Faltan $script:failures requisito(s). Aplica las soluciones indicadas y vuelve a correr este script." -ForegroundColor Red
    exit 1
}
