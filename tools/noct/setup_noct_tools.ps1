# Instala as 4 ferramentas Noct FORA do repositorio (licencas proibem redistribuir,
# e o repositorio vai para o GitHub). Pasta padrao: E:\game\noct-tools
#
# Uso (PowerShell, na pasta do repositorio):
#   powershell -ExecutionPolicy Bypass -File tools\noct\setup_noct_tools.ps1
#   powershell -ExecutionPolicy Bypass -File tools\noct\setup_noct_tools.ps1 -Downloads "E:\UsuariosSSD\Downloads" -Destino "E:\game\noct-tools"
#
# Precisa: Python 3.12 (comando py), Node.js 20+ (22 para o GamejamProject).
# Rodar de novo e seguro: so extrai o que ainda nao existe (use -Reextrair para forcar).

param(
    [string]$Downloads = "E:\UsuariosSSD\Downloads",
    [string]$Destino = "E:\game\noct-tools",
    [switch]$Reextrair,
    [switch]$SemDependencias
)

$ErrorActionPreference = "Stop"

$pacotes = @(
    @{ Zip = "noct-asset-forge-3d-bb-v2.zip"; Pasta = "forge3d";  Interno = "noct-asset-forge-3d-bb-v2" },
    @{ Zip = "noct-asset-forge-v2.5.zip";     Pasta = "forge2d";  Interno = "noct-asset-forge-v2.5" },
    @{ Zip = "Noct3DViewer-Pack.zip";         Pasta = "viewer3d"; Interno = $null },
    @{ Zip = "GamejamProject.zip";            Pasta = "gamejam";  Interno = "GamejamProject" }
)

New-Item -ItemType Directory -Force -Path $Destino | Out-Null

foreach ($p in $pacotes) {
    $zip = Join-Path $Downloads $p.Zip
    $alvo = Join-Path $Destino $p.Pasta
    if ((Test-Path $alvo) -and -not $Reextrair) {
        Write-Host "[noct] $($p.Pasta): ja existe, pulando extracao"
        continue
    }
    if (-not (Test-Path $zip)) { Write-Warning "[noct] nao achei $zip"; continue }
    $tmp = Join-Path $Destino ("_tmp_" + $p.Pasta)
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $origem = if ($p.Interno) { Join-Path $tmp $p.Interno } else { $tmp }
    if (Test-Path $alvo) { Remove-Item -Recurse -Force $alvo }
    Move-Item $origem $alvo
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    Write-Host "[noct] $($p.Pasta): extraido em $alvo"
}

if ($SemDependencias) { Write-Host "[noct] pronto (sem instalar dependencias)"; exit 0 }

# Forge 3D (Python 3.12 + Chromium do Playwright + validador glTF)
Push-Location (Join-Path $Destino "forge3d")
py -3.12 -m pip install -r requirements.txt
py -3.12 -m playwright install chromium
npm ci
py -3.12 -m Tools.forge doctor
Pop-Location

# Forge 2D (Node)
Push-Location (Join-Path $Destino "forge2d")
npm install
npx playwright install chromium
npm run doctor
Pop-Location

# GamejamProject (so o asset-kit tem dependencias)
Push-Location (Join-Path $Destino "gamejam\tools\asset-kit")
npm ci
Pop-Location

# Projetos do jogo dentro das ferramentas, semeados com as receitas versionadas no repositorio
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Push-Location (Join-Path $Destino "forge3d")
if (-not (Test-Path "projects\jogo_resgate\project.json")) {
    $fontes = Join-Path $repo "assets\source\forge3d"
    $ids = @(Get-ChildItem $fontes -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
    if ($ids.Count -gt 0) {
        py -3.12 -m Tools.forge project init projects/jogo_resgate --asset $ids[0]
        foreach ($id in $ids | Select-Object -Skip 1) { py -3.12 -m Tools.forge asset init projects/jogo_resgate --asset $id }
        foreach ($id in $ids) { Copy-Item -Recurse -Force (Join-Path $fontes "$id\*") "projects\jogo_resgate\scripts\$id\" }
        Write-Host "[noct] forge3d/projects/jogo_resgate criado com: $($ids -join ', ')"
    }
}
Pop-Location
Push-Location (Join-Path $Destino "forge2d")
if (-not (Test-Path "projects\jogo_resgate")) {
    npm run new-project -- jogo_resgate
    $fontes2d = Join-Path $repo "assets\source\forge2d"
    if (Test-Path $fontes2d) { Copy-Item -Recurse -Force (Join-Path $fontes2d "*") "projects\jogo_resgate\source\" }
    Write-Host "[noct] forge2d/projects/jogo_resgate criado"
}
Pop-Location

Write-Host ""
Write-Host "[noct] Tudo instalado em $Destino"
Write-Host "  Visualizador 3D (Forge 3D):  $Destino\forge3d\viewer.bat"
Write-Host "  Visualizador 2D (Forge 2D):  $Destino\forge2d\dev.bat  (abre localhost:5173)"
Write-Host "  Inspetor de FBX/Mixamo:      $Destino\viewer3d\Noct3DViewer.exe"
