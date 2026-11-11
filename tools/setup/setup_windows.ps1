<#
.SYNOPSIS
  Prepara o repositório no Windows sem instalar software de terceiros.
.DESCRIPTION
  1. Verifica Git, Git LFS e Python.
  2. Configura Git LFS e hooks do repositório (.githooks).
  3. Cria .venv e instala tools/requirements.txt.
  4. Roda testes rápidos e check_environment.py.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\setup\setup_windows.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\setup\setup_windows.ps1 -SkipTests
#>
param(
    [switch]$SkipTests,
    [string]$UeRoot = $env:UE_ROOT
)
$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

function Require-Command($Name, $Hint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Host "[FALTA] $Name. $Hint" -ForegroundColor Red
        return $false
    }
    Write-Host "[OK]    $Name" -ForegroundColor Green
    return $true
}

if (Test-Path (Join-Path $RepoRoot "_bootstrap")) {
    & (Join-Path $PSScriptRoot "bootstrap_dirs.ps1")
}

$ok = $true
$ok = (Require-Command git "Instale Git for Windows: https://git-scm.com/download/win") -and $ok
$ok = (Require-Command python "Instale Python 3.11+: https://www.python.org/downloads/") -and $ok
if (-not $ok) { exit 1 }

git lfs version | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "[FALTA] Git LFS (vem com o Git for Windows recente)" -ForegroundColor Red; exit 1 }
git lfs install --local | Out-Null
git config core.hooksPath .githooks
Write-Host "[OK]    Git LFS e hooks configurados" -ForegroundColor Green

if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
& .\.venv\Scripts\python.exe -m pip install -r tools\requirements.txt
Write-Host "[OK]    .venv pronto (ative com .\.venv\Scripts\Activate.ps1)" -ForegroundColor Green

if (-not $SkipTests) {
    & .\.venv\Scripts\python.exe -m pytest tests\python -q
    if ($LASTEXITCODE -ne 0) { Write-Host "[ERRO]  testes falharam" -ForegroundColor Red }
}

$envArgs = @("tools\setup\check_environment.py", "--json", "reports\environment.json")
if ($UeRoot) { $envArgs += @("--ue-root", $UeRoot) }
& .\.venv\Scripts\python.exe @envArgs
Write-Host "Relatório: reports\environment.json (ignorado pelo Git). Cole o resultado em docs\setup\ENVIRONMENT_REPORT.md se quiser registrar."
