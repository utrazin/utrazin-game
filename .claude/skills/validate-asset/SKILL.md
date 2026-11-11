---
name: validate-asset
description: Executa todos os validadores de um asset (manifesto, nomes, licença, cena/rig, conteúdo Unreal) e produz relatório.
---

# /validate-asset

Executa todos os validadores de um asset (manifesto, nomes, licença, cena/rig, conteúdo Unreal) e produz relatório.

## Pré-requisitos
- Asset com entrada no manifesto

## Passos
1. `python tools/pipeline/manifest.py validate`
2. `python tools/pipeline/validate_naming.py <arquivos do asset>`
3. `python tools/pipeline/check_licenses.py --ids <ID>`
4. Blender: validate_scene/validate_rig (se aplicável)
5. Unreal: `tools/unreal/validate_content.py --paths <engine_path>` (se importado)
6. Consolide em `docs/qa/reports/<data>_<ID>.md` com ok/falha/não executado

## Ferramentas necessárias
- tools/pipeline/*
- tools/blender/*
- tools/unreal/*

## Diretórios afetados
- docs/qa/reports/

## Verificações
- Cada validador com resultado real

## Erros comuns
- Marcar validador não executado como ok

## Critério de sucesso / resultado esperado
Relatório e status `in_review` quando tudo passar.

Registre o que foi realmente executado. Se um pré-requisito faltar (ex.: Unreal não instalada), pare nessa etapa e reporte como bloqueado.
