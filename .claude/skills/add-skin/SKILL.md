---
name: add-skin
description: Adiciona uma skin cosmética a um personagem existente.
---

# /add-skin

Adiciona uma skin cosmética a um personagem existente.

## Pré-requisitos
- Personagem existente
- Concept da skin aprovado

## Passos
1. `/create-asset` com `SKN-NNN` referenciando o personagem
2. Modelar sobre o mesmo esqueleto
3. Importar e criar MIs
4. Adicionar `FJRSkinDefinition` na `DA_Character_*`
5. Testar troca e save

## Ferramentas necessárias
- Blender
- Unreal Editor

## Diretórios afetados
- unreal/JogoResgate/Content/Characters/<Nome>/Skins/

## Verificações
- Sem mudança de hitbox
- save mantém skin

## Erros comuns
- Skin com esqueleto diferente

## Critério de sucesso / resultado esperado
Skin selecionável e salva.

Registre o que foi realmente executado. Se um pré-requisito faltar (ex.: Unreal não instalada), pare nessa etapa e reporte como bloqueado.
