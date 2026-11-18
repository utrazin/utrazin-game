"""Importa os modelos e texturas do usuário (Tripo 3D + texturas TX_*) para a Unreal.

RODA NO EDITOR (caixa Cmd, sem Play), DEPOIS de compilar o C++:
  py "E:/game/utrazin-game/tools/unreal/import_user_assets.py"          (importa só o que falta)
  py "E:/game/utrazin-game/tools/unreal/import_user_assets.py" force    (reimporta tudo)

Entradas (geradas fora da Unreal, ver assets/raw/tripo/CATALOG.md):
  assets/raw/tripo/tripo_catalog.json        nomes, categoria, colisão
  assets/work/tripo/SM_<Nome>.fbx            malha em tamanho real (m), origem no pé, frente +X, caixas UCX_
  assets/work/tripo/textures/T_<Nome>_D.jpg  cor base
  assets/work/tripo/tripo_processed.json     medidas finais (para conferir a escala depois do import)
  assets/work/textures/user/T_User_<Nome>_D.png / _N.png   texturas repetíveis do usuário
Saídas:
  /Game/Environment/User/<Categoria>/SM_<Nome>        (+ SM_PRP_Bau_Base / SM_PRP_Bau_Tampa)
  /Game/Environment/User/<Categoria>/Textures/T_<Nome>_D
  /Game/Environment/User/<Categoria>/Materials/MI_<Nome>  (filho de M_User_Prop: nada fica branco)
  /Game/Environment/User/Materials/M_User_Prop        (cor base por textura, 2 lados, brilho opcional)
  /Game/Environment/Textures/User/T_User_<Nome>_D / _N (normal = NormalMap, sem sRGB)
  /Game/Environment/User/Materials/M_User_Tiling + MI_User_<Nome>  (alinhado ao mundo, 3 projeções)
  reports/import_user_assets.json
Colisão: "box"/"trunk" = caixas UCX do FBX (casas decorativas: a caixa fecha a porta); "complex" = a própria
malha (barraca aberta na frente, cobertura do posto, arco, marcos, pedras grandes, cela); "none" = sem colisão.
"""
import json
import os
import sys
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RAW = os.path.join(REPO, "assets", "raw", "tripo")
WORK = os.path.join(REPO, "assets", "work", "tripo")
USER_TEX = os.path.join(REPO, "assets", "work", "textures", "user")
ROOT = "/Game/Environment/User"
MATS = f"{ROOT}/Materials"
TEX_TILING = "/Game/Environment/Textures/User"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
FORCE = any(a.lower() == "force" for a in sys.argv[1:])
R = {"time": datetime.now().isoformat(), "force": FORCE, "meshes": {}, "tiling": {}, "steps": [], "warnings": [],
     "errors": []}

# brilho leve (emissivo = cor base x valor) nas coisas bioluminescentes
GLOW = {"NAT_Flor": 0.6, "NAT_Flor2": 0.6, "NAT_Cogumelos": 0.5, "MRC_Cristal": 0.4, "MRC_ArvoreMae": 0.25,
        "MRC_Colmeia": 0.2, "NAT_Arbusto1": 0.25, "NAT_Arvore4": 0.15, "PRP_Poste": 0.3, "ITM_Municao": 0.3}
# tamanho do ladrilho (cm) de cada textura repetível
TILE_CM = {"AreiaVermelha": 800, "Asfalto": 600, "Terra": 600, "GramaAlien": 500, "LamaToxica": 600,
           "MusgoRoxo": 500, "Pedra": 500, "RochaCristal": 700, "Tijolo": 250, "TelhaCeramica": 250,
           "MadeiraPiso": 300, "MadeiraTabuas": 300, "MadeiraVelha": 300, "Concreto": 400, "Reboco": 400,
           "MetalOndulado": 300, "MetalAlien": 300, "Lona": 300, "VidroSujo": 200, "PeleZumbi": 200,
           "CascaAlien": 300, "FolhasAlien": 300}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[import_user_assets] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[import_user_assets] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-700:]})
    unreal.log_error(f"[import_user_assets] {where}: {exc}")


def setp(obj, k, v, where=""):
    try:
        obj.set_editor_property(k, v)
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"{where}.{k}: {exc}")
        return False


def save(a):
    EAL.save_loaded_asset(a, only_if_is_dirty=False)


# ------------------------------------------------------------------ texturas
def import_image(path, folder, name, kind):
    """kind: color | normal. Já existe e sem force: só confere as configurações."""
    dest = f"{folder}/{name}"
    if FORCE or not EAL.does_asset_exist(dest):
        task = unreal.AssetImportTask()
        task.filename = path
        task.destination_path = folder
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        TOOLS.import_asset_tasks([task])
    t = EAL.load_asset(dest)
    if t is None:
        raise RuntimeError(f"textura não importada: {path}")
    if kind == "normal":
        setp(t, "compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP, name)
        setp(t, "srgb", False, name)
        setp(t, "flip_green_channel", False, name)       # já é DirectX (verde para baixo), o padrão da Unreal
        setp(t, "lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP, name)
    else:
        setp(t, "compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT, name)
        setp(t, "srgb", True, name)
        setp(t, "lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD, name)
    save(t)
    return t


# ------------------------------------------------------------------ materiais (mesmo ajudante do setup_wave1)
class MB:
    def __init__(self, path):
        folder, name = path.rsplit("/", 1)
        EAL.make_directory(folder)
        if EAL.does_asset_exist(path):
            self.m = EAL.load_asset(path)
            MEL.delete_all_material_expressions(self.m)
        else:
            self.m = TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
        self.x, self.y = -2000, 0

    def node(self, cls, **props):
        e = MEL.create_material_expression(self.m, cls, self.x, self.y)
        self.y += 140
        if self.y > 2800:
            self.y, self.x = 0, self.x + 280
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def link(self, a, a_out, b, b_in):
        if not MEL.connect_material_expressions(a, a_out, b, b_in):
            warn(f"{self.m.get_name()}: ligação {a.get_name()}.{a_out} -> {b.get_name()}.{b_in} falhou")

    def out(self, e, prop, e_out=""):
        if not MEL.connect_material_property(e, e_out, prop):
            warn(f"{self.m.get_name()}: saída {prop} falhou")

    def op(self, cls, a, b=None, a_out="", b_out="", cb=None):
        e = self.node(cls)
        self.link(a, a_out, e, "A")
        if b is not None:
            self.link(b, b_out, e, "B")
        elif cb is not None:
            e.set_editor_property("const_b", float(cb))
        return e

    def mask(self, src, chans):
        e = self.node(unreal.MaterialExpressionComponentMask, r="r" in chans, g="g" in chans, b="b" in chans, a=False)
        self.link(src, "", e, "")
        return e

    def finish(self):
        MEL.recompile_material(self.m)
        save(self.m)
        log(f"material {self.m.get_name()} pronto")
        return self.m


def master_prop(default_tex):
    """M_User_Prop: BaseColor (textura) x Tint; Roughness; brilho = cor x EmissiveStrength. Dois lados."""
    b = MB(f"{MATS}/M_User_Prop")
    setp(b.m, "two_sided", True, "M_User_Prop")
    tex = b.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="BaseColor", texture=default_tex)
    tint = b.node(unreal.MaterialExpressionVectorParameter, parameter_name="Tint",
                  default_value=unreal.LinearColor(1, 1, 1, 1))
    col = b.op(unreal.MaterialExpressionMultiply, tex, tint, a_out="RGB")
    b.out(col, MP.MP_BASE_COLOR)
    rough = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="Roughness", default_value=0.8)
    b.out(rough, MP.MP_ROUGHNESS)
    metal = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="Metallic", default_value=0.0)
    b.out(metal, MP.MP_METALLIC)
    glow = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="EmissiveStrength", default_value=0.0)
    b.out(b.op(unreal.MaterialExpressionMultiply, col, glow), MP.MP_EMISSIVE_COLOR)
    return b.finish()


def master_tiling(def_d, def_n):
    """M_User_Tiling: textura alinhada ao mundo (projeção de cima, de frente e de lado misturadas pela normal),
    para terreno e paredes. Parâmetros: Diffuse, Normal, TileSizeCm, Tint, Roughness."""
    b = MB(f"{MATS}/M_User_Tiling")
    wp = b.node(unreal.MaterialExpressionWorldPosition)
    size = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="TileSizeCm", default_value=400.0)
    uvs = {}
    for key, ch in (("z", "rg"), ("y", "rb"), ("x", "gb")):
        uvs[key] = b.op(unreal.MaterialExpressionDivide, b.mask(wp, ch), size)
    # pesos: |normal|^4 normalizado
    vn = b.node(unreal.MaterialExpressionVertexNormalWS)
    ab = b.node(unreal.MaterialExpressionAbs)
    b.link(vn, "", ab, "")
    pw = b.node(unreal.MaterialExpressionPower, const_exponent=4.0)
    b.link(ab, "", pw, "Base")
    one = b.node(unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(1, 1, 1, 1))
    dot = b.node(unreal.MaterialExpressionDotProduct)
    b.link(pw, "", dot, "A")
    b.link(one, "", dot, "B")
    w = b.op(unreal.MaterialExpressionDivide, pw, dot)
    wx, wy, wz = b.mask(w, "r"), b.mask(w, "g"), b.mask(w, "b")

    def tri(param, default, normal):
        acc = None
        for key, wk in (("x", wx), ("y", wy), ("z", wz)):
            s = b.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=param, texture=default)
            if normal:
                s.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            b.link(uvs[key], "", s, "UVs")
            part = b.op(unreal.MaterialExpressionMultiply, s, wk, a_out="RGB")
            acc = part if acc is None else b.op(unreal.MaterialExpressionAdd, acc, part)
        return acc
    tint = b.node(unreal.MaterialExpressionVectorParameter, parameter_name="Tint",
                  default_value=unreal.LinearColor(1, 1, 1, 1))
    b.out(b.op(unreal.MaterialExpressionMultiply, tri("Diffuse", def_d, False), tint), MP.MP_BASE_COLOR)
    b.out(tri("Normal", def_n, True), MP.MP_NORMAL)
    rough = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="Roughness", default_value=0.9)
    b.out(rough, MP.MP_ROUGHNESS)
    return b.finish()


def make_mi(path, parent, textures=None, scalars=None):
    folder, name = path.rsplit("/", 1)
    EAL.make_directory(folder)
    if EAL.does_asset_exist(path):
        mi = EAL.load_asset(path)
    else:
        mi = TOOLS.create_asset(name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    for k, v in (textures or {}).items():
        MEL.set_material_instance_texture_parameter_value(mi, k, v)
    for k, v in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
    MEL.update_material_instance(mi)
    save(mi)
    return mi


# ------------------------------------------------------------------ malhas
def import_mesh(fbx, folder, sm_name):
    path = f"{folder}/{sm_name}"
    if not FORCE and EAL.does_asset_exist(path):
        return EAL.load_asset(path), False
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = folder
    task.destination_name = sm_name
    task.automated = True
    task.replace_existing = True
    task.save = True
    o = unreal.FbxImportUI()
    o.import_mesh = True
    o.import_as_skeletal = False
    o.import_animations = False
    o.import_materials = False        # o material vem do MI_<Nome> (abaixo); o FBX não traz textura
    o.import_textures = False
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    d = o.static_mesh_import_data
    for k, v in (("combine_meshes", True), ("auto_generate_collision", False), ("generate_lightmap_u_vs", False),
                 ("build_nanite", False), ("one_convex_hull_per_ucx", True), ("import_uniform_scale", 1.0)):
        setp(d, k, v, sm_name)
    task.options = o
    TOOLS.import_asset_tasks([task])
    sm = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
    if not isinstance(sm, unreal.StaticMesh):
        raise RuntimeError(f"não virou StaticMesh: {path}")
    return sm, True


def set_collision_flag(sm, kind):
    bs = sm.get_editor_property("body_setup")
    if bs is None:
        return
    flag = (unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE if kind == "complex"
            else unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
    bs.set_editor_property("collision_trace_flag", flag)
    # [A-063] "box"/"trunk" dependem da caixa UCX do Blender; se ela não veio, o herói atravessa (print_01)
    try:
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        if kind in ("box", "trunk") and sub.get_simple_collision_count(sm) == 0:
            if kind == "box":
                sub.add_simple_collisions(sm, unreal.ScriptCollisionShapeType.BOX)
                warn(f"{sm.get_name()}: sem UCX no FBX; ganhou uma caixa do tamanho da malha")
            else:
                warn(f"{sm.get_name()}: sem UCX do tronco no FBX (fica sem colisão; rode fix_l01_frente1.py)")
    except Exception as exc:  # noqa: BLE001
        warn(f"{sm.get_name()}: conferir colisão: {exc}")


def add_lods(sm, name):
    """3 LODs automáticos (100%, 45%, 20%) para os modelos de 15 a 20 mil triângulos."""
    try:
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        if sub.get_lod_count(sm) >= 3:
            return
        opts = unreal.EditorScriptingMeshReductionOptions()
        opts.set_editor_property("auto_compute_lod_screen_size", False)
        opts.set_editor_property("reduction_settings", [
            unreal.EditorScriptingMeshReductionSettings(1.0, 1.0),
            unreal.EditorScriptingMeshReductionSettings(0.45, 0.35),
            unreal.EditorScriptingMeshReductionSettings(0.2, 0.12)])
        sub.set_lods(sm, opts)
    except Exception as exc:  # noqa: BLE001
        warn(f"{name}: LODs automáticos: {exc}")


def size_cm(sm):
    b = sm.get_bounding_box()
    return [round(b.max.x - b.min.x, 1), round(b.max.y - b.min.y, 1), round(b.max.z - b.min.z, 1)]


def mesh_item(it, proc, master):
    name, cat = it["name"], it["category"]
    folder = f"{ROOT}/{cat}"
    p = proc.get(name, {})
    fbx = os.path.join(WORK, f"SM_{name}.fbx")
    if not os.path.exists(fbx):
        raise FileNotFoundError(f"falta {fbx} (rode tools/blender/prep_tripo.py)")
    tex_path = os.path.join(WORK, "textures", f"T_{name}_D.jpg")
    tex = import_image(tex_path, f"{folder}/Textures", f"T_{name}_D", "color") if os.path.exists(tex_path) else None
    if tex is None:
        warn(f"{name}: sem textura de cor (ficaria branco)")
    mi = make_mi(f"{folder}/Materials/MI_{name}", master, {"BaseColor": tex} if tex else {},
                 {"EmissiveStrength": GLOW.get(name, 0.0)})
    out = {}
    parts = [("", name)]
    if name == "PRP_Bau":
        parts += [("_Base", f"{name}_Base"), ("_Tampa", f"{name}_Tampa")]
    for suffix, fname in parts:
        sm, imported = import_mesh(os.path.join(WORK, f"SM_{fname}.fbx"), folder, f"SM_{fname}")
        for i in range(max(1, len(sm.get_editor_property("static_materials")))):
            sm.set_material(i, mi)
        set_collision_flag(sm, it["collision"])
        if p.get("tris", 0) > 12000 and cat in ("Natureza", "Props", "Itens", "Construcoes"):
            add_lods(sm, fname)
        save(sm)
        got = size_cm(sm)
        want = [round(v * 100, 1) for v in p.get("dims_m", [])] if not suffix else None
        ok = want is None or all(abs(a - b) <= max(2.0, 0.02 * b) for a, b in zip(got, want))
        out[f"SM_{fname}"] = {"path": f"{folder}/SM_{fname}", "imported_now": imported, "size_cm": got,
                              "expected_cm": want, "scale_ok": ok, "material": mi.get_path_name().split(".")[0],
                              "texture": tex.get_path_name().split(".")[0] if tex else None,
                              "collision": it["collision"]}
        if not ok:
            warn(f"SM_{fname}: tamanho {got} cm, esperado {want} cm (escala do FBX?)")
    return out


def tiling():
    files = sorted(f for f in os.listdir(USER_TEX) if f.startswith("T_User_") and f.endswith("_D.png")) \
        if os.path.isdir(USER_TEX) else []
    if not files:
        warn(f"sem texturas em {USER_TEX} (rode tools/pipeline/make_user_textures.py)")
        return
    tex = {}
    for f in files:
        base = f[len("T_User_"):-len("_D.png")]
        d = import_image(os.path.join(USER_TEX, f), TEX_TILING, f"T_User_{base}_D", "color")
        npath = os.path.join(USER_TEX, f"T_User_{base}_N.png")
        n = import_image(npath, TEX_TILING, f"T_User_{base}_N", "normal") if os.path.exists(npath) else None
        tex[base] = (d, n)
    first = tex.get("Pedra") or next(iter(tex.values()))
    master = master_tiling(first[0], first[1])
    for base, (d, n) in tex.items():
        t = {"Diffuse": d}
        if n:
            t["Normal"] = n
        mi = make_mi(f"{MATS}/MI_User_{base}", master, t, {"TileSizeCm": TILE_CM.get(base, 400)})
        R["tiling"][base] = {"mi": mi.get_path_name().split(".")[0], "tile_cm": TILE_CM.get(base, 400),
                             "normal": bool(n)}
    log(f"{len(tex)} texturas repetíveis + M_User_Tiling + MIs")


def main():
    cat = json.load(open(os.path.join(RAW, "tripo_catalog.json"), encoding="utf-8"))
    proc_path = os.path.join(WORK, "tripo_processed.json")
    proc = json.load(open(proc_path, encoding="utf-8")) if os.path.exists(proc_path) else {}
    for c in sorted({i["category"] for i in cat["items"]}):
        EAL.make_directory(f"{ROOT}/{c}")
    first_tex = None
    for it in cat["items"]:
        p = os.path.join(WORK, "textures", f"T_{it['name']}_D.jpg")
        if os.path.exists(p):
            first_tex = import_image(p, f"{ROOT}/{it['category']}/Textures", f"T_{it['name']}_D", "color")
            break
    master = master_prop(first_tex)
    with unreal.ScopedSlowTask(len(cat["items"]), "Importando modelos do usuário") as task:
        task.make_dialog(True)
        for it in cat["items"]:
            if task.should_cancel():
                break
            task.enter_progress_frame(1, it["name"])
            try:
                R["meshes"].update(mesh_item(it, proc, master))
            except Exception as exc:  # noqa: BLE001
                err(it["name"], exc)
    log(f"{len(R['meshes'])} malhas prontas em {ROOT}")
    try:
        tiling()
    except Exception as exc:  # noqa: BLE001
        err("tiling", exc)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "import_user_assets.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    bad = [k for k, v in R["meshes"].items() if not v.get("scale_ok")]
    unreal.log(f"[import_user_assets] fim | malhas: {len(R['meshes'])} | escala errada: {len(bad)} | "
               f"avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
