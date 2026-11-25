"""[A-098] Grama estilizada da cidade: tufos de cards cruzados (sem billboard), normais para cima, cor do chão.

Substitui a grama billboard do A-092 ("parecia um PNG reto"). RODA NO EDITOR (caixa Cmd, sem Play), DEPOIS do
E:\\game\\gerar_grama.bat (Blender gera os tufos) e ANTES do setup_city_landscape.py:
  py "E:/game/utrazin-game/tools/unreal/setup_grass.py"

O que faz:
  1. importa T_Grama_Laminas (dado, sem sRGB: R altura na lâmina, G sorteio, B dobra, A recorte) e os 3 tufos
     SM_Grama_Tufo_0..2 (assets/work/grass, gerados por tools/blender/gen_grass_tufts.py)
  2. M_Grama_Tufo (masked, dois lados, normal do mundo PARA CIMA, sem tangente) + MI_Grama_Tufo para ajustar:
       - cor = a MESMA textura da grama do chão (T_User_GramaAlien_D, mesmo ladrilho 420 cm e mesma mistura macro
         do M_Cidade_Chao2/3) projetada pela posição no mundo: a base do tufo some no chão, sem emenda
       - escurece na base (BaseDark), ponta clara ciano (TipColor/TipAmount), variação por tufo (PerInstanceRandom)
         e por lâmina (G), dobra cartunesca (B)
       - vento: duas senoides pela posição do tufo, peso (1 - V)^2 (só a ponta mexe), curvatura fixa (WindBend)
       - some com a distância afinando as lâminas (PerInstanceFadeAmount), sem "estalo"
       - BackFix (0 ou 1): se o verso das lâminas ficar escuro no Play, ponha 1 no MI
  3. LGT_Cidade_Grama (o MESMO asset que o chão usa) com os 3 tufos: grade com jitter, giro aleatório, alinhado ao
     terreno, sem sombra, tufo menor perto da borda da área de grama (weight_attenuates_max_scale), cull 25 a 60 m
  4. limpa o cache de grama (grass.FlushCache) para o chão refazer os tufos
Relatório: reports/setup_grass.json
"""
import json
import os
import traceback

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(REPO, "assets", "work", "grass")
DIR = "/Game/Environment/Cidade/Grama"
GROUND_TEX = "/Game/Environment/Textures/User/T_User_GramaAlien_D"
GROUND_TILE_CM = 420.0   # igual ao LAYERS["grama"] do setup_city_landscape.py
GROUND_MACRO = 0.35      # igual ao Macro_grama do chão
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
R = {"steps": [], "warnings": [], "errors": []}
# tufo: densidade (por 10 m2), escala min, escala max, início e fim do sumiço (cm)
TUFTS = {
    "SM_Grama_Tufo_0": (60.0, 0.8, 1.2, 2500, 4000),
    "SM_Grama_Tufo_1": (25.0, 0.8, 1.25, 3000, 5000),
    "SM_Grama_Tufo_2": (5.0, 0.85, 1.2, 3500, 6000),
}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[grass] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[grass] {m}")


def try_set(obj, key, val, what=""):
    try:
        obj.set_editor_property(key, val)
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"{what or obj.get_name()}: {key} ({exc})")
        return False


def imp(filename, name, options=None):
    path = os.path.join(SRC, filename)
    if not os.path.isfile(path):
        raise RuntimeError(f"falta {path}: rode E:\\game\\gerar_grama.bat antes (Blender gera os tufos)")
    task = unreal.AssetImportTask()
    task.filename = path
    task.destination_path = DIR
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options is not None:
        task.options = options
    TOOLS.import_asset_tasks([task])
    a = EAL.load_asset(f"{DIR}/{name}")
    if a is None:
        raise RuntimeError(f"não importou {filename}")
    return a


def fbx_options():
    o = unreal.FbxImportUI()
    o.import_mesh = True
    o.import_as_skeletal = False
    o.import_materials = False
    o.import_textures = False
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    sm = o.static_mesh_import_data
    sm.set_editor_property("auto_generate_collision", False)
    sm.set_editor_property("combine_meshes", True)
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)  # normais para cima
    return o


class B:
    def __init__(self, path):
        folder, name = path.rsplit("/", 1)
        self.m = TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
        self.x, self.y = -1600, 0

    def node(self, cls, **props):
        n = MEL.create_material_expression(self.m, cls, self.x, self.y)
        self.y += 70
        if self.y > 2400:
            self.y, self.x = 0, self.x + 280
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n

    def link(self, a, a_out, b, b_in):
        if not MEL.connect_material_expressions(a, a_out, b, b_in):
            warn(f"ligação {a.get_name()}.{a_out} -> {b.get_name()}.{b_in} falhou")

    def op(self, cls, a, b, a_out="", b_out=""):
        n = self.node(cls)
        self.link(a, a_out, n, "A")
        self.link(b, b_out, n, "B")
        return n

    def opc(self, cls, a, c, a_out=""):
        n = self.node(cls, const_b=c)
        self.link(a, a_out, n, "A")
        return n

    def mask(self, src, ch, out=""):
        n = self.node(unreal.MaterialExpressionComponentMask, r="r" in ch, g="g" in ch, b="b" in ch, a="a" in ch)
        self.link(src, out, n, "")
        return n

    def one(self, cls, src, out=""):
        n = self.node(cls)
        self.link(src, out, n, "")
        return n

    def lerp(self, a, b_, alpha, a_out="", b_out="", alpha_out=""):
        n = self.node(unreal.MaterialExpressionLinearInterpolate)
        self.link(a, a_out, n, "A")
        self.link(b_, b_out, n, "B")
        self.link(alpha, alpha_out, n, "Alpha")
        return n

    def vec(self, x, y, z):
        return self.node(unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(x, y, z, 1))

    def const(self, v):
        return self.node(unreal.MaterialExpressionConstant, r=float(v))

    def scalar(self, name, v):
        return self.node(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=float(v))

    def color(self, name, r, g, b_):
        return self.node(unreal.MaterialExpressionVectorParameter, parameter_name=name, default_value=unreal.LinearColor(r, g, b_, 1))


def material(blades, ground):
    path = f"{DIR}/M_Grama_Tufo"
    if EAL.does_asset_exist(path):
        log("M_Grama_Tufo já existe (mantido; ajuste pelo MI_Grama_Tufo)")
        return EAL.load_asset(path)
    b = B(path)
    m = b.m
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property("two_sided", True)
    m.set_editor_property("opacity_mask_clip_value", 0.4)
    try_set(m, "tangent_space_normal", False, "M_Grama_Tufo")  # normal em espaço de mundo: (0,0,1) = para cima
    try_set(m, "used_with_instanced_static_meshes", True, "M_Grama_Tufo")
    # ---- textura das lâminas (dado)
    lam = b.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="Laminas", texture=blades,
                 sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    # ---- cor do chão no mesmo lugar (mesma conta do M_Cidade_Chao)
    wp = b.node(unreal.MaterialExpressionWorldPosition)
    xy = b.mask(wp, "rg")
    uv = b.op(unreal.MaterialExpressionDivide, xy, b.scalar("GroundTileCm", GROUND_TILE_CM))
    uv2 = b.opc(unreal.MaterialExpressionMultiply, uv, 0.23)
    if ground is not None:
        g1 = b.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="GroundD", texture=ground)
        b.link(uv, "", g1, "UVs")
        g2 = b.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="GroundD_Macro", texture=ground)
        b.link(uv2, "", g2, "UVs")
        gcol = b.lerp(g1, g2, b.scalar("GroundMacro", GROUND_MACRO), a_out="RGB", b_out="RGB")
    else:
        warn(f"falta {GROUND_TEX}: cor do chão fixa (GroundColor)")
        gcol = b.color("GroundColor", 0.30, 0.20, 0.45)
    gcol = b.op(unreal.MaterialExpressionMultiply, gcol, b.color("GroundTint", 1.0, 1.0, 1.0))
    # ---- base escura -> ponta clara
    hb = b.mask(lam, "r", "RGBA")
    col = b.op(unreal.MaterialExpressionMultiply, gcol, b.lerp(b.scalar("BaseDark", 0.6), b.const(1.0), hb))
    pw =b.node(unreal.MaterialExpressionPower, const_exponent=2.5)
    b.link(hb, "", pw, "Base")
    tipw = b.op(unreal.MaterialExpressionMultiply, pw, b.scalar("TipAmount", 0.35))
    tipc = b.color("TipColor", 0.45, 0.95, 1.0)
    col = b.lerp(col, tipc, tipw)
    # ---- variação por tufo e por lâmina, dobra cartunesca
    pir = b.node(unreal.MaterialExpressionPerInstanceRandom)
    var_t = b.lerp(b.scalar("VarMin", 0.86), b.scalar("VarMax", 1.14), pir)
    var_l = b.lerp(b.const(0.9), b.const(1.1), b.mask(lam, "g", "RGBA"))
    col = b.op(unreal.MaterialExpressionMultiply, col, b.op(unreal.MaterialExpressionMultiply, var_t, var_l))
    col = b.op(unreal.MaterialExpressionMultiply, col, b.mask(lam, "b", "RGBA"))
    MEL.connect_material_property(col, "", MP.MP_BASE_COLOR)
    MEL.connect_material_property(b.scalar("Roughness", 0.85), "", MP.MP_ROUGHNESS)
    MEL.connect_material_property(b.scalar("Specular", 0.25), "", MP.MP_SPECULAR)
    MEL.connect_material_property(b.op(unreal.MaterialExpressionMultiply, b.op(unreal.MaterialExpressionMultiply, tipc, tipw),
                                       b.scalar("TipGlow", 0.06)), "", MP.MP_EMISSIVE_COLOR)
    # ---- normal para cima (BackFix = 1 vira o verso, se o motor inverter o lado de trás)
    up = b.vec(0, 0, 1)
    sgn = b.node(unreal.MaterialExpressionTwoSidedSign)
    nrm = b.lerp(up, b.op(unreal.MaterialExpressionMultiply, up, sgn), b.scalar("BackFix", 0.0))
    MEL.connect_material_property(nrm, "", MP.MP_NORMAL)
    # ---- recorte, afinando com a distância
    try:
        fade = b.node(unreal.MaterialExpressionPerInstanceFadeAmount)
        op_mask = b.op(unreal.MaterialExpressionSubtract, lam, fade, a_out="A")
    except Exception as exc:  # noqa: BLE001
        warn(f"PerInstanceFadeAmount ({exc}): sem afinar na distância")
        op_mask = b.mask(lam, "a", "RGBA")
    MEL.connect_material_property(op_mask, "", MP.MP_OPACITY_MASK)
    # ---- vento: peso (1 - V)^2, fase pela posição do tufo
    tc = b.node(unreal.MaterialExpressionTextureCoordinate)
    hf = b.one(unreal.MaterialExpressionOneMinus, b.mask(tc, "g"))
    w2 = b.op(unreal.MaterialExpressionMultiply, hf, hf)
    obj = b.node(unreal.MaterialExpressionObjectPositionWS)
    phase = b.op(unreal.MaterialExpressionAdd, b.opc(unreal.MaterialExpressionMultiply, b.mask(obj, "r"), 0.011),
                 b.opc(unreal.MaterialExpressionMultiply, b.mask(obj, "g"), 0.007))
    t = b.op(unreal.MaterialExpressionMultiply, b.node(unreal.MaterialExpressionTime), b.scalar("WindSpeed", 1.4))
    s1 = b.one(unreal.MaterialExpressionSine, b.op(unreal.MaterialExpressionAdd, t, phase))
    s2 = b.one(unreal.MaterialExpressionSine, b.op(unreal.MaterialExpressionAdd, b.opc(unreal.MaterialExpressionMultiply, t, 2.3),
                                                   b.opc(unreal.MaterialExpressionMultiply, phase, 1.7)))
    wave = b.op(unreal.MaterialExpressionAdd, b.opc(unreal.MaterialExpressionMultiply, s1, 0.65),
                b.opc(unreal.MaterialExpressionMultiply, s2, 0.35))
    wave = b.op(unreal.MaterialExpressionAdd, wave, b.scalar("WindBend", 0.35))
    sway = b.op(unreal.MaterialExpressionMultiply, b.op(unreal.MaterialExpressionMultiply, wave, w2), b.scalar("WindStrength", 5.0))
    wdir = b.color("WindDir", 0.8, 0.6, 0.0)
    MEL.connect_material_property(b.op(unreal.MaterialExpressionMultiply, b.mask(wdir, "rgb"), sway), "",
                                  MP.MP_WORLD_POSITION_OFFSET)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    log("M_Grama_Tufo criado (masked, dois lados, normal para cima, cor do chão, vento, sumiço suave)")
    return m


def material_instance(parent):
    path = f"{DIR}/MI_Grama_Tufo"
    mi = EAL.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        "MI_Grama_Tufo", DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    EAL.save_loaded_asset(mi)
    return mi


def pp_float(v):
    p = unreal.PerPlatformFloat()
    p.set_editor_property("default", float(v))
    return p


def pp_int(v):
    p = unreal.PerPlatformInt()
    p.set_editor_property("default", int(v))
    return p


def grass_type(meshes):
    path = f"{DIR}/LGT_Cidade_Grama"
    lgt = EAL.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        "LGT_Cidade_Grama", DIR, unreal.LandscapeGrassType, unreal.LandscapeGrassTypeFactory())
    out = []
    for name, m in meshes:
        dens, smin, smax, c0, c1 = TUFTS[name]
        v = unreal.GrassVariety()
        v.set_editor_property("grass_mesh", m)
        for k, val in (("grass_density", pp_float(dens)), ("start_cull_distance", pp_int(c0)),
                       ("end_cull_distance", pp_int(c1))):
            try_set(v, k, val, name)
        for k, val in (("use_grid", True), ("placement_jitter", 1.0), ("random_rotation", True), ("align_to_surface", True),
                       ("cast_dynamic_shadow", False), ("receives_decals", False), ("use_landscape_lightmap", False),
                       ("weight_attenuates_max_scale", True), ("max_scale_weight_attenuation", 0.6)):
            try_set(v, k, val, name)
        try:
            v.set_editor_property("scaling", unreal.GrassScaling.UNIFORM)
            v.set_editor_property("scale_x", unreal.FloatInterval(smin, smax))
        except Exception as exc:  # noqa: BLE001
            warn(f"{name}: escala ({exc})")
        out.append(v)
    lgt.set_editor_property("grass_varieties", out)
    EAL.save_loaded_asset(lgt)
    log(f"LGT_Cidade_Grama com {len(out)} tufos (os SM_Grama_0..3 do billboard saíram)")
    return lgt


def main():
    blades = imp("T_Grama_Laminas.png", "T_Grama_Laminas")
    blades.set_editor_property("srgb", False)
    try_set(blades, "compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT, "T_Grama_Laminas")
    try_set(blades, "address_x", unreal.TextureAddress.TA_WRAP, "T_Grama_Laminas")
    # mips mantêm a cobertura do recorte (a grama não "some" de longe)
    if try_set(blades, "do_scale_mips_for_alpha_coverage", True, "T_Grama_Laminas"):
        try_set(blades, "alpha_coverage_thresholds", unreal.Vector4(0, 0, 0, 0.4), "T_Grama_Laminas")
    EAL.save_loaded_asset(blades)
    ground = EAL.load_asset(GROUND_TEX) if EAL.does_asset_exist(GROUND_TEX) else None
    mat = material(blades, ground)
    mi = material_instance(mat)
    meshes = []
    for name in TUFTS:
        m = imp(f"{name}.fbx", name, fbx_options())
        m.set_material(0, mi)
        try:
            body = m.get_editor_property("body_setup")
            if body:
                body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
        except Exception:  # noqa: BLE001
            pass
        bb = m.get_bounding_box()
        R.setdefault("tufos", {})[name] = {"h_cm": round(bb.max.z - bb.min.z, 1), "w_cm": round(bb.max.x - bb.min.x, 1)}
        EAL.save_loaded_asset(m)
        meshes.append((name, m))
    log(f"{len(meshes)} tufos importados com MI_Grama_Tufo: {R['tufos']}")
    for name, (_, _, _, _, _) in TUFTS.items():
        h = R["tufos"][name]["h_cm"]
        if h < 10 or h > 200:
            warn(f"{name} com {h} cm de altura: a escala do FBX veio errada (esperado 30 a 75 cm)")
    grass_type(meshes)
    try:
        unreal.SystemLibrary.execute_console_command(None, "grass.FlushCache")
        log("grass.FlushCache (o chão refaz os tufos)")
    except Exception as exc:  # noqa: BLE001
        warn(f"grass.FlushCache: {exc}")


try:
    main()
except Exception as exc:  # noqa: BLE001
    R["errors"].append(str(exc))
    unreal.log_error(f"[grass] {exc}\n{traceback.format_exc()[-1500:]}")
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_grass.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[grass] fim | avisos {len(R['warnings'])} | erros {len(R['errors'])}")
