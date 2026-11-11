# IA de inimigos (Fase 1: zumbis)

Implementação: StateTree (ADR-002). Dados em `UJREnemyArchetype`.

| Arquétipo | Vida | Aggro (cm) | Distância preferida | Ataque | Imprecisão |
|---|---|---|---|---|---|
| ENM-001 Corpo a corpo | 60 | 2.500 | 150 | 15 dano, 1/s | n/a |
| ENM-002 Arqueiro | 40 | 4.000 | 1.800 | flecha 20, 1 a cada 2,5 s, com antecipação | 3° |
| ENM-003 Atirador | 50 | 3.500 | 1.500 | rajada 3x8, intervalo 3 s | 5° |

## Estados

Decisão pura em `FJREnemyStateLogic::Decide` (testada). No greybox, o próprio `AJREnemyCharacter` executa a decisão por timer ("cérebro embutido", `bUseBuiltInBrain`), para a IA funcionar antes de existir qualquer asset. Quando o StateTree `ST_Enemy_Base` for criado no Editor, ele assume a orquestração chamando `UpdateBrain`/`TryAttack` e o cérebro embutido é desligado.


`Idle -> Patrol -> Alert -> Chase -> Attack -> Dead`. Transições por distância e linha de visão; `Alert` dura 1,5 s (telegrafa ao jogador).

## Mira à distância

`FJRAimPrediction::PredictInterceptPoint` resolve o ponto de interceptação para alvo com velocidade constante (inclui veículo). `ApplySpread` adiciona dispersão cônica para evitar precisão perfeita.

## Orçamento

`UJREnemyBudgetSubsystem`: no máximo 12 agentes "completos" (A-029), escolhidos por proximidade; os demais com tick 0,25 s e sem percepção. Até 30 visíveis na horda.

## Hordas

`AJRHordeDirector`: lista de ondas (`FJRWave`: arquétipo, quantidade, intervalo). Spawn só em pontos **fora do frustum** e a mais de 1.500 cm do jogador; libera agentes mortos após 10 s e distantes > 8.000 cm.

## Testes

Perseguição do veículo e do personagem; checklist `tests/gameplay/checklists/ENEMIES.md`; teste puro `JR.AI.AimPrediction.*`.
