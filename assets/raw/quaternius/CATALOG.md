# Quaternius CC0 asset catalog

Downloaded 2026-11-15 by the Arte agent (Etapa 4). All packs are CC0 1.0 (checked on the pack page and in the License.txt inside each archive). Each pack folder has a `LICENSE_SOURCE.txt` and a `_preview.png` contact sheet.

How the numbers were measured: every glTF (or FBX where no glTF exists) was imported in Blender 5.2 (bpy). `tris` = evaluated triangles of all visible meshes. `size` = world bounding box X x Y x Z in Blender units (meters, Z up) after import. Quaternius rigged glTFs ship a hidden helper mesh called `Icosphere`; it was excluded. For rigged characters the size is the rest/T-pose box, so use the largest number as rough height; Ultimate Monsters and Space Kit characters come in at roughly 2.5 to 4.5 units and will need scaling in Unreal. Paths are relative to `assets/raw/quaternius/`.

Legend: **HERO** = good hero / landmark piece. FBX twin: every glTF has an FBX with the same name in the sibling `FBX/` folder (Unreal import: prefer FBX for skeletal meshes, glTF Importer or FBX for statics).

## Recommendations for the alien forest

| Use | Pick | Why |
|---|---|---|
| Ground cover | Nature `Grass_Wispy_Short/Tall`, `Grass_Common_Short/Tall`, `Clover_1/2`, `Fern_1`, `Plant_7(_Big)`, `Petal_1..5`; Space Kit `Grass_1..3` as alien accents | 48 to 620 tris, textured cards, good for foliage painting / PCG. Recolor grass to teal/violet via material instance for alien look |
| Bushes | Nature `Bush_Common`, `Bush_Common_Flowers`, `Plant_1_Big`; Space Kit `Bush_1..3` (teal crystal-like) | Nature bushes are dense and textured; Space Kit bushes give alien silhouettes |
| Trees, species A (canopy/mass) | Nature `TwistedTree_1..5` (9 to 10k tris, 15 to 19 m) | Big gnarled canopy, swap leaf texture/tint to magenta or cyan. Main forest mass |
| Trees, species B (alien) | Space Kit `Tree_Blob_1..3`, `Tree_Swirl_1/2`, `Tree_Spiral_1..3`, `Tree_Light_1/2` | Clearly alien shapes, low poly (750 to 6k). Use as mid-layer and near paths. `Tree_Light` (glowing bulbs) = natural light source |
| Trees, species C (dead/eerie) | Nature `DeadTree_1..5` (6k tris, up to 16 m), Nature `Pine_1..5` for background mass | Zombie mood; dead trees as silhouettes against sky |
| Rocks | Nature `Rock_Medium_1..3` (textured, 250 to 520 tris), Space Kit `Rock_1..4`, `Rock_Large_1..3` (up to 8.5 m, HERO cliffs), Nature `Pebble_*` and `RockPath_*` for trails | Mix: nature rocks for detail, Space Kit large rocks for blockout and landmarks |
| Mushrooms / alien plants | Nature `Mushroom_Common`, `Mushroom_Laetiporus` (scale up 5 to 10x for giant shelf fungus HERO); Space Kit `Plant_1..3`, `Tree_Lava_1..3`, `Tree_Floating_1..3`, `Tree_Spikes_1/2` | Scaled mushrooms plus Space Kit tendrils give the "alien forest" read |
| Landmarks | Space Kit `GeodesicDome`, `Base_Large`, `Rock_Large_2/3`, `Tree_Blob_1`; Ruins `Statue_Stag`, `Wall_ArchRound_Overgrown`, `Arch_Gothic`; Zombie `WaterTower`, `TownSign`; Nature `TwistedTree_*` scaled 1.5x | Readable silhouettes for navigation |
| Houses / base / gas station | Space Kit modular base (`House_Single/Long/Cylinder/Open`, `Connector`, `Roof_*`, `SolarPanel_*`, `Stairs`, `Ramp`) for the survivor base; Ruins walls/arches/floors for old overgrown structures; Zombie `Street_*`, `StreetLights`, `TrafficLight_*`, `Container_*`, `PlasticBarrier`, `TrafficBarrier_*`, `Barrel`, `Pallet*`, `TrashBag_*`, `Wheels_Stack`, `FireHydrant` to dress a gas-station / roadside area | No dedicated gas station model in any free pack downloaded. Build it from Zombie Kit street props + Space Kit `House_Long`/`Building_L` or a simple kitbash. Downtown City MegaKit (itch.io) may have one; not downloaded |
| Vehicles | Zombie `Vehicle_Pickup(_Armored)`, `Vehicle_Truck(_Armored)`, `Vehicle_Sports`; Cars Pack (7 sedans/SUV/cop/taxi, about 3k tris) as wrecks; Space Kit `Rover_1/2` | Zombie Kit vehicles match the art style best |
| Zombies | Zombie Kit `Zombie_Basic`, `Zombie_Chubby`, `Zombie_Arm`, `Zombie_Ribcage` (rigged, 4.8k to 7.8k tris, Crawl/Idle/Idle_Attack/Walk/Run/Run_Arms/Run_Attack/Punch/HitReact/Death and more) | Same rig family (43 to 50 bones) as the Zombie Kit survivors; Ribcage has a reduced 12-bone rig |
| Alien creatures (optional) | Space Kit `Enemy_Large/Small/ExtraSmall/Flying`; Ultimate Monsters `Alien` (Big), `Mushnub(_Evolved)`, `GreenSpikyBlob`, `MushroomKing` | Rigged and animated; good as alien wildlife or mutated enemies |

Survivor characters also available: Zombie Kit `Characters_Lis/Matt/Sam/Shaun` (25 to 28k tris with all weapons attached; `_SingleWeapon` variants 9 to 11k tris) plus dog companions `Characters_GermanShepherd`, `Characters_Pug`.

Caveats: the free Nature MegaKit is the Standard tier (68 of 116 models, no custom wind shader; the Unreal-ready shader is in the paid Source tier). Ruins FBX foliage (Bush_*, Tree_*) render white in Blender because the leaf texture is not auto-linked; textures are in `UltimateModularRuins/.../Textures/`. Cars Pack is untextured flat-color and more "realistic low poly" than the rest.

## Stylized Nature MegaKit (Standard free tier, 68/116 models)

- Folder: `StylizedNatureMegaKit/` | Page: https://quaternius.com/packs/stylizednaturemegakit.html | Formats: glTF (+ .bin, textures in glTF/), FBX, FBX (Unity), OBJ | Models measured: 68
- Preview: `StylizedNatureMegaKit/_preview.png`

### Trees

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| CommonTree_1 | 6265 | 4.31 x 4.58 x 7.26 |  | `StylizedNatureMegaKit/glTF/CommonTree_1.gltf` |
| CommonTree_2 | 5648 | 4.46 x 4.28 x 7.64 |  | `StylizedNatureMegaKit/glTF/CommonTree_2.gltf` |
| CommonTree_3 | 3505 | 4.06 x 4.24 x 9.43 |  | `StylizedNatureMegaKit/glTF/CommonTree_3.gltf` |
| CommonTree_4 | 4066 | 3.83 x 3.76 x 9.44 |  | `StylizedNatureMegaKit/glTF/CommonTree_4.gltf` |
| CommonTree_5 | 3182 | 3.67 x 4.22 x 7.01 |  | `StylizedNatureMegaKit/glTF/CommonTree_5.gltf` |
| DeadTree_1 | 6169 | 6.15 x 5.75 x 9.5 |  | `StylizedNatureMegaKit/glTF/DeadTree_1.gltf` |
| DeadTree_2 | 6557 | 6.73 x 6.38 x 11.49 |  | `StylizedNatureMegaKit/glTF/DeadTree_2.gltf` |
| DeadTree_3 | 5802 | 6.39 x 6.43 x 13.28 |  | `StylizedNatureMegaKit/glTF/DeadTree_3.gltf` |
| DeadTree_4 | 5702 | 7.96 x 7.73 x 12.77 | **HERO** | `StylizedNatureMegaKit/glTF/DeadTree_4.gltf` |
| DeadTree_5 | 5648 | 8.36 x 8.41 x 16.44 | **HERO** | `StylizedNatureMegaKit/glTF/DeadTree_5.gltf` |
| Pine_1 | 3947 | 4.94 x 4.54 x 7.32 |  | `StylizedNatureMegaKit/glTF/Pine_1.gltf` |
| Pine_2 | 3648 | 5.73 x 5.22 x 7.38 |  | `StylizedNatureMegaKit/glTF/Pine_2.gltf` |
| Pine_3 | 4964 | 3.61 x 4 x 7.39 |  | `StylizedNatureMegaKit/glTF/Pine_3.gltf` |
| Pine_4 | 3370 | 5.8 x 5.37 x 10.24 |  | `StylizedNatureMegaKit/glTF/Pine_4.gltf` |
| Pine_5 | 1646 | 6.42 x 6.22 x 8.72 |  | `StylizedNatureMegaKit/glTF/Pine_5.gltf` |
| TwistedTree_1 | 9564 | 13.52 x 11.55 x 16.73 | **HERO** | `StylizedNatureMegaKit/glTF/TwistedTree_1.gltf` |
| TwistedTree_2 | 9134 | 10.56 x 9.2 x 18.95 | **HERO** | `StylizedNatureMegaKit/glTF/TwistedTree_2.gltf` |
| TwistedTree_3 | 10089 | 11.36 x 11.51 x 16.07 | **HERO** | `StylizedNatureMegaKit/glTF/TwistedTree_3.gltf` |
| TwistedTree_4 | 9600 | 10.38 x 11.29 x 18.74 | **HERO** | `StylizedNatureMegaKit/glTF/TwistedTree_4.gltf` |
| TwistedTree_5 | 10104 | 9.49 x 9.39 x 15.66 | **HERO** | `StylizedNatureMegaKit/glTF/TwistedTree_5.gltf` |

### Bushes / shrubs

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Bush_Common | 900 | 1.91 x 1.97 x 1.58 |  | `StylizedNatureMegaKit/glTF/Bush_Common.gltf` |
| Bush_Common_Flowers | 1368 | 1.91 x 1.97 x 1.58 |  | `StylizedNatureMegaKit/glTF/Bush_Common_Flowers.gltf` |

### Grass / ground cover / small plants

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Clover_1 | 379 | 0.8 x 0.76 x 1.14 |  | `StylizedNatureMegaKit/glTF/Clover_1.gltf` |
| Clover_2 | 615 | 0.85 x 0.84 x 1.26 |  | `StylizedNatureMegaKit/glTF/Clover_2.gltf` |
| Fern_1 | 288 | 2.83 x 2.65 x 0.84 |  | `StylizedNatureMegaKit/glTF/Fern_1.gltf` |
| Flower_3_Group | 755 | 1.49 x 1.59 x 2.05 |  | `StylizedNatureMegaKit/glTF/Flower_3_Group.gltf` |
| Flower_3_Single | 285 | 0.91 x 0.88 x 2.07 |  | `StylizedNatureMegaKit/glTF/Flower_3_Single.gltf` |
| Flower_4_Group | 1690 | 1.78 x 1.37 x 2.49 |  | `StylizedNatureMegaKit/glTF/Flower_4_Group.gltf` |
| Flower_4_Single | 642 | 1.07 x 0.77 x 2.42 |  | `StylizedNatureMegaKit/glTF/Flower_4_Single.gltf` |
| Grass_Common_Short | 155 | 0.64 x 0.74 x 1.33 |  | `StylizedNatureMegaKit/glTF/Grass_Common_Short.gltf` |
| Grass_Common_Tall | 326 | 0.9 x 0.99 x 1.87 |  | `StylizedNatureMegaKit/glTF/Grass_Common_Tall.gltf` |
| Grass_Wispy_Short | 494 | 1.32 x 1.21 x 1.07 |  | `StylizedNatureMegaKit/glTF/Grass_Wispy_Short.gltf` |
| Grass_Wispy_Tall | 622 | 1.54 x 1.59 x 1.67 |  | `StylizedNatureMegaKit/glTF/Grass_Wispy_Tall.gltf` |
| Petal_1 | 13 | 0.46 x 0.45 x 0.24 |  | `StylizedNatureMegaKit/glTF/Petal_1.gltf` |
| Petal_2 | 15 | 0.67 x 0.63 x 0.24 |  | `StylizedNatureMegaKit/glTF/Petal_2.gltf` |
| Petal_3 | 15 | 0.62 x 0.61 x 0.19 |  | `StylizedNatureMegaKit/glTF/Petal_3.gltf` |
| Petal_4 | 30 | 0.33 x 0.24 x 0.25 |  | `StylizedNatureMegaKit/glTF/Petal_4.gltf` |
| Petal_5 | 15 | 0.83 x 0.8 x 0.29 |  | `StylizedNatureMegaKit/glTF/Petal_5.gltf` |
| Plant_1 | 120 | 1.27 x 1.39 x 1.01 |  | `StylizedNatureMegaKit/glTF/Plant_1.gltf` |
| Plant_1_Big | 360 | 1.81 x 1.95 x 2.35 |  | `StylizedNatureMegaKit/glTF/Plant_1_Big.gltf` |
| Plant_7 | 48 | 1.05 x 0.96 x 0.25 |  | `StylizedNatureMegaKit/glTF/Plant_7.gltf` |
| Plant_7_Big | 112 | 1.31 x 1.36 x 0.25 |  | `StylizedNatureMegaKit/glTF/Plant_7_Big.gltf` |

### Mushrooms

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Mushroom_Common | 880 | 0.56 x 0.78 x 0.46 |  | `StylizedNatureMegaKit/glTF/Mushroom_Common.gltf` |
| Mushroom_Laetiporus | 3216 | 1.37 x 1.1 x 0.77 | **HERO** | `StylizedNatureMegaKit/glTF/Mushroom_Laetiporus.gltf` |

### Rocks / pebbles / paths

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Pebble_Round_1 | 136 | 0.5 x 0.37 x 0.1 |  | `StylizedNatureMegaKit/glTF/Pebble_Round_1.gltf` |
| Pebble_Round_2 | 114 | 0.45 x 0.41 x 0.09 |  | `StylizedNatureMegaKit/glTF/Pebble_Round_2.gltf` |
| Pebble_Round_3 | 128 | 0.45 x 0.48 x 0.1 |  | `StylizedNatureMegaKit/glTF/Pebble_Round_3.gltf` |
| Pebble_Round_4 | 126 | 0.41 x 0.45 x 0.1 |  | `StylizedNatureMegaKit/glTF/Pebble_Round_4.gltf` |
| Pebble_Round_5 | 124 | 0.42 x 0.35 x 0.1 |  | `StylizedNatureMegaKit/glTF/Pebble_Round_5.gltf` |
| Pebble_Square_1 | 104 | 0.43 x 0.44 x 0.13 |  | `StylizedNatureMegaKit/glTF/Pebble_Square_1.gltf` |
| Pebble_Square_2 | 78 | 0.39 x 0.28 x 0.14 |  | `StylizedNatureMegaKit/glTF/Pebble_Square_2.gltf` |
| Pebble_Square_3 | 52 | 0.37 x 0.32 x 0.16 |  | `StylizedNatureMegaKit/glTF/Pebble_Square_3.gltf` |
| Pebble_Square_4 | 48 | 0.34 x 0.29 x 0.17 |  | `StylizedNatureMegaKit/glTF/Pebble_Square_4.gltf` |
| Pebble_Square_5 | 72 | 0.35 x 0.45 x 0.15 |  | `StylizedNatureMegaKit/glTF/Pebble_Square_5.gltf` |
| Pebble_Square_6 | 65 | 0.46 x 0.26 x 0.14 |  | `StylizedNatureMegaKit/glTF/Pebble_Square_6.gltf` |
| RockPath_Round_Small_1 | 998 | 1.06 x 1.48 x 0.11 |  | `StylizedNatureMegaKit/glTF/RockPath_Round_Small_1.gltf` |
| RockPath_Round_Small_2 | 1126 | 1.14 x 1.35 x 0.1 |  | `StylizedNatureMegaKit/glTF/RockPath_Round_Small_2.gltf` |
| RockPath_Round_Small_3 | 1002 | 1.18 x 1.29 x 0.11 |  | `StylizedNatureMegaKit/glTF/RockPath_Round_Small_3.gltf` |
| RockPath_Round_Thin | 2254 | 1.46 x 2.09 x 0.11 |  | `StylizedNatureMegaKit/glTF/RockPath_Round_Thin.gltf` |
| RockPath_Round_Wide | 3500 | 2.11 x 2.13 x 0.11 |  | `StylizedNatureMegaKit/glTF/RockPath_Round_Wide.gltf` |
| RockPath_Square_Small_1 | 783 | 1.02 x 0.97 x 0.15 |  | `StylizedNatureMegaKit/glTF/RockPath_Square_Small_1.gltf` |
| RockPath_Square_Small_2 | 559 | 0.99 x 0.97 x 0.15 |  | `StylizedNatureMegaKit/glTF/RockPath_Square_Small_2.gltf` |
| RockPath_Square_Small_3 | 568 | 0.84 x 1.08 x 0.17 |  | `StylizedNatureMegaKit/glTF/RockPath_Square_Small_3.gltf` |
| RockPath_Square_Thin | 1793 | 1.56 x 1.99 x 0.18 |  | `StylizedNatureMegaKit/glTF/RockPath_Square_Thin.gltf` |
| RockPath_Square_Wide | 2256 | 2.05 x 1.99 x 0.18 |  | `StylizedNatureMegaKit/glTF/RockPath_Square_Wide.gltf` |
| Rock_Medium_1 | 342 | 3.23 x 2.99 x 2.26 |  | `StylizedNatureMegaKit/glTF/Rock_Medium_1.gltf` |
| Rock_Medium_2 | 244 | 3.05 x 2.48 x 1.9 |  | `StylizedNatureMegaKit/glTF/Rock_Medium_2.gltf` |
| Rock_Medium_3 | 522 | 3.42 x 3.48 x 2.32 |  | `StylizedNatureMegaKit/glTF/Rock_Medium_3.gltf` |

## Ultimate Space Kit (March 2023)

- Folder: `UltimateSpaceKit/` | Page: https://quaternius.com/packs/ultimatespacekit.html | Formats: glTF, FBX, OBJ, .blend | Models measured: 92
- Preview: `UltimateSpaceKit/_preview.png`

### Characters / creatures (rigged)

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Astronaut_BarbaraTheBee | 8562 | 3.4 x 1.07 x 2.99 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Idle_Gun, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Gun, Run_Gun_Shoot, Walk, Walk_Gun, Wave, Weapon, Yes | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Characters/GLTF/Astronaut_BarbaraTheBee.gltf` |
| Astronaut_FernandoTheFlamingo | 7938 | 3.4 x 1.33 x 2.93 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Idle_Gun, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Gun, Run_Gun_Shoot, Walk, Walk_Gun, Wave, Weapon, Yes | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Characters/GLTF/Astronaut_FernandoTheFlamingo.gltf` |
| Astronaut_FinnTheFrog | 8606 | 3.4 x 1.61 x 2.74 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Idle_Gun, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Gun, Run_Gun_Shoot, Walk, Walk_Gun, Wave, Weapon, Yes | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Characters/GLTF/Astronaut_FinnTheFrog.gltf` |
| Astronaut_RaeTheRedPanda | 8032 | 3.4 x 1.43 x 3.06 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Idle_Gun, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Gun, Run_Gun_Shoot, Walk, Walk_Gun, Wave, Weapon, Yes | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Characters/GLTF/Astronaut_RaeTheRedPanda.gltf` |
| Enemy_ExtraSmall | 1572 | 0.92 x 0.92 x 1.69 | rigged 5 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Characters/GLTF/Enemy_ExtraSmall.gltf` |
| Enemy_Flying | 3820 | 1.26 x 1.48 x 3.6 | rigged 4 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Characters/GLTF/Enemy_Flying.gltf` |
| Enemy_Large | 4724 | 3.24 x 1.54 x 3.46 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Characters/GLTF/Enemy_Large.gltf` |
| Enemy_Small | 1856 | 1.25 x 1.49 x 2.22 | rigged 5 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Characters/GLTF/Enemy_Small.gltf` |
| Mech_BarbaraTheBee | 6756 | 3.14 x 2.52 x 2.68 | rigged 13 bones; anims: Dance, Death, Hello, HitRecieve_1, HitRecieve_2, Idle, Jump, Jump_Landing, Jump_NoHeight, Kick, No, Pickup, Run, Shoot_Big, Shoot_Small, Walk, Yes | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Characters/GLTF/Mech_BarbaraTheBee.gltf` |
| Mech_FernandoTheFlamingo | 4086 | 3.01 x 2.54 x 3.23 | rigged 13 bones; anims: Dance, Death, Hello, HitRecieve_1, HitRecieve_2, Idle, Jump, Jump_Landing, Jump_NoHeight, Kick, No, Pickup, Run, Shoot_Big, Shoot_Small, Walk, Yes | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Characters/GLTF/Mech_FernandoTheFlamingo.gltf` |
| Mech_FinnTheFrog | 5846 | 4.4 x 2.55 x 2.79 | rigged 13 bones; anims: Dance, Death, Hello, HitRecieve_1, HitRecieve_2, Idle, Jump, Jump_Landing, Jump_NoHeight, Kick, No, Pickup, Run, Shoot_Big, Shoot_Small, Walk, Yes | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Characters/GLTF/Mech_FinnTheFrog.gltf` |
| Mech_RaeTheRedPanda | 4008 | 3.01 x 2.3 x 2.78 | rigged 13 bones; anims: Dance, Death, Hello, HitRecieve_1, HitRecieve_2, Idle, Jump, Jump_Landing, Jump_NoHeight, Kick, No, Pickup, Run, Shoot_Big, Shoot_Small, Walk, Yes | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Characters/GLTF/Mech_RaeTheRedPanda.gltf` |

### Trees

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Tree_Blob_1 | 6112 | 3.86 x 3.86 x 5.88 | **HERO** | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Blob_1.gltf` |
| Tree_Blob_2 | 5776 | 3.69 x 3.86 x 4.61 | **HERO** | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Blob_2.gltf` |
| Tree_Blob_3 | 1892 | 2.8 x 2.77 x 3.42 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Blob_3.gltf` |
| Tree_Floating_1 | 2440 | 2.09 x 0.83 x 4.61 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Floating_1.gltf` |
| Tree_Floating_2 | 4048 | 2.63 x 0.84 x 5.87 | **HERO** | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Floating_2.gltf` |
| Tree_Floating_3 | 4079 | 3.87 x 0.84 x 5.21 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Floating_3.gltf` |
| Tree_Lava_1 | 1282 | 1.2 x 1.2 x 3.24 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Lava_1.gltf` |
| Tree_Lava_2 | 1174 | 1.23 x 1.15 x 3.08 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Lava_2.gltf` |
| Tree_Lava_3 | 1088 | 1.12 x 1.13 x 2.09 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Lava_3.gltf` |
| Tree_Light_1 | 2280 | 2.63 x 1.96 x 3.76 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Light_1.gltf` |
| Tree_Light_2 | 1080 | 1.45 x 1.51 x 2.51 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Light_2.gltf` |
| Tree_Spikes_1 | 2548 | 4.05 x 4.05 x 5.15 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Spikes_1.gltf` |
| Tree_Spikes_2 | 1698 | 2.42 x 2.11 x 4.49 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Spikes_2.gltf` |
| Tree_Spiral_1 | 748 | 2.36 x 2.23 x 4.49 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Spiral_1.gltf` |
| Tree_Spiral_2 | 1490 | 3.8 x 2.2 x 6.19 | **HERO** | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Spiral_2.gltf` |
| Tree_Spiral_3 | 1280 | 4.22 x 2.54 x 4.05 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Spiral_3.gltf` |
| Tree_Swirl_1 | 2010 | 4.61 x 1.68 x 7.35 | **HERO** | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Swirl_1.gltf` |
| Tree_Swirl_2 | 1112 | 3.07 x 1.15 x 5.15 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Tree_Swirl_2.gltf` |

### Bushes / shrubs

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Bush_1 | 2304 | 3.26 x 0.98 x 2.48 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Bush_1.gltf` |
| Bush_2 | 1504 | 1.82 x 0.62 x 1.6 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Bush_2.gltf` |
| Bush_3 | 640 | 1.86 x 0.63 x 1.58 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Bush_3.gltf` |

### Grass / ground cover / small plants

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Grass_1 | 246 | 1.27 x 0.91 x 0.99 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Grass_1.gltf` |
| Grass_2 | 96 | 1.7 x 1.17 x 1.4 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Grass_2.gltf` |
| Grass_3 | 408 | 2.23 x 1.49 x 2.38 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Grass_3.gltf` |
| Plant_1 | 540 | 1.8 x 0.64 x 2.18 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Plant_1.gltf` |
| Plant_2 | 196 | 1.06 x 1.01 x 1.97 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Plant_2.gltf` |
| Plant_3 | 1608 | 2.12 x 1.44 x 2.98 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Plant_3.gltf` |
| Spaceship_FernandoTheFlamingo | 2814 | 11.14 x 8.66 x 2.53 | **HERO** | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Vehicles/GLTF/Spaceship_FernandoTheFlamingo.gltf` |

### Rocks / pebbles / paths

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Rock_1 | 224 | 3.1 x 2.83 x 3.61 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Rock_1.gltf` |
| Rock_2 | 210 | 2.74 x 2.52 x 2.71 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Rock_2.gltf` |
| Rock_3 | 224 | 3.3 x 3.01 x 3.83 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Rock_3.gltf` |
| Rock_4 | 456 | 2.16 x 1.7 x 3.46 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Rock_4.gltf` |
| Rock_Large_1 | 222 | 7.67 x 7.33 x 3.29 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Rock_Large_1.gltf` |
| Rock_Large_2 | 432 | 8.54 x 7.62 x 8.21 | **HERO** | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Rock_Large_2.gltf` |
| Rock_Large_3 | 448 | 5.31 x 5.19 x 7.43 | **HERO** | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Rock_Large_3.gltf` |

### Buildings / base / ruins (modular)

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Base_Large | 2790 | 8.53 x 8.53 x 4.97 | **HERO** | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Base_Large.gltf` |
| Building_L | 2940 | 7.8 x 7.79 x 4.31 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Building_L.gltf` |
| Connector | 508 | 3.37 x 2.17 x 2.21 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Connector.gltf` |
| GeodesicDome | 1432 | 8.53 x 8.53 x 5.28 | **HERO** | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/GeodesicDome.gltf` |
| House_Cylinder | 1166 | 5.61 x 5.61 x 4.32 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/House_Cylinder.gltf` |
| House_Long | 2228 | 3.99 x 7.79 x 4.31 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/House_Long.gltf` |
| House_Open | 1156 | 3.99 x 3.61 x 4 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/House_Open.gltf` |
| House_OpenBack | 1180 | 3.99 x 3.61 x 4 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/House_OpenBack.gltf` |
| House_Single | 1080 | 3.99 x 3.8 x 4 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/House_Single.gltf` |
| House_Single_Support | 464 | 3.58 x 3.58 x 0.87 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/House_Single_Support.gltf` |
| MetalSupport | 540 | 0.14 x 5.95 x 1.2 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/MetalSupport.gltf` |
| Ramp | 192 | 1.87 x 3.11 x 1.39 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Ramp.gltf` |
| Roof_Antenna | 492 | 1.41 x 1.43 x 3.54 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Roof_Antenna.gltf` |
| Roof_Opening | 350 | 1.41 x 1.43 x 1.2 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Roof_Opening.gltf` |
| Roof_Radar | 972 | 1.63 x 1.65 x 2.71 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Roof_Radar.gltf` |
| Roof_VentL | 140 | 1.15 x 1.43 x 1.15 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Roof_VentL.gltf` |
| Roof_VentR | 140 | 1.15 x 1.43 x 1.15 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Roof_VentR.gltf` |
| SolarPanel_Ground | 372 | 1.29 x 1.67 x 1.1 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/SolarPanel_Ground.gltf` |
| SolarPanel_Roof | 812 | 2.73 x 1.73 x 1.7 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/SolarPanel_Roof.gltf` |
| SolarPanel_Structure | 1432 | 4 x 4 x 3.07 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/SolarPanel_Structure.gltf` |
| Stairs | 256 | 1.87 x 3.11 x 1.39 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Stairs.gltf` |

### Vehicles

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Pickup_KeyCard | 256 | 1.04 x 0.09 x 0.67 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Items/GLTF/Pickup_KeyCard.gltf` |
| Rover_1 | 7346 | 4.58 x 5.16 x 4.88 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Vehicles/GLTF/Rover_1.gltf` |
| Rover_2 | 8032 | 4.58 x 6.56 x 4.88 | **HERO** | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Vehicles/GLTF/Rover_2.gltf` |
| Rover_Round | 7052 | 5.79 x 3.69 x 5.17 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Vehicles/GLTF/Rover_Round.gltf` |
| Spaceship_BarbaraTheBee | 6208 | 7.34 x 4.96 x 5.7 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Vehicles/GLTF/Spaceship_BarbaraTheBee.gltf` |
| Spaceship_FinnTheFrog | 3376 | 11.62 x 4.11 x 3.06 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Vehicles/GLTF/Spaceship_FinnTheFrog.gltf` |
| Spaceship_RaeTheRedPanda | 1614 | 9.95 x 11.17 x 2.35 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Vehicles/GLTF/Spaceship_RaeTheRedPanda.gltf` |

### Planets (sky dressing)

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Planet_1 | 2672 | 3.78 x 3.8 x 3.93 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Planet_1.gltf` |
| Planet_10 | 2586 | 5.74 x 5.74 x 4.68 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Planet_10.gltf` |
| Planet_11 | 2178 | 5.59 x 5.74 x 5.67 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Planet_11.gltf` |
| Planet_2 | 2720 | 3.8 x 3.84 x 3.82 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Planet_2.gltf` |
| Planet_3 | 2400 | 3.63 x 3.38 x 3.65 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Planet_3.gltf` |
| Planet_4 | 2622 | 4.49 x 3.96 x 4.09 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Planet_4.gltf` |
| Planet_5 | 1320 | 4.23 x 4.03 x 4.52 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Planet_5.gltf` |
| Planet_6 | 1598 | 3.76 x 3.76 x 3.75 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Planet_6.gltf` |
| Planet_7 | 2010 | 4.81 x 4.46 x 2.87 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Planet_7.gltf` |
| Planet_8 | 1070 | 3.45 x 3.75 x 3.75 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Planet_8.gltf` |
| Planet_9 | 1864 | 3.82 x 3.81 x 3.75 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Environment/GLTF/Planet_9.gltf` |

### Props

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Pickup_Bullets | 624 | 0.83 x 0.28 x 0.84 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Items/GLTF/Pickup_Bullets.gltf` |
| Pickup_Crate | 1348 | 0.87 x 0.9 x 0.86 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Items/GLTF/Pickup_Crate.gltf` |
| Pickup_Health | 684 | 0.97 x 0.44 x 1 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Items/GLTF/Pickup_Health.gltf` |
| Pickup_Jar | 308 | 0.69 x 0.69 x 1.02 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Items/GLTF/Pickup_Jar.gltf` |
| Pickup_Sphere | 1824 | 0.89 x 0.89 x 0.89 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Items/GLTF/Pickup_Sphere.gltf` |
| Pickup_Thunder | 228 | 0.97 x 0.88 x 0.86 |  | `UltimateSpaceKit/Ultimate Space Kit - March 2023/Items/GLTF/Pickup_Thunder.gltf` |

## Zombie Apocalypse Kit (March 2024)

- Folder: `ZombieApocalypseKit/` | Page: https://quaternius.com/packs/zombieapocalypsekit.html | Formats: glTF, FBX, OBJ, .blend | Models measured: 64
- Preview: `ZombieApocalypseKit/_preview.png`

### Characters / creatures (rigged)

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Characters_GermanShepherd | 4898 | 0.49 x 1.5 x 0.91 | rigged 50 bones; anims: Attack, Death, Eating, HitReact_Left, HitReact_Right, Idle, Idle_2, Idle_2_HeadLow, Run, Run_Jump, Walk | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Characters/glTF/Characters_GermanShepherd.gltf` |
| Characters_Lis | 25855 | 1.19 x 1.76 x 1.53 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Idle_Gun, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Gun, Run_Slash, Run_Stab, Slash, Stab, Walk, Walk_Gun, Wave, Yes | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Characters/glTF/Characters_Lis.gltf` |
| Characters_Lis_SingleWeapon | 8921 | 1.14 x 1.6 x 1.53 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Idle_Gun, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Gun, Run_Slash, Run_Stab, Slash, Stab, Walk, Walk_Gun, Wave, Yes | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Characters/glTF/Characters_Lis_SingleWeapon.gltf` |
| Characters_Matt | 25469 | 1.19 x 1.76 x 1.42 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Idle_Gun, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Gun, Run_Slash, Run_Stab, Slash, Stab, Walk, Walk_Gun, Wave, Yes | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Characters/glTF/Characters_Matt.gltf` |
| Characters_Matt_SingleWeapon | 9378 | 1.19 x 1.21 x 1.35 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Idle_Gun, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Gun, Run_Slash, Run_Stab, Slash, Stab, Walk, Walk_Gun, Wave, Yes | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Characters/glTF/Characters_Matt_SingleWeapon.gltf` |
| Characters_Pug | 3603 | 0.44 x 1.16 x 0.72 | rigged 36 bones; anims: Attack, Death, Eating, HitReact_Left, HitReact_Right, Idle, Idle_2, Idle_2_HeadLow, Run, Run_Jump, Walk | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Characters/glTF/Characters_Pug.gltf` |
| Characters_Sam | 28105 | 1.19 x 1.76 x 1.42 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Idle_Gun, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Gun, Run_Slash, Run_Stab, Slash, Stab, Walk, Walk_Gun, Wave, Yes | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Characters/glTF/Characters_Sam.gltf` |
| Characters_Sam_SingleWeapon | 10292 | 1.13 x 1.35 x 1.37 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Idle_Gun, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Gun, Run_Slash, Run_Stab, Slash, Stab, Walk, Walk_Gun, Wave, Yes | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Characters/glTF/Characters_Sam_SingleWeapon.gltf` |
| Characters_Shaun | 27713 | 1.19 x 1.89 x 1.42 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Idle_Gun, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Gun, Run_Slash, Run_Stab, Slash, Stab, Walk, Walk_Gun, Wave, Yes | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Characters/glTF/Characters_Shaun.gltf` |
| Characters_Shaun_SingleWeapon | 10951 | 1.12 x 1.54 x 1.41 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Idle_Gun, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Gun, Run_Slash, Run_Stab, Slash, Stab, Walk, Walk_Gun, Wave, Yes | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Characters/glTF/Characters_Shaun_SingleWeapon.gltf` |
| Zombie_Arm | 5670 | 2.09 x 0.68 x 1.44 | rigged 45 bones; anims: Death, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Arms, Run_Attack, Walk, Wave, Yes | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Characters/glTF/Zombie_Arm.gltf` |
| Zombie_Basic | 7822 | 0.94 x 1.74 x 0.68 | rigged 50 bones; anims: Crawl, Death, HitReact, Idle, Idle_Attack, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Arms, Run_Attack, Walk, Wave, Yes | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Characters/glTF/Zombie_Basic.gltf` |
| Zombie_Chubby | 6174 | 1.18 x 2.39 x 0.84 | rigged 50 bones; anims: Crawl, Death, HitReact, Idle, Idle_Attack, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Run_Arms, Run_Attack, Walk, Wave, Yes | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Characters/glTF/Zombie_Chubby.gltf` |
| Zombie_Ribcage | 4774 | 0.77 x 1.25 x 0.37 | rigged 12 bones; anims: Crawl, Death, HitReact, Idle, Jump, Jump_Idle, Jump_Land, Run, Walk | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Characters/glTF/Zombie_Ribcage.gltf` |

### Buildings / base / ruins (modular)

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Container_Green | 1336 | 5.71 x 2.56 x 2.6 | **HERO** | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Container_Green.gltf` |
| Container_Red | 1032 | 5.71 x 2.56 x 2.6 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Container_Red.gltf` |
| StreetLights | 426 | 0.36 x 2.93 x 6.64 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/StreetLights.gltf` |
| Street_4Way | 188 | 8 x 8 x 0.1 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Street_4Way.gltf` |
| Street_Straight | 228 | 8 x 8 x 0.12 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Street_Straight.gltf` |
| Street_Straight_Crack1 | 576 | 8 x 8 x 0.29 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Street_Straight_Crack1.gltf` |
| Street_Straight_Crack2 | 676 | 8 x 8 x 0.58 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Street_Straight_Crack2.gltf` |
| Street_T | 180 | 8 x 8 x 0.1 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Street_T.gltf` |
| Street_Turn | 220 | 8 x 8 x 0.12 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Street_Turn.gltf` |
| TownSign | 1397 | 5.98 x 1.74 x 5.35 | **HERO** | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/TownSign.gltf` |
| WaterTower | 1158 | 2.65 x 2.71 x 9.38 | **HERO** | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/WaterTower.gltf` |

### Vehicles

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Wheel | 608 | 0.57 x 0.57 x 0.2 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Wheel.gltf` |
| Wheels_Stack | 1824 | 0.66 x 0.57 x 0.61 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Wheels_Stack.gltf` |
| Vehicle_Pickup | 6432 | 2.31 x 5.18 x 1.85 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Vehicles/glTF/Vehicle_Pickup.gltf` |
| Vehicle_Pickup_Armored | 13160 | 2.65 x 5.51 x 2 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Vehicles/glTF/Vehicle_Pickup_Armored.gltf` |
| Vehicle_Sports | 5804 | 2.67 x 5.66 x 1.86 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Vehicles/glTF/Vehicle_Sports.gltf` |
| Vehicle_Sports_Armored | 10030 | 2.95 x 5.66 x 1.86 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Vehicles/glTF/Vehicle_Sports_Armored.gltf` |
| Vehicle_Truck | 7476 | 2.71 x 5.26 x 2.88 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Vehicles/glTF/Vehicle_Truck.gltf` |
| Vehicle_Truck_Armored | 16134 | 2.98 x 5.59 x 2.9 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Vehicles/glTF/Vehicle_Truck_Armored.gltf` |

### Weapons

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Axe | 790 | 0.3 x 1.3 x 0.09 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Weapons/glTF/Axe.gltf` |
| Guitar | 2325 | 0.72 x 1.8 x 0.13 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Weapons/glTF/Guitar.gltf` |
| Knife | 860 | 0.15 x 0.82 x 0.08 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Weapons/glTF/Knife.gltf` |
| Pistol | 1446 | 0.14 x 0.98 x 0.34 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Weapons/glTF/Pistol.gltf` |
| Rifle | 2103 | 0.11 x 1.64 x 0.52 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Weapons/glTF/Rifle.gltf` |
| SMG | 2497 | 0.15 x 0.99 x 0.47 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Weapons/glTF/SMG.gltf` |
| Shotgun | 1542 | 0.1 x 1.11 x 0.34 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Weapons/glTF/Shotgun.gltf` |
| Spear | 3200 | 0.14 x 2.01 x 0.15 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Weapons/glTF/Spear.gltf` |
| WoodenBat_Barbed | 2188 | 0.18 x 1.24 x 0.19 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Weapons/glTF/WoodenBat_Barbed.gltf` |
| WoodenBat_Saw | 2308 | 0.38 x 1.37 x 0.21 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Weapons/glTF/WoodenBat_Saw.gltf` |

### Props

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Barrel | 882 | 0.7 x 0.7 x 1.14 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Barrel.gltf` |
| Blood_1 | 130 | 3.41 x 3.56 x 0 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Blood_1.gltf` |
| Blood_2 | 74 | 1.71 x 1.32 x 0 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Blood_2.gltf` |
| Blood_3 | 82 | 1.72 x 2.14 x 0 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Blood_3.gltf` |
| Chest | 3190 | 0.64 x 0.48 x 0.41 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Chest.gltf` |
| Chest_Special | 3422 | 0.85 x 0.48 x 0.41 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Chest_Special.gltf` |
| CinderBlock | 368 | 0.47 x 0.21 x 0.23 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/CinderBlock.gltf` |
| Couch | 3078 | 3.01 x 1.21 x 1.24 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Couch.gltf` |
| FireHydrant | 976 | 0.52 x 0.4 x 0.77 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/FireHydrant.gltf` |
| Pallet | 240 | 0.89 x 1.22 x 0.14 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Pallet.gltf` |
| Pallet_Broken | 216 | 0.92 x 1.22 x 0.16 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Pallet_Broken.gltf` |
| Pipes | 1496 | 0.75 x 3.36 x 0.67 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/Pipes.gltf` |
| PlasticBarrier | 852 | 1.04 x 0.33 x 0.6 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/PlasticBarrier.gltf` |
| TrafficBarrier_1 | 732 | 1.56 x 0.88 x 1.11 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/TrafficBarrier_1.gltf` |
| TrafficBarrier_2 | 364 | 1.56 x 0.78 x 0.8 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/TrafficBarrier_2.gltf` |
| TrafficCone_1 | 134 | 0.52 x 0.52 x 0.67 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/TrafficCone_1.gltf` |
| TrafficCone_2 | 460 | 0.6 x 0.6 x 0.74 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/TrafficCone_2.gltf` |
| TrafficLight_1 | 849 | 1.51 x 1.51 x 4.66 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/TrafficLight_1.gltf` |
| TrafficLight_2 | 1369 | 5.34 x 1.92 x 4.66 | **HERO** | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/TrafficLight_2.gltf` |
| TrashBag_1 | 1044 | 0.5 x 0.5 x 0.56 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/TrashBag_1.gltf` |
| TrashBag_2 | 2088 | 0.91 x 0.52 x 0.53 |  | `ZombieApocalypseKit/Zombie Apocalypse Kit - March 2024/Environment/glTF/TrashBag_2.gltf` |

## Ultimate Modular Ruins Pack (Aug 2021)

- Folder: `UltimateModularRuins/` | Page: https://quaternius.com/packs/ultimatemodularruins.html | Formats: FBX, OBJ, .blend (no glTF) | Models measured: 92
- Preview: `UltimateModularRuins/_preview.png`

### Characters / creatures (rigged)

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Character_Animated | 6050 | 1.02 x 1.65 x 2.76 | rigged 42 bones; anims: Attacking_Idle, Dagger_Attack, Dagger_Attack2, Death, Idle, PickUp, Punch, RecieveHit, RecieveHit_Attacking, Roll, Run, Walk | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Character_Animated.fbx` |

### Trees

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| DeadTree_1 | 444 | 1.22 x 0.76 x 2.59 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/DeadTree_1.fbx` |
| DeadTree_2 | 516 | 1.45 x 0.24 x 2.62 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/DeadTree_2.fbx` |
| DeadTree_3 | 1392 | 2.25 x 2.26 x 2.81 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/DeadTree_3.fbx` |
| Tree_1 | 804 | 2.07 x 2.07 x 2.77 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Tree_1.fbx` |
| Tree_2 | 1816 | 2.72 x 2.19 x 2.86 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Tree_2.fbx` |
| Tree_3 | 1332 | 2.77 x 2.24 x 2.93 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Tree_3.fbx` |

### Bushes / shrubs

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Bush_1x1 | 516 | 1.12 x 1.19 x 1.2 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Bush_1x1.fbx` |
| Bush_2x1 | 652 | 1.19 x 1.19 x 1.63 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Bush_2x1.fbx` |
| Bush_2x2 | 956 | 1.8 x 1.19 x 1.63 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Bush_2x2.fbx` |
| Bush_Large | 360 | 2.07 x 2.07 x 1.19 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Bush_Large.fbx` |
| Bush_Round | 312 | 1.25 x 1.25 x 0.71 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Bush_Round.fbx` |

### Grass / ground cover / small plants

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Grass | 192 | 0.37 x 0.33 x 1.01 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Grass.fbx` |

### Buildings / base / ruins (modular)

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Arch_Gothic | 2904 | 3.09 x 0.49 x 3.76 | **HERO** | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Arch_Gothic.fbx` |
| Arch_Gothic_RoundColumn | 3224 | 3.09 x 0.49 x 3.76 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Arch_Gothic_RoundColumn.fbx` |
| Arch_Round | 2956 | 3.09 x 0.49 x 3.53 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Arch_Round.fbx` |
| Arch_Round_RoundColumn | 3276 | 3.09 x 0.49 x 3.53 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Arch_Round_RoundColumn.fbx` |
| BridgeSection | 1888 | 2.58 x 2.23 x 0.44 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/BridgeSection.fbx` |
| Column_BridgeSupport | 1242 | 0.78 x 0.62 x 4.02 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Column_BridgeSupport.fbx` |
| Column_Round | 1010 | 0.66 x 0.66 x 3.99 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Column_Round.fbx` |
| Column_Round_Short | 634 | 0.49 x 0.49 x 1.83 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Column_Round_Short.fbx` |
| Column_Square | 690 | 0.66 x 0.66 x 3.99 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Column_Square.fbx` |
| Curve_1 | 2302 | 2.27 x 2.07 x 2 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Curve_1.fbx` |
| Curve_1_Overgrown | 2444 | 2.3 x 2.07 x 2 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Curve_1_Overgrown.fbx` |
| Curve_2 | 2302 | 2.27 x 2.07 x 2 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Curve_2.fbx` |
| Curve_2_Overgrown | 2444 | 2.3 x 2.07 x 2 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Curve_2_Overgrown.fbx` |
| Doors_GothicArch | 2184 | 2.31 x 0.27 x 3.21 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Doors_GothicArch.fbx` |
| Doors_GothicArch_Covered | 2096 | 2.52 x 0.28 x 3.21 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Doors_GothicArch_Covered.fbx` |
| Doors_RoundArch | 2184 | 2.31 x 0.27 x 2.97 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Doors_RoundArch.fbx` |
| Doors_RoundArch_Covered | 2096 | 2.52 x 0.28 x 2.97 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Doors_RoundArch_Covered.fbx` |
| Flag_GothicArch | 144 | 2.19 x 0.32 x 1.22 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Flag_GothicArch.fbx` |
| Flag_RoundArch | 132 | 2.17 x 0.32 x 1.13 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Flag_RoundArch.fbx` |
| Flag_Wall | 204 | 0.92 x 0.32 x 2.02 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Flag_Wall.fbx` |
| Flag_Wall2 | 368 | 1.13 x 0.32 x 2.35 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Flag_Wall2.fbx` |
| Floor_Diamond | 400 | 2 x 2 x 0.12 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Floor_Diamond.fbx` |
| Floor_Hole_Corner | 327 | 1.99 x 2 x 0.14 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Floor_Hole_Corner.fbx` |
| Floor_Hole_Straight | 227 | 2 x 1.1 x 0.14 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Floor_Hole_Straight.fbx` |
| Floor_SquareLarge | 118 | 1.98 x 1.98 x 0.11 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Floor_SquareLarge.fbx` |
| Floor_Squares | 413 | 1.99 x 2 x 0.12 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Floor_Squares.fbx` |
| Floor_Standard | 1304 | 1.99 x 1.98 x 0.29 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Floor_Standard.fbx` |
| Floor_Standard_Half | 821 | 2 x 2 x 0.12 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Floor_Standard_Half.fbx` |
| Floor_Tree | 341 | 1.99 x 2 x 0.15 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Floor_Tree.fbx` |
| Rail_Corner | 468 | 1.17 x 1.17 x 0.49 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Rail_Corner.fbx` |
| Rail_Divider | 208 | 0.36 x 0.36 x 0.49 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Rail_Divider.fbx` |
| Rail_Straight | 428 | 0.36 x 2 x 0.49 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Rail_Straight.fbx` |
| Stairs | 2272 | 2.02 x 2.15 x 0.92 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Stairs.fbx` |
| Stairs_2 | 2072 | 2.15 x 2.02 x 1.78 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Stairs_2.fbx` |
| Support_Center | 4432 | 3 x 0.66 x 4.11 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Support_Center.fbx` |
| Support_Left | 3570 | 1.65 x 0.66 x 4.1 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Support_Left.fbx` |
| Support_Right | 3570 | 1.65 x 0.66 x 4.1 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Support_Right.fbx` |
| Support_Tall | 674 | 0.8 x 0.65 x 4.12 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Support_Tall.fbx` |
| Trapdoor | 506 | 1.74 x 1.57 x 0.22 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Trapdoor.fbx` |
| Wall | 1296 | 2 x 0.29 x 2 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Wall.fbx` |
| Wall_ArchGothic | 2352 | 4 x 0.29 x 3.99 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Wall_ArchGothic.fbx` |
| Wall_ArchRound | 2364 | 4 x 0.31 x 3.99 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Wall_ArchRound.fbx` |
| Wall_ArchRound_Broken | 1604 | 3.99 x 0.31 x 3.98 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Wall_ArchRound_Broken.fbx` |
| Wall_ArchRound_Overgrown | 2602 | 4 x 0.32 x 3.99 | **HERO** | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Wall_ArchRound_Overgrown.fbx` |
| Wall_ArchRound_Overgrown_Broken | 1826 | 3.99 x 0.32 x 3.98 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Wall_ArchRound_Overgrown_Broken.fbx` |
| Wall_Broken | 976 | 1.99 x 0.29 x 1.95 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Wall_Broken.fbx` |
| Wall_Double_Broken | 856 | 1.99 x 0.57 x 0.99 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Wall_Double_Broken.fbx` |
| Wall_Double_Hole | 1880 | 1.99 x 0.57 x 1.98 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Wall_Double_Hole.fbx` |
| Wall_Half | 632 | 1 x 0.29 x 2 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Wall_Half.fbx` |
| Wall_Hole | 912 | 2 x 0.29 x 2 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Wall_Hole.fbx` |
| Wall_Overgrown | 1370 | 1.99 x 0.3 x 1.98 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Wall_Overgrown.fbx` |
| Window_Bars | 1222 | 1.99 x 0.3 x 1.99 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Window_Bars.fbx` |
| Window_Bars_Double_Overgrown | 2192 | 2.01 x 0.31 x 3.99 | **HERO** | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Window_Bars_Double_Overgrown.fbx` |
| Window_Bars_Overgrown | 1352 | 1.99 x 0.31 x 1.99 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Window_Bars_Overgrown.fbx` |
| Window_Open | 1148 | 1.99 x 0.3 x 1.99 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Window_Open.fbx` |
| Window_Open_Double | 1952 | 1.99 x 0.3 x 3.99 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Window_Open_Double.fbx` |

### Vehicles

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Cart | 1432 | 3.31 x 2.83 x 1.38 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Cart.fbx` |

### Props

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Barrel | 1312 | 0.83 x 0.82 x 1.07 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Barrel.fbx` |
| BearTrap_Closed | 608 | 1.13 x 1.42 x 0.68 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/BearTrap_Closed.fbx` |
| BearTrap_Open | 608 | 1.2 x 1.42 x 0.27 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/BearTrap_Open.fbx` |
| Bookcase_Empty | 1260 | 2.08 x 0.66 x 2.65 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Bookcase_Empty.fbx` |
| Bookcase_Full | 3360 | 2.08 x 0.66 x 2.65 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Bookcase_Full.fbx` |
| Brick | 76 | 0.53 x 0.28 x 0.32 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Brick.fbx` |
| Bricks | 312 | 1.82 x 1.61 x 0.55 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Bricks.fbx` |
| Candles_1 | 844 | 0.88 x 0.84 x 0.61 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Candles_1.fbx` |
| Candles_2 | 1224 | 0.99 x 0.99 x 0.65 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Candles_2.fbx` |
| Chest | 1676 | 1.18 x 0.83 x 0.91 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Chest.fbx` |
| Chest_Gold | 22512 | 1.18 x 0.82 x 0.91 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Chest_Gold.fbx` |
| Crate | 784 | 0.82 x 0.82 x 0.82 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Crate.fbx` |
| Pot1 | 1038 | 0.77 x 0.77 x 0.96 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Pot1.fbx` |
| Pot1_Broken | 432 | 0.77 x 0.77 x 0.66 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Pot1_Broken.fbx` |
| Pot2 | 878 | 0.46 x 0.46 x 0.64 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Pot2.fbx` |
| Pot2_Broken | 322 | 0.46 x 0.46 x 0.43 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Pot2_Broken.fbx` |
| Pot3 | 750 | 0.46 x 0.46 x 0.84 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Pot3.fbx` |
| Pot3_Broken | 188 | 0.46 x 0.46 x 0.33 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Pot3_Broken.fbx` |
| Skull | 426 | 0.44 x 0.6 x 0.46 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Skull.fbx` |
| Statue_Fox | 2152 | 1.35 x 1.68 x 3.75 | **HERO** | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Statue_Fox.fbx` |
| Statue_Stag | 4042 | 2.31 x 1.27 x 4.63 | **HERO** | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Statue_Stag.fbx` |
| Torch | 386 | 0.28 x 0.44 x 1.17 |  | `UltimateModularRuins/Ultimate Modular Ruins Pack - Aug 2021/FBX/Torch.fbx` |

## Ultimate Monsters

- Folder: `UltimateMonsters/` | Page: https://quaternius.com/packs/ultimatemonsters.html | Formats: glTF, FBX, OBJ, .blend | Models measured: 50
- Preview: `UltimateMonsters/_preview.png`

### Characters / creatures (rigged)

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Alien (Big) | 7676 | 3.23 x 2 x 3.04 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/Alien.gltf` |
| Birb (Big) | 5704 | 3.24 x 1.81 x 3.17 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/Birb.gltf` |
| BlueDemon (Big) | 5799 | 3.16 x 1.79 x 2.51 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/BlueDemon.gltf` |
| Bunny (Big) | 8282 | 3.22 x 2.1 x 3.22 | rigged 49 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/Bunny.gltf` |
| Cactoro (Big) | 6398 | 3.22 x 2.5 x 3.57 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/Cactoro.gltf` |
| Demon (Big) | 6712 | 3.66 x 2.42 x 2.74 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/Demon.gltf` |
| Dino (Big) | 5414 | 3.24 x 2.03 x 2.83 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/Dino.gltf` |
| Fish (Big) | 6854 | 3.25 x 2.36 x 3.55 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/Fish.gltf` |
| Frog (Big) | 5016 | 3.23 x 1.77 x 2.27 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/Frog.gltf` |
| Monkroose (Big) | 5824 | 3.23 x 1.85 x 2.67 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/Monkroose.gltf` |
| MushroomKing (Big) | 6044 | 3.37 x 2.34 x 3.31 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/MushroomKing.gltf` |
| Ninja (Big) | 5964 | 3.13 x 2.69 x 2.9 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/Ninja.gltf` |
| Orc (Big) | 7344 | 3.28 x 1.94 x 2.97 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/Orc.gltf` |
| Orc_Skull (Big) | 7363 | 3.23 x 1.91 x 3.08 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/Orc_Skull.gltf` |
| Tribal (Big) | 6620 | 3.29 x 1.92 x 3.39 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/Tribal.gltf` |
| Yeti (Big) | 6094 | 3.23 x 1.65 x 2.42 | rigged 43 bones; anims: Death, Duck, HitReact, Idle, Jump, Jump_Idle, Jump_Land, No, Punch, Run, Walk, Wave, Weapon, Yes | `UltimateMonsters/Ultimate Monsters/Big/glTF/Yeti.gltf` |
| Alien (Blob) | 2616 | 3.87 x 1.93 x 3.27 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/Alien.gltf` |
| Birb (Blob) | 3164 | 2.8 x 2.84 x 2.57 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/Birb.gltf` |
| Cactoro (Blob) | 2388 | 4.08 x 3.69 x 3.6 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/Cactoro.gltf` |
| Cat (Blob) | 1772 | 2.1 x 1.71 x 1.97 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/Cat.gltf` |
| Chicken (Blob) | 2904 | 2.35 x 2.09 x 2.37 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/Chicken.gltf` |
| Dog (Blob) | 1392 | 2.14 x 1.72 x 1.83 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/Dog.gltf` |
| Fish (Blob) | 3346 | 2.8 x 2.87 x 2.71 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/Fish.gltf` |
| GreenBlob (Blob) | 1520 | 2.25 x 2.21 x 1.86 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/GreenBlob.gltf` |
| GreenSpikyBlob (Blob) | 4888 | 3.5 x 4.14 x 4.14 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/GreenSpikyBlob.gltf` |
| Mushnub (Blob) | 1248 | 2.75 x 2.75 x 3.31 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/Mushnub.gltf` |
| Mushnub_Evolved (Blob) | 3072 | 3.41 x 3.47 x 4.45 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/Mushnub_Evolved.gltf` |
| Ninja (Blob) | 2160 | 2.48 x 2.64 x 3.02 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/Ninja.gltf` |
| Orc (Blob) | 2296 | 2.63 x 1.66 x 2.38 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/Orc.gltf` |
| Pigeon (Blob) | 2184 | 2.35 x 2 x 1.8 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/Pigeon.gltf` |
| PinkBlob (Blob) | 1030 | 1.83 x 1.72 x 2.03 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/PinkBlob.gltf` |
| Wizard (Blob) | 1674 | 2.33 x 2.31 x 2.6 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/Wizard.gltf` |
| Yeti (Blob) | 2136 | 2.55 x 2.56 x 2.45 | rigged 4 bones; anims: Bite_Front, Dance, Death, HitRecieve, Idle, Jump, No, Walk, Yes | `UltimateMonsters/Ultimate Monsters/Blob/glTF/Yeti.gltf` |
| Alpaking (Flying) | 2508 | 4.45 x 2.25 x 2.14 | rigged 13 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Alpaking.gltf` |
| Alpaking_Evolved (Flying) | 4684 | 4.44 x 2.87 x 3.12 | rigged 13 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Alpaking_Evolved.gltf` |
| Armabee (Flying) | 2280 | 4.45 x 2.12 x 1.89 | rigged 13 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Armabee.gltf` |
| Armabee_Evolved (Flying) | 3200 | 4.45 x 2.15 x 2.12 | rigged 13 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Armabee_Evolved.gltf` |
| Demon (Flying) | 4784 | 4.55 x 2.63 x 2.2 | rigged 43 bones; anims: Flying_Idle | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Demon.gltf` |
| Dragon (Flying) | 4562 | 4.54 x 2.4 x 1.69 | rigged 13 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Dragon.gltf` |
| Dragon_Evolved (Flying) | 7440 | 4.55 x 2.87 x 2.86 | rigged 46 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Dragon_Evolved.gltf` |
| Ghost (Flying) | 3192 | 2.94 x 2.05 x 3.02 | rigged 38 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Ghost.gltf` |
| Ghost_Skull (Flying) | 3146 | 2.94 x 2.27 x 2.96 | rigged 38 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Ghost_Skull.gltf` |
| Glub (Flying) | 2528 | 4.45 x 2.11 x 2.22 | rigged 13 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Glub.gltf` |
| Glub_Evolved (Flying) | 4452 | 4.45 x 2.04 x 3.61 | rigged 13 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Glub_Evolved.gltf` |
| Goleling (Flying) | 3696 | 4.55 x 1.94 x 1.67 | rigged 13 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Goleling.gltf` |
| Goleling_Evolved (Flying) | 5864 | 4.55 x 2.09 x 2.45 | rigged 13 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Goleling_Evolved.gltf` |
| Hywirl (Flying) | 3296 | 2.95 x 2.48 x 2.76 | rigged 38 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Hywirl.gltf` |
| Pigeon (Flying) | 3512 | 4.3 x 2.07 x 1.36 | rigged 13 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Pigeon.gltf` |
| Squidle (Flying) | 4880 | 4.55 x 2.87 x 2.26 | rigged 43 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Squidle.gltf` |
| Tribal (Flying) | 5252 | 3.16 x 2.33 x 4.08 | rigged 38 bones; anims: Death, Fast_Flying, Flying_Idle, Headbutt, HitReact, No, Punch, Yes | `UltimateMonsters/Ultimate Monsters/Flying/glTF/Tribal.gltf` |

## Cars Pack (Realistic Car Pack, Nov 2018)

- Folder: `CarsPack/` | Page: https://quaternius.com/packs/cars.html | Formats: FBX, OBJ, .blend (no glTF) | Models measured: 7
- Preview: `CarsPack/_preview.png`

### Vehicles

| Model | tris | size (m) | notes | path |
|---|---|---|---|---|
| Cop | 3232 | 1.78 x 3.73 x 1.24 |  | `CarsPack/Realistic Car Pack - Nov 2018/FBX/Cop.fbx` |
| NormalCar1 | 2954 | 1.81 x 4.22 x 1.18 |  | `CarsPack/Realistic Car Pack - Nov 2018/FBX/NormalCar1.fbx` |
| NormalCar2 | 3124 | 1.64 x 3.31 x 1.15 |  | `CarsPack/Realistic Car Pack - Nov 2018/FBX/NormalCar2.fbx` |
| SUV | 3294 | 2.11 x 4.21 x 1.53 |  | `CarsPack/Realistic Car Pack - Nov 2018/FBX/SUV.fbx` |
| SportsCar | 3078 | 1.8 x 3.97 x 1.16 |  | `CarsPack/Realistic Car Pack - Nov 2018/FBX/SportsCar.fbx` |
| SportsCar2 | 3148 | 1.87 x 3.93 x 1.2 |  | `CarsPack/Realistic Car Pack - Nov 2018/FBX/SportsCar2.fbx` |
| Taxi | 3278 | 1.81 x 4.22 x 1.31 |  | `CarsPack/Realistic Car Pack - Nov 2018/FBX/Taxi.fbx` |
