---
name: add-enemy
description: Adiciona um novo arquétipo de inimigo (dados, StateTree, malha) reutilizando a IA existente.
---

# /add-enemy

Adiciona um novo arquétipo de inimigo (dados, StateTree, malha) reutilizando a IA existente.

## Pré-requisitos
- Concept aprovado
- ADR-002

## Passos
1. `/create-asset` com `ENM-NNN`
2. Crie `DA_Enemy_<Nome>` (UJREnemyArchetype): vida, raios, distâncias, ataque, imprecisão
3. Reutilize ou derive `ST_Enemy_*`
4. BP_Enemy_<Nome> derivado de AJREnemyCharacter
5. Inclua nas ondas do `AJRHordeDirector` e na DA da fase
6. Checklist ENEMIES.md

## Ferramentas necessárias
- Unreal Editor

## Diretórios afetados
- unreal/JogoResgate/Content/Enemies/

## Verificações
- Respeita orçamento de agentes

## Erros comuns
- Precisão perfeita
- Tick por frame

## Critério de sucesso / resultado esperado
Inimigo funcional nas hordas.

Registre o que foi realmente executado. Se um pré-requisito faltar (ex.: Unreal não instalada), pare nessa etapa e reporte como bloqueado.
