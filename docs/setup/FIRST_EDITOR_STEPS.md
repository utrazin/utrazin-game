# Primeiros passos no Editor (após compilar)

O C++ define os sistemas; os assets abaixo precisam ser criados **no Editor** (não dá para gerá-los por texto). Ordem sugerida para chegar ao greybox (M1). Use placeholders marcados no manifesto (`creation_method: placeholder`).

## 1. Input (`Content/Core/Input/`)

| Asset | Tipo | Valor |
|---|---|---|
| `IA_Move` | Input Action | Axis2D |
| `IA_Look` | Input Action | Axis2D |
| `IA_Jump`, `IA_Sprint`, `IA_Aim`, `IA_Fire`, `IA_Reload`, `IA_Interact` | Input Action | Digital (bool) |
| `IA_Throttle`, `IA_Brake` | Input Action | Axis1D |
| `IA_Steer` | Input Action | Axis1D |
| `IA_Handbrake` | Input Action | Digital |
| `IA_Pause` | Input Action | Digital |
| `IMC_OnFoot` | Mapping Context | WASD/stick esquerdo, mouse/stick direito, Espaço, Shift, RMB/LT, LMB/RT, R, E |
| `IMC_Vehicle` | Mapping Context | W/RT acelera, S/LT freia, A-D/stick volante, Espaço/B freio de mão, mouse/stick câmera |
| `IMC_Global` | Mapping Context | Esc/Start pausa |

## 2. Blueprints base

| Asset | Pai | Configurar |
|---|---|---|
| `BP_GameInstance` | `JRGameInstance` | Characters, Levels; definir em Project Settings > Maps & Modes |
| `BP_PlayerController` | `JRPlayerController` | IMC_Vehicle, IMC_OnFoot, IMC_Global |
| `BP_Character_Hero01` | `JRCharacter` | malha placeholder (Manny do template Third Person), ABP, ações de input, `DA_Weapon_AlienPistol` no WeaponComponent |
| `BP_Vehicle_SUV` | `JRVehiclePawn` | malha placeholder (veículo do template Vehicle da Epic), WheelSetups FL, FR, RL, RR **nessa ordem**, valores de `docs/gameplay/VEHICLE.md`, ações de input |
| `BP_GameMode_L01` | `JRGameMode` | LevelDefinition = `DA_Level_L01_Zombies`, FallbackCharacterClass, FallbackVehicleClass, PlayerControllerClass = BP_PlayerController |

## 3. Dados (`Content/Data/`)

`DA_Weapon_AlienPistol` (JRWeaponDefinition), `DA_Enemy_ZombieMelee`, `DA_Enemy_ZombieArcher`, `DA_Enemy_ZombieGunner` (JREnemyArchetype, valores de `docs/gameplay/ENEMY_AI.md`), `DA_Character_Hero01` (JRCharacterDefinition com 2 skins), `DA_Level_L01_Zombies` (JRLevelDefinition).

## 4. Mapa `L01_Zombies` (greybox)

Layout em `docs/gameplay/LEVELS.md`. Colocar: Landscape, `AJRCheckpoint` "Start" (bIsLevelStart, StageOnRespawn=Driving), `AJRCheckpoint` "Transition" (bIsVehicleTransition, StageOnRespawn=OnFoot), inimigos `BP_Enemy_*`, `AJRHordeDirector` com Target Points, `AJRRescueTarget`, NavMeshBoundsVolume cobrindo o trecho a pé. World Settings > GameMode Override = `BP_GameMode_L01`.

Validar: `tools/unreal/validate_level.py --map /Game/Levels/L01_Zombies/L01_Zombies`.

## 5. Licença dos placeholders

Conteúdo dos templates da Epic (Manny/Quinn, veículo do template) pode ser usado em projetos Unreal pelo EULA, mas é **placeholder**: registrar no manifesto com `creation_method: placeholder` e substituir antes do M3.
