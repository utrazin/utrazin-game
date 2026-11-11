# Personagem e combate

## Movimento

- `AJRCharacter` com `UCharacterMovementComponent`: andar 350 cm/s, correr 600 cm/s, pulo 450 cm/s.
- Câmera: Spring Arm 300 cm, offset ombro (Y +50), lag leve; mira aproxima para 150 cm.
- Empurrar: objetos com `Physics Simulate` e massa < 150 kg recebem força proporcional; objetos maiores bloqueiam.

## Arma (`UJRWeaponComponent` + `UJRWeaponDefinition`)

| Campo | Pistola alienígena (provisório) |
|---|---|
| Dano | 25 |
| Cadência | 4 tiros/s |
| Pente | 12 |
| Reserva inicial | 48 |
| Recarga | 1,6 s |
| Tipo | hitscan com traçador (projétil visual) |
| Alcance | 6.000 cm |

Munição em `FJRAmmoState` (lógica pura testada). Sem troca de arma no MVP (A-011), mas o componente suporta lista de definições.

## Saúde (`UJRHealthComponent`)

- Personagem 100, inimigos conforme arquétipo.
- Delegates: `OnHealthChanged`, `OnDeath`. Tag `State.Dead` aplicada na morte.
- Sem regeneração (A-026).

## Interação (`UJRInteractionComponent` + `IJRInteractable`)

Trace curto à frente da câmera (250 cm); o alvo implementa `CanInteract` / `Interact`. Exemplos: portas, grades, cela do resgate (`AJRRescueTarget`).

## Resgate

`AJRRescueTarget`: requer `EJRLevelStage::Rescue`; interação abre a cela, alinha jogador e vítima em sockets e toca `AM_Rescue_Hug` em ambos; ao fim, `UJRObjectiveSubsystem::CompleteLevel()`.

## Personagens e skins

`UJRCharacterDefinition` lista skins (`FJRSkinDefinition`: id, nome, skeletal mesh soft ref, materiais). Troca de skin = troca de mesh/materiais, mesmo esqueleto e cápsula.
