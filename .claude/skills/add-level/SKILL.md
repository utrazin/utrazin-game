---
name: add-level
description: Adiciona uma nova fase ao jogo usando Data Asset de fase e mapa, sem código novo.
---

# /add-level

Adiciona uma nova fase ao jogo usando Data Asset de fase e mapa, sem código novo.

## Pré-requisitos
- M2 validado (para fases 2+)
- Tema decidido (OD-010)

## Passos
1. Crie pasta `Content/Levels/L<NN>_<Nome>/`
2. No Editor, crie o mapa `L<NN>_<Nome>` (greybox primeiro)
3. Crie `DA_Level_L<NN>_<Nome>` (UJRLevelDefinition) preenchendo todos os campos de docs/gameplay/LEVELS.md
4. Posicione `AJRCheckpoint` (Start e Transition), `AJRHordeDirector`, `AJRRescueTarget`
5. Registre a fase na lista do `UJRProgressionSubsystem` (DA de catálogo)
6. Rode `tools/unreal/validate_level.py --map <caminho>`

## Ferramentas necessárias
- Unreal Editor
- tools/unreal/validate_level.py

## Diretórios afetados
- unreal/JogoResgate/Content/Levels/
- unreal/JogoResgate/Content/Data/

## Verificações
- validate_level sem erros
- fluxo completo jogável (MANUAL_QA)

## Erros comuns
- Checkpoint de transição ausente
- spawns visíveis

## Critério de sucesso / resultado esperado
Fase jogável com os mesmos sistemas.

Registre o que foi realmente executado. Se um pré-requisito faltar (ex.: Unreal não instalada), pare nessa etapa e reporte como bloqueado.
