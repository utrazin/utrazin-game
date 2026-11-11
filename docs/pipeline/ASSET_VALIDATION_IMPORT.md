# Validação e importação de assets

## Antes do export (Blender)

```powershell
blender -b <arquivo.blend> --python tools\blender\validate_scene.py -- --config tools\blender\validation_config.json --report reports\<ID>_scene.json
blender -b <arquivo.blend> --python tools\blender\validate_rig.py   -- --required-bones tools\blender\ue5_required_bones.txt --report reports\<ID>_rig.json
```

Verifica: nomes, duplicados, escala/transformações aplicadas, geometria inválida (faces degeneradas, n-gons acima do limite), UVs ausentes, materiais vazios, limites de triângulos, ossos obrigatórios e hierarquia.

## Export

```powershell
blender -b <arquivo.blend> --python tools\blender\export_assets.py -- --preset blender\export-presets\fbx_unreal.json --out assets\final\meshes --asset-id <ID> --report reports\<ID>_export.json
python tools\pipeline\manifest.py set-export <ID> assets\final\meshes\<arquivo>.fbx
```

`set-export` calcula SHA-256, grava `export_file`, `hash` e muda o status para `exported`.

## Import (Editor Unreal, Python embutido)

```powershell
UnrealEditor-Cmd.exe unreal\JogoResgate\JogoResgate.uproject -run=pythonscript -script="tools\unreal\import_assets.py --manifest assets\manifest\assets.json --ids <ID>" -unattended
```

O script: lê o manifesto, confere existência e hash do arquivo, **recusa sobrescrever** asset `approved`, importa com opções por categoria e registra falhas em `reports/import_<data>.json`.

## Depois do import

- `tools/unreal/validate_content.py`: nomes, dependências, materiais, colisão.
- Inspeção humana no Editor: escala ao lado do manequim de referência, materiais, LODs, colisão (Show > Collision).
- `python tools\pipeline\manifest.py set-status <ID> in_review`.
- Aprovação: `python tools\pipeline\manifest.py approve <ID> --reviewer "<nome>"` (somente humano).
