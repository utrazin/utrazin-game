"""Importa modelos Quaternius (CC0) de assets/raw/quaternius para /Game/Environment/Quaternius/<Pack>/ (reutilizável).

RODA DENTRO DO EDITOR (é importado por tools/unreal/build_l01.py; o agente Densidade pode usar também):
    import sys; sys.path.append("E:/game/utrazin-game/tools/unreal")
    import quaternius_lib as Q
    sm = Q.load_static("Nature/TwistedTree_1")             # importa na 1a vez, depois só carrega
    sm = Q.load_static("ZombieKit/Container_Green", collision="complex")

Referência "Pack/Modelo" (o mesmo nome do arquivo .fbx, sem extensão). Packs:
    Nature    = StylizedNatureMegaKit        SpaceKit = UltimateSpaceKit
    ZombieKit = ZombieApocalypseKit          Ruins    = UltimateModularRuins
    CarsPack  = CarsPack                     Monsters = UltimateMonsters (estáticos só)
Asset criado: /Game/Environment/Quaternius/<Pack>/SM_<Modelo> (+ materiais/texturas na mesma pasta).
Tamanhos: os FBX da Quaternius já vêm em metros (catálogo: assets/raw/quaternius/CATALOG.md); a Unreal
converte para cm na importação (uniform_scale 1). Pivô ~ no pé do modelo.
collision: "simple" (caixas automáticas), "complex" (usa a malha: casas, arcos, pedras grandes) ou "none".
"""
import os

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RAW = os.path.join(REPO, "assets", "raw", "quaternius")
DEST_ROOT = "/Game/Environment/Quaternius"
PACKS = {"Nature": "StylizedNatureMegaKit", "SpaceKit": "UltimateSpaceKit", "ZombieKit": "ZombieApocalypseKit",
         "Ruins": "UltimateModularRuins", "CarsPack": "CarsPack", "Monsters": "UltimateMonsters"}
EAL = unreal.EditorAssetLibrary
_FBX_INDEX = {}
LOG = []


def _index(pack):
    """Mapa nome.fbx (minúsculo) -> caminho, pulando as pastas 'Unity' (FBX com eixos de Unity)."""
    if pack in _FBX_INDEX:
        return _FBX_INDEX[pack]
    idx = {}
    base = os.path.join(RAW, PACKS[pack])
    for root, dirs, files in os.walk(base):
        if "unity" in root.lower():
            continue
        for f in files:
            if f.lower().endswith(".fbx"):
                key = f[:-4].lower()
                # prefere a pasta "FBX" (a mesma referência pode existir em glTF/OBJ)
                if key not in idx or os.sep + "FBX" in root:
                    idx[key] = os.path.join(root, f)
    _FBX_INDEX[pack] = idx
    return idx


def split_ref(ref):
    pack, model = ref.split("/", 1)
    if pack not in PACKS:
        raise ValueError(f"pack desconhecido em {ref!r} (use {sorted(PACKS)})")
    return pack, model


def asset_path(ref):
    pack, model = split_ref(ref)
    return f"{DEST_ROOT}/{pack}/SM_{model}"


def fbx_path(ref):
    pack, model = split_ref(ref)
    p = _index(pack).get(model.lower())
    if not p:
        raise FileNotFoundError(f"{ref}: {model}.fbx não achado em {os.path.join(RAW, PACKS[pack])}")
    return p


def _import(ref, collision):
    pack, model = split_ref(ref)
    task = unreal.AssetImportTask()
    task.filename = fbx_path(ref)
    task.destination_path = f"{DEST_ROOT}/{pack}"
    task.destination_name = f"SM_{model}"
    task.automated = True
    task.replace_existing = True
    task.save = True
    o = unreal.FbxImportUI()
    o.import_mesh = True
    o.import_as_skeletal = False
    o.import_animations = False
    o.import_materials = True
    o.import_textures = True
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    d = o.static_mesh_import_data
    for k, v in (("combine_meshes", True), ("auto_generate_collision", collision == "simple"),
                 ("generate_lightmap_u_vs", False), ("build_nanite", False)):
        try:
            d.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            LOG.append(f"{ref}: opção {k}: {exc}")
    task.options = o
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = [p.split(".")[0] for p in task.imported_object_paths]
    LOG.append(f"importado {ref} -> {paths[:1]}")


def ensure_simple_box(sm):
    """[A-063] "simple" sem nenhuma forma de colisão = o herói atravessa. Põe uma caixa do tamanho da malha.
    Retorna True se adicionou."""
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    if sub.get_simple_collision_count(sm) > 0:
        return False
    sub.add_simple_collisions(sm, unreal.ScriptCollisionShapeType.BOX)
    return True


def set_collision(sm, collision):
    try:
        bs = sm.get_editor_property("body_setup")
        if bs is None:
            return
        dirty = False
        flag = (unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE if collision == "complex"
                else unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
        if bs.get_editor_property("collision_trace_flag") != flag:
            bs.set_editor_property("collision_trace_flag", flag)
            dirty = True
        if collision == "simple" and ensure_simple_box(sm):
            LOG.append(f"{sm.get_name()}: estava sem colisão, ganhou uma caixa")
            dirty = True
        if dirty:
            EAL.save_loaded_asset(sm, only_if_is_dirty=False)
    except Exception as exc:  # noqa: BLE001
        LOG.append(f"{sm.get_name()}: colisão: {exc}")


def load_static(ref, collision="simple", reimport=False):
    """Carrega (importando se preciso) o modelo. Retorna unreal.StaticMesh ou None (motivo em LOG)."""
    path = asset_path(ref)
    try:
        if reimport or not EAL.does_asset_exist(path):
            _import(ref, collision)
        sm = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
        if not isinstance(sm, unreal.StaticMesh):
            LOG.append(f"{ref}: não virou StaticMesh em {path}")
            return None
        if collision in ("simple", "complex"):
            set_collision(sm, collision)
        return sm
    except Exception as exc:  # noqa: BLE001
        LOG.append(f"{ref}: {exc}")
        return None


def size_m(sm):
    """Tamanho (m) da caixa da malha, para conferir a escala no relatório."""
    try:
        b = sm.get_bounding_box()
        return [round((b.max.x - b.min.x) / 100, 2), round((b.max.y - b.min.y) / 100, 2), round((b.max.z - b.min.z) / 100, 2)]
    except Exception:  # noqa: BLE001
        return None
