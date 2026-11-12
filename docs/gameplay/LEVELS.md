# Fases e configuração por Data Asset

Cada fase tem um `UJRLevelDefinition` (`DA_Level_L01_Zombies` etc.) com:

| Campo | Exemplo L01 |
|---|---|
| LevelId | `L01` |
| DisplayName / Theme | "Fase 1" / Zumbis |
| Map | `/Game/Levels/L01_Zombies/L01_Zombies` (soft ref) |
| AvailableCharacters | CHR-001, CHR-002 |
| VehicleProfile | `DA_Vehicle_SUV` |
| EnemyArchetypes | ENM-001, ENM-002, ENM-003 |
| HordeWaves | 3 ondas (ver ENEMY_AI) |
| Checkpoints | `Start`, `Transition` (principal) |
| RescueTargetId | a definir (OD-008) |
| Ambience / Weather / Lighting | `AMB_L01`, nublado, fim de tarde (provisório) |
| PerformanceProfile | `High` |

Adicionar fase = novo Data Asset + mapa (skill `/add-level`), **sem código novo**.

## Greybox L01 (M1)

Orçamento de tempo (A-018: **no máximo 10 min**, ~50% carro / ~50% a pé):

| Trecho | Tempo alvo | Tamanho |
|---|---|---|
| Carro (velocidade média ~30 km/h em terreno ruim) | 4 a 5 min | ~1,5 km |
| A pé até a arena (3 encontros) | 2 a 3 min | ~300 m |
| Horda final | 1,5 a 2 min | arena ~40 m |
| Resgate + abraço | < 30 s | |

```
[Início/carro] --estrada sinuosa com morros e buracos (~1,5 km)--> [Checkpoint de transição]
      --trilha a pé com ruínas e obstáculos (~300 m)--> [Arena da horda] --> [Cela / resgate]
```

- Landscape 1 x 1 km (suficiente para o percurso sinuoso), resolução 1009 x 1009.
- Trecho de carro: 3 subidas, 2 descidas fortes, 6 buracos, 4 pontos de emboscada de arqueiros.
- Transição: área plana com socket de saída do carro e checkpoint.
- Trecho a pé: 3 encontros escalonados (corpo a corpo, misto, misto + atirador).
- Arena: circular ~40 m, 4 pontos de spawn fora da visão, coberturas.
- Resgate: cela com grade interativa.
