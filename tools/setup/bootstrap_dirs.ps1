<#
.SYNOPSIS
  Move _bootstrap\claude -> .claude e _bootstrap\github -> .github (uma única vez).
.DESCRIPTION
  As pastas .claude e .github foram entregues em _bootstrap\ porque a ferramenta remota
  que criou o repositório não pode escrever em pastas protegidas. Este script só move
  arquivos dentro do próprio repositório. Não sobrescreve arquivos existentes.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\setup\bootstrap_dirs.ps1
#>
$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Pairs = @(
    @{ From = "_bootstrap\claude"; To = ".claude" },
    @{ From = "_bootstrap\github"; To = ".github" }
)
foreach ($p in $Pairs) {
    $src = Join-Path $RepoRoot $p.From
    $dst = Join-Path $RepoRoot $p.To
    if (-not (Test-Path $src)) { Write-Host "[--] $($p.From) não existe (já instalado?)"; continue }
    Get-ChildItem $src -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($src.Length).TrimStart('\')
        $target = Join-Path $dst $rel
        if (Test-Path $target) { Write-Host "[PULADO] $($p.To)\$rel já existe" -ForegroundColor Yellow; return }
        New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
        Move-Item $_.FullName $target
    }
    Write-Host "[OK] $($p.From) -> $($p.To)" -ForegroundColor Green
}
$leftover = Get-ChildItem (Join-Path $RepoRoot "_bootstrap") -Recurse -File -ErrorAction SilentlyContinue
if (-not $leftover) {
    Remove-Item (Join-Path $RepoRoot "_bootstrap") -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] _bootstrap removida" -ForegroundColor Green
} else {
    Write-Host "[ATENÇÃO] Restaram arquivos em _bootstrap (conflitos acima). Revise manualmente." -ForegroundColor Yellow
}
