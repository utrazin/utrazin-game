# Integração Blender para Unreal

Caminho padrão: **FBX via script** (`tools/blender/export_assets.py`) + **import via Python da Unreal** (`tools/unreal/import_assets.py`). Não depende de addon de terceiros. O addon "Send to Unreal" (BlenderTools) é opcional, ver [`MCP_SECURITY.md`](MCP_SECURITY.md).

## Convenções de cena no Blender

- Unidades: Metric, Unit Scale **1.0**, comprimento em metros.
- Frente do asset para **-Y** no Blender (vira +X na Unreal com as configurações abaixo).
- Transformações aplicadas (`Ctrl+A > All Transforms`) antes do export; `validate_scene.py` verifica.
- Origem: personagens no chão entre os pés; veículo no centro do chassi na altura do chão; props na base.
- Coleções: `EXPORT` (o que vai para a engine), `WIP`, `REF`. Só `EXPORT` é exportada.
- Colisão estática: malhas `UCX_<NomeDoMesh>_00` dentro de `EXPORT`.
- LODs: `<Nome>_LOD0`, `_LOD1`... ou gerados na Unreal (decisão por asset no manifesto).

## Configuração FBX (preset `blender/export-presets/fbx_unreal.json`)

| Opção | Valor |
|---|---|
| Apply Scalings | FBX Units Scale |
| Forward / Up | -Y Forward / Z Up |
| Apply Unit | ligado |
| Add Leaf Bones | **desligado** |
| Primary/Secondary bone axis | Y / X |
| Smoothing | Face |
| Tangent Space | ligado (malhas estáticas) |
| Bake Animation | ligado só para animações |
| Mesh: Apply Modifiers | ligado |

## Esqueleto

- Nomes de ossos compatíveis com o esqueleto UE5 (`pelvis`, `spine_01`... `hand_r`) para retarget com IK Retargeter.
- Armature chamada `root` (evita osso extra "Armature" na Unreal).

## Import na Unreal

| Tipo | Pasta | Opções |
|---|---|---|
| Static Mesh | `Content/<Categoria>/<Asset>/Meshes` | Combine meshes off; collision custom (UCX); Nanite **off** por padrão |
| Skeletal Mesh | `Content/Characters/<Asset>/Meshes` | Skeleton compartilhado `SK_Mannequin_JR`; Import morph targets se houver |
| Animação | `Content/Animations/<Grupo>` | Skeleton existente; root motion conforme manifesto |
| Textura | `.../Textures` | `_N` como Normalmap; `_ORM` sem sRGB |

Nada é sobrescrito se o asset existente estiver `approved` (import_assets.py aborta).
