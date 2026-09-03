# One-liner install: clona el template y corre bootstrap
# Uso:
#   iwr -useb https://raw.githubusercontent.com/JocDLC/dev-harness-template/main/scripts/install.ps1 | iex

param (
    [string]$TargetDir = "$env:USERPROFILE\dev-harness-template"
)

$repo = "https://github.com/JocDLC/dev-harness-template.git"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git no esta instalado. Instalalo desde https://git-scm.com"
    exit 1
}

if (Test-Path $TargetDir) {
    Write-Error "El directorio $TargetDir ya existe. Borralo o elige otro."
    exit 1
}

Write-Host "==> Clonando template..."
git clone $repo $TargetDir

Write-Host "==> Corriendo bootstrap..."
& "$TargetDir\scripts\bootstrap.ps1"

Write-Host "==> Corriendo setup-project..."
& "$TargetDir\scripts\setup-project.ps1"

Write-Host "Listo. Entra en $TargetDir y abrelo en tu IDE."
