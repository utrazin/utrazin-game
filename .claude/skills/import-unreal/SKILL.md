---
name: import-unreal
description: Importa assets exportados para o projeto Unreal via Python do Editor, sem sobrescrever assets aprovados.
---

# /import-unreal

Importa assets exportados para o projeto Unreal via Python do Editor, sem sobrescrever assets aprovados.

## Pré-requisitos
- Unreal 5.8.4 instalada e projeto compilado
- Asset `exported` com hash

## Passos
1. Feche o Editor (ou use-o com o Python console)
2. `UnrealEditor-Cmd.exe unreal/JogoResgate/JogoResgate.uproject -run=pythonscript -script="tools/unreal/import_assets.py --manifest assets/manifest/assets.json --ids <ID>" -unattended`
3. Verifique `reports/import_*.json`
4. Abra no Editor: escala, materiais, colisão, skeleton, LOD
5. `manifest.py set-status <ID> imported`

## Ferramentas necessárias
- UnrealEditor-Cmd
- tools/unreal/import_assets.py

## Diretórios afetados
- unreal/JogoResgate/Content/

## Verificações
- Sem falhas no relatório
- inspeção visual feita

## Erros comuns
- hash divergente
- asset aprovado já existente (abortado de propósito)

## Critério de sucesso / resultado esperado
Asset importado no caminho do manifesto (`engine_path`).

Registre o que foi realmente executado. Se um pré-requisito faltar (ex.: Unreal não instalada), pare nessa etapa e reporte como bloqueado.
