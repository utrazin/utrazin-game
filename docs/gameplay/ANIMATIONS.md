# Animações (auditoria 2026-11-16)

Fonte das animações: **Mixamo** (esqueleto do X Bot, `assets/raw/mixamo/**`, importadas em `/Game/Characters/Mixamo/Anims/<grupo>`) e **template da Epic** (Manny, `/Game/Characters/Mannequins/Anims`). Tudo chega aos personagens por **IK Retargeter** (`/Game/Characters/Rigs/RTG_*`). A Unreal não sobrescreve saídas de retarget: cada script grava em pasta nova (`Anims/Mixamo`, `Anims/Wave1`, `Anims/Wave2`, ...).

Legenda da coluna "Situação": **ok** = existe e está ligada no jogo; **parcial** = existe mas com limitação; **falta** = sem animação; **pronta, sem uso** = asset existe, mas nada no C++/ABP toca.

## Heróis (Hero01 Enzo e Hero02 Victoria, sufixos `_H01` / `_H02`)

| Ação | Asset no projeto | Fonte | Situação |
|---|---|---|---|
| Parado / andar / correr | `Anims/ABP_Unarmed_HNN`, `BS_Idle_Walk_Run_HNN`, `MM_Idle_HNN`, `MF_Unarmed_Walk_*`, `MF_Unarmed_Jog_*` | template Epic (Manny) via RTG_Manny_HeroNN | ok |
| Correr rápido (sprint, Shift) | mesma blend space (jog) acelerada | template Epic | parcial (sem animação própria de sprint) |
| Pular / cair / aterrissar | `MM_Jump_HNN`, `MM_Fall_Loop_HNN`, `MM_Land_HNN` | template Epic | ok |
| Agachar | nenhum | - | não existe a mecânica (sem necessidade) |
| Dash / wall jump | `MM_Dash_HNN`, `MM_WallJump_HNN` | template Epic | pronta, sem uso |
| Pistola: mirar (AimAnim) | `Anims/Mixamo/A_Pistol_idle_HNN` | Mixamo "Pistol Idle" | ok |
| Pistola: atirar (FireAnim) | `A_Fire_Recoil_HNN` | Mixamo | ok |
| Pistola: recarregar (ReloadAnim) | `A_Reload_Pistol_HNN` | Mixamo | ok |
| Pistola: sacar / guardar | `A_Equip_Pistol_HNN` / `A_Unequip_Pistol_HNN` | Mixamo | ok |
| Arma na mão SEM mirar (ArmedIdleAnim) | `Wave2/A_Pistol_Idle_Low_HNN` (após `setup_anims_wave2.py`) | Mixamo "Pistol Idle" (Idle Holding Pistol, Kicking Out And Shaking Legs), `hero/Pistol_Idle_Low.fbx` | ok depois do script (pistola baixa nas duas mãos, cano para a frente e para baixo; ver `_grip_check_*_ArmadaParada.png`) |
| Andar/correr mirando com pistola | `A_Pistol_walk/run/strafe/*_HNN` (13 variações), `A_Pistol_jump*`, `A_Pistol_kneel*` | Mixamo | pronta, sem uso (o ABP não tem estado armado) |
| Escopeta: mirar / atirar / recarregar / sacar (Shotgun*Anim) | `Anims/Wave2/MF_Rifle_Idle_ADS_HNN`, `MM_Rifle_Fire_HNN`, `MM_Rifle_Reload_HNN`, `MM_Rifle_Equip_HNN` | template Epic (rifle) via RTG_Manny_HeroNN | ok depois de `setup_anims_wave2.py` (o encaixe da escopeta é medido na mira de rifle pelo `fix_weapon_grips.py`) |
| Escopeta: bombear (pump) | nenhum | - | falta (o rifle do template não tem pump; baixar "Shotgun"/"Pump Action" no Mixamo se quiser) |
| Graveto: combo (MeleeAnims) | `Anims/Wave1/A_Melee_Slash_Out_HNN`, `A_Melee_Slash_In_HNN` | Mixamo "Stable Sword Outward/Inward Slash" | ok |
| Pegar do chão (PickupAnim) | `Wave1/A_PickUp_Gun_HNN` | Mixamo "Unarmed Grab Torch From Floor" | ok |
| Abrir baú (OpenChestAnim) | `Wave1/A_Open_Chest_HNN` | Mixamo "Opening A Lid" | ok |
| Curar com bandagem / kit (HealAnim) | `Wave2/A_Heal_Bandage_HNN` | Mixamo "Drinking" (Male Drinking, 267 quadros = 8,9 s), `hero/Heal_Bandage.fbx`. O Mixamo não tem animação de bandagem | ok depois do script (parcial: é "beber"; HealDuration corta antes do fim) |
| Reação a dano (HitReactAnim) | `A_HitReact_Pistol_HNN` | Mixamo | ok |
| Morte (DeathMontage) | `AM_Death_Backwards_HNN` | Mixamo | ok |
| Entrar no carro | `A_Car_Enter_HNN` | Mixamo | pronta, sem uso (o herói some na hora ao entrar) |
| Sair do carro (ExitVehicleMontage) | `AM_Car_Exit_HNN` | Mixamo | ok |
| Dirigindo (DrivingAnim) | `Wave1/A_Driving_HNN` | Mixamo "Driving" | ok |
| Resgate / abraço (RescueHugMontage) | `AM_Rescue_HelpIntoVehicle_HNN` | Mixamo | ok |
| Interagir: abastecer, portão, gerador (InteractAnim) | `Wave2/A_Interact_Button_HNN` | Mixamo "Button Pushing" (98 quadros = 3,3 s), `hero/Interact_Button.fbx` | ok depois do script |
| Armar explosivo na colmeia (PlantAnim) | `Wave2/A_Plant_Kneel_HNN` | Mixamo "Plant A Plant" (ajoelhado, 228 quadros = 7,6 s), `hero/Plant_Kneel.fbx` | ok depois do script |

## Zumbis (Melee, Archer, Gunner, Elite)

Hoje: malha Copzombie com montages `_CZ` (`/Game/Enemies/Copzombie/Anims`). Depois de `setup_zombie_models.py` (A-053) cada personagem novo (ZMB_Comum, ZMB_Corredor, ZMB_Tanque) recebe cópias retargetadas das mesmas origens.

| Ação | Asset no projeto | Fonte | Situação |
|---|---|---|---|
| Parado / andar / correr | `A_Zombie_Idle/Walk/Run` (X Bot) -> `_Manny` -> `_CZ`; blend space `BS_Idle_Walk_Run_CZ` | Mixamo | ok (lados/trás ainda do Manny, A-048) |
| Atacar (AttackMontage) | `AM_Zombie_Punching_CZ` | Mixamo "Zombie Punching" | ok (só Melee e Elite) |
| Agarrar o carro | usa a pose de pé + AttackMontage | - | parcial (A-041) |
| Reação a dano (HitReactMontage) | `AM_Zombie_ReactionHit_CZ` | Mixamo | ok |
| Morte | ragdoll (Physics Asset); `A_Zombie_Death` existe sem uso | Mixamo | ok (ragdoll) |
| Comer (FeedMontage) | `AM_Zombie_Feed_*` (por esqueleto do DA) | Mixamo "Zombie Biting" (Biting Victim On The Ground, 71 quadros), `zombie/Zombie_Feed.fbx` | ok depois do script |
| Gritar / variação parado (IdleVariationMontages) | `AM_Zombie_Scream_*` e `AM_Zombie_ScratchIdle_*` | Mixamo "Zombie Scream" (85 quadros) e "Zombie Scratch Idle" (142 quadros), `zombie/Zombie_Scream.fbx`, `zombie/Zombie_ScratchIdle.fbx` | ok depois do script |

## Sobrevivente (vítima do resgate)

| Ação | Asset no projeto | Fonte | Situação |
|---|---|---|---|
| Parado ferido, acenando | `A_Rescued_InjuredWaveIdle` (X Bot) -> `A_NPC_Sobrevivente_Idle` (setup_zombie_models) | Mixamo | ok |
| Com medo (scared) | `/Game/Characters/Mixamo/Anims/npc/A_Survivor_Terrified` (só importado) | Mixamo "Terrified" (601 quadros = 20 s), `npc/Survivor_Terrified.fbx` | pronta, sem uso (para trocar, mude SURVIVOR_IDLE no `setup_zombie_models.py`) |
| Seguir o herói | não existe a mecânica (A-047: a sobrevivente não anda) | - | - |
| Abraço (VictimHugMontage) | vazio: só o herói anima | - | falta (A-052) |

## Downloads do Mixamo (2026-11-16)

Baixados no navegador embutido (FBX Binary, Without Skin, 30 fps), conferidos no Blender (65 ossos `mixamorig:`, quadros batendo com o site). O personagem selecionado no Mixamo era o do usuário (`SM_NPC_Sobrevivente_mixamo`: quadril a 0,97 m e cabeça a 1,44 m, contra 1,04 m e 1,60 m do X Bot). Não troquei para o X Bot porque o site avisa que o personagem atual "não será salvo". Efeito possível: o retarget a partir do X Bot pode deixar o quadril ~7% mais baixo (joelhos um pouco dobrados) nas animações de corpo inteiro. Conferir no editor; se incomodar, baixar de novo com o X Bot selecionado.

Nada de bandagem ou abraço no Mixamo (buscas: bandage, injured, heal, wound, checking, hug). Entrar no carro, zumbi agarrando o carro e abraço da vítima continuam sem animação (não há propriedade no C++ para os dois últimos).

## Encaixe das armas (grip check, 2026-11-16)

Conferido no Blender (`tools/blender/grip_check.py`, imagens `assets/work/weapons/_grip_check_<Herói>_<Arma>_<Pose>.png`; linha vermelha = cano/lâmina, verde = frente do herói):

- **Pistola (atual)**: presa no pulso (origem no osso `hand_r`, ~1 cm dele), cabo meio fora da mão e cano **17 a 20 graus para a direita e ~6 graus para baixo** na mira. Causa: `setup_mixamo.weapon_grip` usa "peito -> mão" como frente e não achou os ossos dos dedos (o ponto ficou no pulso).
- **Escopeta**: usa o mesmo encaixe da pistola, mas o cabo dela fica 3 a 4 cm mais para trás/baixo. Malha grande (0,9 m) cobre o rosto vista de frente.
- **Graveto** (`fix_weapons_user.py`): a mão segura o pomo (origem da malha), não a parte enrolada (a ~16,5 cm). Com lâmina a 20 graus, alguns quadros do golpe encostam no corpo; 30 graus fica limpo nos dois heróis.
- **Arma abaixada**: sem ArmedIdleAnim o herói armado usa as animações desarmadas (mão aberta, arma pendurada). Com `A_Pistol_Idle_Low` no ArmedIdleAnim a pistola e a escopeta ficam fechadas na mão, apontando para a frente e para baixo (`_grip_check_<Herói>_<Arma>_ArmadaParada.png`).
- Correção: `tools/unreal/fix_weapon_grips.py` mede na própria Unreal e põe o centro do cabo no centro do punho, cano para a frente do personagem; graveto pela parte enrolada, lâmina 30 graus. Valores e conferência em `reports/fix_weapon_grips.json`.

## Mudanças de C++ pedidas (dono: `Characters/JRCharacter.*`; segundo o coordenador, já feitas: armed_idle_anim, shotgun_*_anim, interact_anim, plant_anim, heal_anim, pistol/shotgun/melee_grip_transform)

1. Encaixe por arma: `FTransform PistolGripTransform`, `ShotgunGripTransform`, `MeleeGripTransform` (EditDefaultsOnly), aplicados em WeaponMesh/MeleeMesh quando a arma troca (hoje só muda a malha e `ShotgunMeshScale`). O `fix_weapon_grips.py` já tenta preencher `pistol_grip_transform`/`shotgun_grip_transform`/`melee_grip_transform`.
2. Escopeta: `ShotgunAimAnim`, `ShotgunFireAnim`, `ShotgunReloadAnim`, `ShotgunEquipAnim` (usar quando `CurrentSlot == Shotgun`, cair para as da pistola se vazias). O `setup_anims_wave2.py` preenche `shotgun_*_anim` com o rifle do template.
3. `ArmedIdleAnim` (loop no slot UpperBody enquanto armado e sem mirar), para a mão fechar na arma.
4. `InteractAnim` / `PlantAnim` (corpo inteiro via `PlayFullBodyAction`) usados por `AJRBlockingGate` (combustível, explosivo).
