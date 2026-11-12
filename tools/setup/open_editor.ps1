<#
.SYNOPSIS
  Abre o projeto JogoResgate no Unreal Editor sem depender da associação de arquivo .uproject.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\setup\open_editor.ps1
#>
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$UeRoot = if ($env:UE_ROOT) { $env:UE_ROOT } else { [Environment]::GetEnvironmentVariable("UE_ROOT", "User") }
if (-not $UeRoot) { Write-Host "Defina UE_ROOT (ex.: E:\UE_5.8)" -ForegroundColor Red; exit 1 }
$Editor = Join-Path $UeRoot "Engine\Binaries\Win64\UnrealEditor.exe"
if (-not (Test-Path $Editor)) { Write-Host "Editor não encontrado: $Editor" -ForegroundColor Red; exit 1 }
Start-Process $Editor -ArgumentList "`"$RepoRoot\unreal\JogoResgate\JogoResgate.uproject`""
