---
name: export-blender
description: Valida e exporta um asset do Blender para FBX com preset do projeto e registra hash no manifesto.
---

# /export-blender

Valida e exporta um asset do Blender para FBX com preset do projeto e registra hash no manifesto.

## Pré-requisitos
- Blender 5.2 instalado (`BLENDER_EXE` ou PATH)
- Asset em `modeling`/`rigging`/`animation`
- `.blend` com coleção EXPORT

## Passos
1. `git lfs lock` no .blend se for editar
2. `blender -b <arquivo.blend> --python tools/blender/validate_scene.py -- --config tools/blender/validation_config.json --report reports/<ID>_scene.json`
3. Para skeletal: `validate_rig.py -- --required-bones tools/blender/ue5_required_bones.txt`
4. `blender -b <arquivo.blend> --python tools/blender/export_assets.py -- --preset blender/export-presets/fbx_unreal.json --out assets/final/meshes --asset-id <ID> --report reports/<ID>_export.json`
5. `python tools/pipeline/manifest.py set-export <ID> <fbx>`

## Ferramentas necessárias
- Blender
- tools/blender/*
- tools/pipeline/manifest.py

## Diretórios afetados
- blender/
- assets/final/

## Verificações
- Relatórios sem erros
- hash no manifesto
- status exported

## Erros comuns
- transformações não aplicadas
- leaf bones
- escala 100x

## Critério de sucesso / resultado esperado
FBX em assets/final com hash e status `exported`.

Registre o que foi realmente executado. Se um pré-requisito faltar (ex.: Unreal não instalada), pare nessa etapa e reporte como bloqueado.
