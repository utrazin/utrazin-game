# Regras de conteúdo Unreal

## Prefixos obrigatórios

| Tipo | Prefixo | Tipo | Prefixo |
|---|---|---|---|
| Blueprint | `BP_` | Widget Blueprint | `WBP_` |
| Static Mesh | `SM_` | Skeletal Mesh | `SK_` |
| Skeleton | `SKEL_` | Physics Asset | `PHYS_` |
| Material | `M_` | Material Instance | `MI_` |
| Material Function | `MF_` | Texture | `T_` |
| Render Target | `RT_` | Animation Blueprint | `ABP_` |
| Animation Sequence | `A_` | Animation Montage | `AM_` |
| Blend Space | `BS_` | IK Rig / Retargeter | `IK_` / `RTG_` |
| Niagara System | `NS_` | Niagara Emitter | `NE_` |
| Sound Wave (SFX) | `SFX_` | Música / Ambiente | `MUS_` / `AMB_` |
| Sound Cue / MetaSound | `SC_` / `MS_` | Sound Class / Attenuation | `SCL_` / `ATT_` |
| Data Asset | `DA_` | Data Table | `DT_` |
| Curve | `CF_` / `CV_` | Enum / Struct (BP) | `E_` / `F_` |
| Input Action | `IA_` | Input Mapping Context | `IMC_` |
| StateTree | `ST_` | Behavior Tree / Blackboard | `BT_` / `BB_` |
| Level Sequence | `LS_` | Mapa | `L<NN>_<Nome>` (ex.: `L01_Zombies`), sublevels `L01_Zombies_<Trecho>` |
| Veículo (BP) | `BP_Vehicle_<Nome>` | Wheel BP | `BP_Wheel_<Pos>` |
| Font | `FNT_` | String Table | `ST_Text_` |

## Estrutura

`Content/<Área>/<Asset>/{Meshes,Materials,Textures,Animations}`. Conteúdo de teste pessoal em `Content/Developer/` (nunca referenciado por mapas de produção).

## Regras

- Nomes em PascalCase, sem espaços nem acentos; variações com sufixo `_01`.
- Texturas: sufixos `_BC`, `_N`, `_ORM`, `_E`, `_M` (máscara).
- Sem referências de produção para `Developer/`.
- Fix Up Redirectors após mover/renomear.
- Validar com `tools/pipeline/validate_naming.py` e `tools/unreal/validate_content.py`.
