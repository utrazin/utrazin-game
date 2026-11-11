---
name: add-character
description: Adiciona um personagem jogável (definição, malha, skins, animações) ao jogo.
---

# /add-character

Adiciona um personagem jogável (definição, malha, skins, animações) ao jogo.

## Pré-requisitos
- Concept aprovado (OD-007)
- Esqueleto padrão

## Passos
1. `/create-asset` com `CHR-NNN`
2. Pipeline de arte até `imported`
3. Crie `DA_Character_<Nome>` (UJRCharacterDefinition) com id, nome, mesh base, ABP, skins
4. Adicione à lista de personagens disponíveis nas `DA_Level_*`
5. Teste troca no menu (MANUAL_QA 17)

## Ferramentas necessárias
- Unreal Editor
- manifest.py

## Diretórios afetados
- unreal/JogoResgate/Content/Characters/
- unreal/JogoResgate/Content/Data/

## Verificações
- Retarget OK
- cápsula igual aos demais

## Erros comuns
- Esqueleto diferente do padrão

## Critério de sucesso / resultado esperado
Personagem selecionável.

Registre o que foi realmente executado. Se um pré-requisito faltar (ex.: Unreal não instalada), pare nessa etapa e reporte como bloqueado.
