# Arquitetura

> Estado: **projetada e escrita em C++, nunca compilada** (IMP-001). Os nomes abaixo são os reais do código em `unreal/JogoResgate/Source/JogoResgate/`.

## Camadas

```
            +-----------------------------+
            |  Apresentação (Blueprint)   |  WBP_ HUD/menus, BP_ derivados, ABP_, VFX, áudio
            +--------------+--------------+
                           | lê estado via delegates / getters (nunca escreve regra)
            +--------------v--------------+
            |  Gameplay (C++ componentes) |  Health, Weapon, Interaction, VehicleDamage, Enemy
            +--------------+--------------+
                           |
            +--------------v--------------+
            |  Fluxo de fase (C++)        |  ObjectiveSubsystem, Checkpoint, HordeDirector, RescueTarget
            +--------------+--------------+
                           |
            +--------------v--------------+
            |  Persistência / Progressão  |  ProgressionSubsystem, SaveGame, SaveMigration
            +--------------+--------------+
                           |
            +--------------v--------------+
            |  Dados (Data Assets)        |  LevelDefinition, CharacterDefinition, WeaponDefinition, EnemyArchetype
            +-----------------------------+
```

Lógica pura (sem mundo, testável) fica em structs/funções estáticas: `FJRVehicleDamageState`, `FJRAmmoState`, `FJRAimPrediction`, `FJREnemyStateLogic`, `FJRSaveMigration`. As quatro primeiras também compilam e rodam fora da engine (`tests/cpp/`).

## Módulo e pastas

| Pasta | Classes |
|---|---|
| `Core/` | `UJRGameInstance`, `AJRGameMode`, `AJRPlayerController`, `JRGameplayTags` |
| `Progression/` | `UJRProgressionSubsystem` (GameInstanceSubsystem) |
| `Save/` | `UJRSaveGame`, `FJRSaveMigration` |
| `Levels/` | `UJRLevelDefinition`, `AJRCheckpoint`, `UJRObjectiveSubsystem` (WorldSubsystem) |
| `Characters/` | `AJRCharacter`, `UJRCharacterDefinition` |
| `Vehicles/` | `AJRVehiclePawn`, `UJRVehicleDamageComponent`, `FJRVehicleDamageState` |
| `Combat/` | `UJRHealthComponent`, `UJRWeaponComponent`, `UJRWeaponDefinition`, `FJRAmmoState` |
| `Interactions/` | `IJRInteractable`, `UJRInteractionComponent`, `AJRRescueTarget` |
| `AI/` | `AJREnemyCharacter`, `UJREnemyArchetype`, `AJRHordeDirector`, `UJREnemyBudgetSubsystem`, `FJRAimPrediction`, `FJREnemyStateLogic` |
| `Utilities/` | reservado para helpers compartilhados (vazio no M0) |
| raiz do módulo | `JogoResgate.h/.cpp` (módulo + categoria de log `LogJR`) |
| `Tests/` | Automation Tests das partes puras |

## Fluxos principais

### Possession carro para personagem (checkpoint principal)

1. `AJRCheckpoint` (overlap com `AJRVehiclePawn`) chama `UJRObjectiveSubsystem::ReachCheckpoint`.
2. Subsystem emite `OnCheckpointReached`; `UJRProgressionSubsystem` salva.
3. Se o checkpoint é de transição, `AJRPlayerController::RequestExitVehicle()`:
   - zera input do veículo (`SetThrottleInput(0)`, freio de mão) e desativa simulação ativa (A-015);
   - spawna o `AJRCharacter` no socket `ExitPoint` do veículo (ou reutiliza um existente: **nunca duplica**);
   - toca montage de saída (`AM_Vehicle_Exit`) e então `Possess(Character)`;
   - troca o Input Mapping Context (`IMC_Vehicle` -> `IMC_OnFoot`).
4. Estado `Phase` muda para `OnFoot`.

### Fase

`UJRObjectiveSubsystem` mantém `EJRLevelStage`: `Driving -> OnFoot -> FinalHorde -> Rescue -> Completed` (ou `Failed`). Widgets só **observam** os delegates.

### Morte e checkpoint

`UJRHealthComponent::OnDeath` (personagem) ou `UJRVehicleDamageComponent::OnVehicleDisabled` -> `AJRGameMode::HandlePlayerFailure` -> recarrega o último checkpoint salvo (A-013, A-014).

### Save

`UJRSaveGame` com `SaveVersion` (int). `FJRSaveMigration::Migrate` atualiza saves antigos passo a passo. Slot único `JR_Slot_0` + slot de settings.

## Regras de dependência

- Dados não dependem de nada.
- Componentes de gameplay não conhecem o fluxo de fase; comunicam por delegates e Gameplay Tags.
- Subsystems não referenciam widgets.
- `AI/` depende de `Combat/` (dano), nunca o contrário.
- Sem dependências circulares entre pastas (revisado pelo `technical-architect`).

## Decisões

- ADR-001: GAS fora do MVP
- ADR-002: StateTree para IA
- ADR-003: Chaos Vehicles e modelo de dano
- ADR-004: Renderização e streaming orientados a medição

Ver também [`RENDERING.md`](RENDERING.md).
