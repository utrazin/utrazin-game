# ADR-001: Gameplay Ability System fora do MVP

- Status: proposto (aguarda usuário)
- Data: 2026-11-11

## Contexto

O MVP tem uma arma, saúde, dano simples e inimigos com ataques básicos. GAS oferece atributos, efeitos e habilidades replicáveis, mas tem curva de aprendizado alta e muito boilerplate.

## Decisão

Usar **componentes simples** (`UJRHealthComponent`, `UJRWeaponComponent`) com delegates e Gameplay Tags. Dano via `UGameplayStatics::ApplyDamage` / `TakeDamage` nativo.

## Preservando migração

- Estados e eventos já usam Gameplay Tags (`State.Dead`, `Event.Damage.*`).
- Dano passa por um ponto único (`UJRHealthComponent::ApplyDamage`), substituível por um `GameplayEffect`.
- Definições de arma em Data Assets, mapeáveis para `GameplayAbility`.

## Reavaliar quando

Mais de 3 armas com efeitos distintos, buffs/debuffs, habilidades de personagem ou status (veneno, queimadura).
