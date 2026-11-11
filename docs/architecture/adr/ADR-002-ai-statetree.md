# ADR-002: StateTree para IA de inimigos

- Status: proposto
- Data: 2026-11-11

## Comparação

| Critério | Behavior Tree | StateTree |
|---|---|---|
| Modelo mental | Árvore de decisão reavaliada | Máquina de estados hierárquica |
| Encaixe com o GDD (Idle, Patrol, Alert, Chase, Attack, Dead) | Indireto | **Direto** |
| Custo de CPU | Blackboard + reavaliação | Leve; bom com muitos agentes |
| Integração Mass/LOD de IA | Limitada | Melhor |
| Maturidade | Muito madura | Madura desde 5.4, padrão recomendado pela Epic em projetos novos |
| Debug | Excelente | Bom (StateTree debugger) |
| EQS | Nativo | Via tasks |

## Decisão

**StateTree** (`UStateTreeAIComponent`) com tasks em C++ para percepção por distância, ataque e mira. Estados: `Idle, Patrol, Alert, Chase, Attack, Dead`. Behavior Tree fica como fallback se algum arquétipo exigir EQS complexo.

## Consequências

- Arquétipos (`UJREnemyArchetype`) definem raios de aggro, distância preferida, cadência e imprecisão.
- `UJREnemyBudgetSubsystem` limita agentes com atualização completa (12, A-029); os demais rodam com tick reduzido.
