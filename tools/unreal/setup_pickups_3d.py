"""Pickups 3D no chão (A-082): importa as malhas SM_Pickup_*, cria os materiais com brilho e deixa tudo pronto.

RODA NO EDITOR (caixa Cmd do Output Log, sem Play), DEPOIS de compilar o C++ novo do AJRPickup:
  py "E:/game/utrazin-game/tools/unreal/setup_pickups_3d.py"
Pode rodar de novo (reimporta e refaz os materiais). Relatório: reports/setup_pickups_3d.json

Entrada (gerada por tools/blender/pickups/make_pickups.py, já vem no repositório):
  assets/work/props/pickups/SM_Pickup_<Nome>.fbx, T_Pickup_Palette.png, T_Pickup_RingGlow.png, pickups.json

O que faz:
 1. Texturas em /Game/Props/Pickups/Textures: T_Pickup_Palette (cores chapadas, filtro "nearest", sem mipmaps)
    e T_Pickup_RingGlow (máscara do anel de brilho do chão).
 2. Materiais em /Game/Props/Pickups/Materials:
      M_Pickup_Body  fosco tipo argila: paleta x Tint, Roughness. Slot "Body" das malhas.
      M_Pickup_Core  núcleo que brilha: Color, Intensity (o C++ pulsa Intensity por um MID). Slot "Core".
      M_Pickup_Ring  anel aditivo sem luz no chão: Color, Intensity (o C++ pulsa). Slot "Ring".
    Instâncias: MI_Pickup_Body, MI_Pickup_Core_<Nome> (cor do núcleo de cada item) e MI_Pickup_Ring.
 3. Malhas em /Game/Props/Pickups: SM_Pickup_CellPistol, ShellShotgun, CellRifle, HealthGel, Bandage, Medkit,
    FuryCrystal, Nitro, Repair e Ring. Sem colisão (o AJRPickup usa uma esfera própria), sem Nanite,
    normais do arquivo, materiais ligados pelo nome do slot.
 4. Confere se o C++ novo está compilado (propriedades novas no AJRPickup) e registra os tamanhos em cm.

O AJRPickup acha tudo pelos caminhos padrão (TSoftObjectPtr). Sem este script o jogo continua com as formas antigas.
"""
import json
import os
import sys
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SRC = os.path.join(REPO, "assets", "work", "props", "pickups")
DST = "/Game/Props/Pickups"
TEX_DIR = DST + "/Textures"
MAT_DIR = DST + "/Materials"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "info": {}, "cpp_needed": []}

# Nome -> cor do núcleo (linear). Igual ao C++ (JRPickup.cpp, tabela VisualFor) e ao pickups.json.
ITEMS = {
    "CellPistol": (0.55, 0.12, 1.0),
    "ShellShotgun": (1.0, 0.35, 0.04),
    "CellRifle": (0.1, 0.85, 1.0),
    "HealthGel": (1.0, 0.12, 0.2),
    "Bandage": (1.0, 0.25, 0.25),
    "Medkit": (1.0, 0.2, 0.15),
    "FuryCrystal": (0.75, 0.2, 1.0),
    "Nitro": (0.1, 0.55, 1.0),
    "Repair": (0.2, 1.0, 0.35),
}
CORE_INTENSITY = 6.0
RING_INTENSITY = 1.5


def log(m):
    R["steps"].append(m)
    unreal.log(f"[setup_pickups_3d] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[setup_pickups_3d] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-900:]})
    unreal.log_error(f"[setup_pickups_3d] {where}: {exc}")


def setp(obj, prop, value, where=""):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"{where}: {prop}: {exc}")
        return False


def save(a):
    EAL.save_loaded_asset(a, only_if_is_dirty=False)


def lc(rgb, a=1.0):
    return unreal.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), float(a))


# ------------------------------------------------------------------ 1. texturas

def import_texture(name, srgb):
    f = os.path.join(SRC, name + ".png")
    if not os.path.exists(f):
        raise FileNotFoundError(f"falta {f} (rode tools/blender/pickups/make_pickups.py)")
    EAL.make_directory(TEX_DIR)
    task = unreal.AssetImportTask()
    task.filename = f
    task.destination_path = TEX_DIR
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    TOOLS.import_asset_tasks([task])
    t = EAL.load_asset(f"{TEX_DIR}/{name}")
    if t is None:
        raise RuntimeError(f"textura não importada: {f}")
    setp(t, "srgb", srgb, name)
    setp(t, "compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT, name)
    setp(t, "lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD, name)
    if name == "T_Pickup_Palette":
        setp(t, "filter", unreal.TextureFilter.TF_NEAREST, name)            # cores chapadas, sem borrar
        setp(t, "mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS, name)
    save(t)
    log(f"textura {name}")
    return t


# ------------------------------------------------------------------ 2. materiais

class MB:
    """Monta um material por nós (recria do zero a cada execução)."""

    def __init__(self, name):
        path = f"{MAT_DIR}/{name}"
        EAL.make_directory(MAT_DIR)
        if EAL.does_asset_exist(path):
            self.m = EAL.load_asset(path)
            MEL.delete_all_material_expressions(self.m)
        else:
            self.m = TOOLS.create_asset(name, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
        self.x, self.y = -1200, -200

    def node(self, cls, **props):
        e = MEL.create_material_expression(self.m, cls, self.x, self.y)
        self.y += 130
        if self.y > 1200:
            self.y, self.x = -200, self.x + 280
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def link(self, a, a_out, b, b_in):
        if not MEL.connect_material_expressions(a, a_out, b, b_in):
            warn(f"{self.m.get_name()}: ligação {a.get_name()}.{a_out} -> {b.get_name()}.{b_in} falhou")

    def out(self, e, prop, e_out=""):
        if not MEL.connect_material_property(e, e_out, prop):
            warn(f"{self.m.get_name()}: saída {prop} falhou")

    def vparam(self, name, rgb):
        return self.node(unreal.MaterialExpressionVectorParameter, parameter_name=name, default_value=lc(rgb))

    def sparam(self, name, v):
        return self.node(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=float(v))

    def mul(self, a, b=None, cb=None, a_out="", b_out=""):
        e = self.node(unreal.MaterialExpressionMultiply)
        self.link(a, a_out, e, "A")
        if b is not None:
            self.link(b, b_out, e, "B")
        else:
            e.set_editor_property("const_b", float(cb))
        return e

    def add(self, a, b=None, cb=None):
        e = self.node(unreal.MaterialExpressionAdd)
        self.link(a, "", e, "A")
        if b is not None:
            self.link(b, "", e, "B")
        else:
            e.set_editor_property("const_b", float(cb))
        return e

    def one_minus(self, a):
        e = self.node(unreal.MaterialExpressionOneMinus)
        self.link(a, "", e, "")
        return e

    def lerp(self, a, b, alpha):
        e = self.node(unreal.MaterialExpressionLinearInterpolate)
        self.link(a, "", e, "A")
        self.link(b, "", e, "B")
        self.link(alpha, "", e, "Alpha")
        return e

    def texparam(self, name, tex, linear):
        e = self.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=name, texture=tex)
        if linear:
            e.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        return e

    def finish(self):
        MEL.recompile_material(self.m)
        save(self.m)
        log(f"material {self.m.get_name()}")
        return self.m


def mat_body(palette):
    b = MB("M_Pickup_Body")
    tex = b.texparam("Palette", palette, False)
    tint = b.vparam("Tint", (1, 1, 1))
    col = b.mul(tex, tint, a_out="RGB")
    b.out(col, MP.MP_BASE_COLOR)
    b.out(b.sparam("Roughness", 0.6), MP.MP_ROUGHNESS)
    b.out(b.sparam("Metallic", 0.0), MP.MP_METALLIC)
    # contorno levemente aceso (lê melhor contra o chão escuro); 0 = desligado
    rim = b.node(unreal.MaterialExpressionFresnel, exponent=3.0, base_reflect_fraction=0.0)
    b.out(b.mul(b.mul(col, rim), b.sparam("RimGlow", 0.35)), MP.MP_EMISSIVE_COLOR)
    return b.finish()


def mat_core():
    b = MB("M_Pickup_Core")
    color = b.vparam("Color", ITEMS["CellPistol"])
    inten = b.sparam("Intensity", CORE_INTENSITY)
    b.out(b.mul(color, cb=0.3), MP.MP_BASE_COLOR)
    b.out(b.sparam("Roughness", 0.25), MP.MP_ROUGHNESS)
    # centro mais quente (quase branco) e borda na cor: parece plasma dentro de vidro
    fres = b.node(unreal.MaterialExpressionFresnel, exponent=2.0, base_reflect_fraction=0.0)
    hot = b.mul(b.one_minus(fres), cb=0.45)
    white = b.node(unreal.MaterialExpressionConstant3Vector, constant=lc((1, 1, 1)))
    tint = b.lerp(color, white, hot)
    b.out(b.mul(tint, inten), MP.MP_EMISSIVE_COLOR)
    return b.finish()


def mat_ring(ring_tex):
    b = MB("M_Pickup_Ring")
    setp(b.m, "blend_mode", unreal.BlendMode.BLEND_ADDITIVE, "M_Pickup_Ring")
    setp(b.m, "shading_model", unreal.MaterialShadingModel.MSM_UNLIT, "M_Pickup_Ring")
    setp(b.m, "two_sided", True, "M_Pickup_Ring")
    tex = b.texparam("Mask", ring_tex, True)
    color = b.vparam("Color", ITEMS["CellPistol"])
    inten = b.sparam("Intensity", RING_INTENSITY)
    b.out(b.mul(b.mul(color, inten), tex, b_out="R"), MP.MP_EMISSIVE_COLOR)
    return b.finish()


def make_mi(name, parent, vectors=None, scalars=None):
    path = f"{MAT_DIR}/{name}"
    if EAL.does_asset_exist(path):
        mi = EAL.load_asset(path)
    else:
        mi = TOOLS.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    for k, v in (vectors or {}).items():
        MEL.set_material_instance_vector_parameter_value(mi, k, lc(v))
    for k, v in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
    MEL.update_material_instance(mi)
    save(mi)
    return mi


# ------------------------------------------------------------------ 3. malhas

def import_mesh(name):
    sm_name = f"SM_Pickup_{name}"
    f = os.path.join(SRC, sm_name + ".fbx")
    if not os.path.exists(f):
        raise FileNotFoundError(f"falta {f} (rode tools/blender/pickups/make_pickups.py)")
    task = unreal.AssetImportTask()
    task.filename = f
    task.destination_path = DST
    task.destination_name = sm_name
    task.automated = True
    task.replace_existing = True
    task.save = False
    o = unreal.FbxImportUI()
    o.import_mesh = True
    o.import_as_skeletal = False
    o.import_animations = False
    o.import_materials = False          # os materiais vêm daqui (ligados pelo nome do slot)
    o.import_textures = False
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    d = o.static_mesh_import_data
    opts = [("combine_meshes", True), ("auto_generate_collision", False), ("generate_lightmap_u_vs", False),
            ("build_nanite", False), ("import_uniform_scale", 1.0)]
    nim = getattr(getattr(unreal, "FBXNormalImportMethod", None), "FBXNIM_IMPORT_NORMALS", None)
    if nim is not None:
        opts.append(("normal_import_method", nim))   # sombreado duro/suave do Blender
    for k, v in opts:
        setp(d, k, v, sm_name)
    task.options = o
    TOOLS.import_asset_tasks([task])
    path = f"{DST}/{sm_name}"
    sm = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
    if not isinstance(sm, unreal.StaticMesh):
        raise RuntimeError(f"não virou StaticMesh: {path}")
    return sm


def slot_names(sm):
    out = []
    for s in sm.get_editor_property("static_materials"):
        try:
            out.append(str(s.get_editor_property("material_slot_name")))
        except Exception:  # noqa: BLE001
            out.append("")
    return out


def assign(sm, by_slot, order):
    """Liga material pelo nome do slot; se a importação renomeou, usa a ordem do Blender (Body, Core)."""
    names = slot_names(sm)
    for i, n in enumerate(names):
        key = next((k for k in by_slot if n.lower().startswith(k.lower())), None)
        if key is None and i < len(order):
            key = order[i]
            warn(f"{sm.get_name()}: slot {i} chama '{n}'; usei a ordem ({key})")
        if key:
            sm.set_material(i, by_slot[key])
    return names


def no_collision(sm):
    bs = sm.get_editor_property("body_setup")
    if bs is not None:
        setp(bs, "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_DEFAULT, sm.get_name())
    try:
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        if sub.get_simple_collision_count(sm) > 0:
            sub.remove_collisions(sm)
    except Exception as exc:  # noqa: BLE001
        warn(f"{sm.get_name()}: colisão: {exc}")


def size_cm(sm):
    b = sm.get_bounding_box()
    return [round(b.max.x - b.min.x, 1), round(b.max.y - b.min.y, 1), round(b.max.z - b.min.z, 1), round(b.min.z, 2)]


def meshes(body_mi, core_parent, ring_mi):
    for name, rgb in ITEMS.items():
        try:
            core_mi = make_mi(f"MI_Pickup_Core_{name}", core_parent, vectors={"Color": rgb},
                              scalars={"Intensity": CORE_INTENSITY})
            sm = import_mesh(name)
            names = assign(sm, {"Body": body_mi, "Core": core_mi}, ["Body", "Core"])
            no_collision(sm)
            save(sm)
            R["info"][f"SM_Pickup_{name}"] = {"slots": names, "size_cm_xyz_minz": size_cm(sm)}
            log(f"SM_Pickup_{name}: slots {names}, {size_cm(sm)} cm")
        except Exception as exc:  # noqa: BLE001
            err(f"malha {name}", exc)
    try:
        sm = import_mesh("Ring")
        assign(sm, {"Ring": ring_mi}, ["Ring"])
        no_collision(sm)
        setp(sm, "light_map_resolution", 4, "SM_Pickup_Ring")
        save(sm)
        R["info"]["SM_Pickup_Ring"] = {"slots": slot_names(sm), "size_cm_xyz_minz": size_cm(sm)}
        log(f"SM_Pickup_Ring: {size_cm(sm)} cm")
    except Exception as exc:  # noqa: BLE001
        err("malha Ring", exc)


# ------------------------------------------------------------------ 4. C++

def check_cpp():
    cls = getattr(unreal, "JRPickup", None)
    if cls is None:
        R["cpp_needed"].append("AJRPickup")
        warn("classe JRPickup não achada no Python (C++ não compilado?)")
        return
    cdo = unreal.get_default_object(cls)
    for prop in ("mesh_ammo_pistol", "mesh_fury", "ring_mesh", "magnet_radius"):
        try:
            v = cdo.get_editor_property(prop)
            R["info"][f"cdo.{prop}"] = str(v)
        except Exception:  # noqa: BLE001
            R["cpp_needed"].append(prop)
            warn(f"AJRPickup sem {prop}: compile o C++ novo (Gameplay/JRPickup.h/.cpp) e rode de novo")
    if not R["cpp_needed"]:
        log("C++ novo do AJRPickup compilado (propriedades conferidas)")


def main():
    palette = ring_tex = None
    try:
        palette = import_texture("T_Pickup_Palette", True)
        ring_tex = import_texture("T_Pickup_RingGlow", False)
    except Exception as exc:  # noqa: BLE001
        err("texturas", exc)
        return
    try:
        body = mat_body(palette)
        core = mat_core()
        ring = mat_ring(ring_tex)
        body_mi = make_mi("MI_Pickup_Body", body)
        ring_mi = make_mi("MI_Pickup_Ring", ring, scalars={"Intensity": RING_INTENSITY})
    except Exception as exc:  # noqa: BLE001
        err("materiais", exc)
        return
    meshes(body_mi, core, ring_mi)
    try:
        check_cpp()
    except Exception as exc:  # noqa: BLE001
        err("check_cpp", exc)


if "--help" in sys.argv:
    print(__doc__)
else:
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        err("main", exc)
    finally:
        os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
        with open(os.path.join(REPO, "reports", "setup_pickups_3d.json"), "w", encoding="utf-8") as fh:
            json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
        unreal.log(f"[setup_pickups_3d] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])} "
                   f"| C++ faltando: {len(R['cpp_needed'])}")
