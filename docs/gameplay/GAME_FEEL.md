# Sensação de jogo (game feel), A-073

Camada de resposta por evento, por cima das mecânicas que já funcionam. Nada aqui muda dano, vida, IA ou a física do carro:
o tremor mexe só na câmera, a congelada só na velocidade do tempo por uma fração de segundo, e a queda do zumbi só no
ragdoll dele depois de morto. Status: **implementado no código, NÃO compilado, NÃO testado em jogo.**

## Tabela por evento (tiers da skill game-feel)

| Evento | Tier | Tremor (trauma) | Congelada | Outros canais | Onde |
|---|---|---|---|---|---|
| Pegar arma do chão | pequeno | 0,12 na hora da mão | não | pulso de zoom -2°, item some do chão e aparece na mão no mesmo instante (42% da animação), herói vira para o item em 0,2 s, câmera 3/4 do lado livre | JRCharacter::PickUpWeaponFromGround, JRInteractionCameraComponent |
| Apertar E (baú, bomba, portão...) | pequeno | 0 | não | pulso de zoom -1,5° | JRCharacter::HandleInteract |
| Curar (vida sobe) | pequeno | 0 | não | pulso de zoom -2,5° | JRCharacter::ApplyHealNow |
| Golpe corpo a corpo acerta | médio | 0,30 (era 0,20) | 0,045 s (era nada) | clarão no zumbi (já existia), empurrão (já existia) | JRCharacter::DoMeleeHit |
| Golpe corpo a corpo mata | grande moderado | 0,45 (era 0,35) | 0,085 s (era 0,06) | zoom -1,5°, corpo cai para longe do golpe | DoMeleeHit, JREnemyCharacter::HandleDeath |
| Tiro mata (pistola) | pequeno | 0,15 | não | zoom -1°, corpo cai para longe | JRWeaponComponent::ApplyPelletHit |
| Tiro mata (escopeta/rifle) | médio | 0,25 | 0,04 s | zoom -1°, corpo cai para longe | idem |
| Aterrissar (queda > ~2,2 m) | pequeno a médio | 0,12 a 0,35 | não | câmera afunda até ~7 cm e volta como mola; acima de ~3,5 m levanta terra | JRCharacter::Landed |
| Carro em velocidade | contínuo | vibração leve do terreno (0,18° no máximo) | não | FOV +9° de 35 a 120 km/h (curva suave, lenta) | JRVehiclePawn::CalcCamera |
| Carro bate / pousa de pulo | médio a grande | por desaceleração (acima de 160 km/h por segundo) | não |  | idem |
| Atropelar zumbi | médio | 0,3 a 60 km/h | não |  | idem (escuta OnZombieCarEvent) |

Já existia e foi mantido: coice por arma (pistola leve, escopeta e rifle fortes), tremor ao levar dano, hit marker, FOV de corrida (+5°), zoom de mira.
Corrigido: o tremor agora decai em tempo real (antes ficava parado fora do centro durante a congelada e a roda de itens).

## Peso ao andar

`MoveMaxAcceleration` e `MoveBrakingDeceleration` = 1500 (padrão da engine 2048): arranque e parada um pouco menos secos.
São aplicados no BeginPlay; 0 = deixa o valor do Blueprint.

## Acessibilidade (console: tecla ' ou ~ durante o Play)

| Comando | Efeito |
|---|---|
| `jr.Feel.ShakeScale 0` a `1` | intensidade de todo tremor (herói e carro) |
| `jr.Feel.MotionScale 0` a `1` | FOV de velocidade do carro, afundada ao aterrissar, pulsos de zoom |
| `jr.Feel.ReduceFlash 1` | clarões de acerto e de plasma mais fracos e curtos |
| `jr.Feel.HitStop 0` | desliga as congeladas |

Pendente (outros donos): o clarão vermelho de dano do HUD (UI/JRHUD) ainda não lê `jr.Feel.ReduceFlash`; um menu de opções para salvar isso.

## Diagnóstico do "pegar sem animação"

Ao pegar uma arma, se o AnimBlueprint do herói não tiver o nó Slot `DefaultSlot`, aparece na tela (laranja, 8 s):
"O AnimBlueprint de ... não tem o Slot 'DefaultSlot'". Se `PickupAnim` estiver vazio, o aviso vai para o Output Log.
