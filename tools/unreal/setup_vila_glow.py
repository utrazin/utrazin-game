"""[A-090] Brilho dos cristais (portão, muro, torre) e campo de força do portão (item 7 do handoff de 23/11).

RODA NO EDITOR (caixa Cmd, sem Play):
  py "E:/game/utrazin-game/tools/unreal/setup_vila_glow.py"

Problema: M_User_Prop só tem cor base (EmissiveStrength 0): os cristais ciano/roxos da arte ficavam apagados e o
arco do portão vazio.
O que faz (sem recriar material em uso: isso derruba a Unreal, assert !IsRooted):
  1. M_User_PropGlow (novo): igual ao M_User_Prop + brilho só nos pixels "de cristal" da própria textura
     (ciano: verde e azul altos com pouco vermelho; roxo: vermelho e azul altos com pouco verde), pulsando devagar.
  2. MI_BLD_PortaoArena / MuroArena / TorreArena passam a ser filhos dele (troca só o pai; texturas ficam).
  3. M_ForceField (novo): campo de força azul (aditivo, ruído correndo para cima, linhas de varredura, borda forte
     pelo fresnel). O C++ (arena) e o dress_city_v4.py (cidade) põem um plano com ele no arco do portão.
Relatório: reports/setup_vila_glow.json. Ajuste fino: GlowStrength / CrystalThreshold nas MIs (Details).
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
MATS = "/Game/Environment/User/Materials"
REMAP_MATS = "/Game/Materials/Remap"
VILA_MI = "/Game/Environment/User/Vila/Materials"
R = {"steps": [], "warnings": [], "errors": []}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[vila_glow] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[vila_glow] {m}")


class B:
    """Construtor simples de material (só para material NOVO)."""

    def __init__(self, path):
        folder, name = path.rsplit("/", 1)
        EAL.make_directory(folder)
        self.m = TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
        self.x = -1600

    def node(self, cls, **props):
        n = MEL.create_material_expression(self.m, cls, self.x, 0)
        self.x += 40
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

    def mask(self, src, ch):
        n = self.node(unreal.MaterialExpressionComponentMask, r="r" in ch, g="g" in ch, b="b" in ch, a="a" in ch)
        self.link(src, "", n, "")
        return n

    def one(self, cls, src, out=""):
        n = self.node(cls)
        self.link(src, out, n, "")
        return n

    def out(self, n, prop, n_out=""):
        MEL.connect_material_property(n, n_out, prop)

    def finish(self):
        MEL.recompile_material(self.m)
        EAL.save_loaded_asset(self.m)
        return self.m


def prop_glow():
    path = f"{MATS}/M_User_PropGlow"
    if EAL.does_asset_exist(path):
        log("M_User_PropGlow já existe (mantido)")
        return EAL.load_asset(path)
    b = B(path)
    b.m.set_editor_property("two_sided", True)
    tex = b.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="BaseColor")
    tint = b.node(unreal.MaterialExpressionVectorParameter, parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
    col = b.op(unreal.MaterialExpressionMultiply, tex, tint, a_out="RGB")
    b.out(col, MP.MP_BASE_COLOR)
    b.out(b.node(unreal.MaterialExpressionScalarParameter, parameter_name="Roughness", default_value=0.75), MP.MP_ROUGHNESS)
    b.out(b.node(unreal.MaterialExpressionScalarParameter, parameter_name="Metallic", default_value=0.0), MP.MP_METALLIC)
    r, g, bl = b.mask(tex, "r"), b.mask(tex, "g"), b.mask(tex, "b")
    # ciano: min(G, B) - R ; roxo: min(R, B) - G
    cyan = b.op(unreal.MaterialExpressionSubtract, b.op(unreal.MaterialExpressionMin, g, bl), r)
    purple = b.op(unreal.MaterialExpressionSubtract, b.op(unreal.MaterialExpressionMin, r, bl), g)
    crystal = b.op(unreal.MaterialExpressionMax, cyan, purple)
    thr = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="CrystalThreshold", default_value=0.12)
    soft = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="CrystalSoftness", default_value=0.18)
    m = b.op(unreal.MaterialExpressionDivide, b.op(unreal.MaterialExpressionSubtract, crystal, thr), soft)
    m = b.one(unreal.MaterialExpressionSaturate, m)
    # pulso lento: 0,75 a 1,0 (0,875 + 0,125 x seno)
    t = b.node(unreal.MaterialExpressionTime)
    speed = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="PulseSpeed", default_value=1.3)
    sn = b.one(unreal.MaterialExpressionSine, b.op(unreal.MaterialExpressionMultiply, t, speed))
    k = b.node(unreal.MaterialExpressionMultiply, const_b=0.125)
    b.link(sn, "", k, "A")
    pulse = b.node(unreal.MaterialExpressionAdd, const_b=0.875)
    b.link(k, "", pulse, "A")
    strength = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="GlowStrength", default_value=6.0)
    em = b.op(unreal.MaterialExpressionMultiply, b.op(unreal.MaterialExpressionMultiply, col, m), b.op(unreal.MaterialExpressionMultiply, strength, pulse))
    b.out(em, MP.MP_EMISSIVE_COLOR)
    log("M_User_PropGlow criado")
    return b.finish()


def force_field():
    path = f"{REMAP_MATS}/M_ForceField"
    if EAL.does_asset_exist(path):
        log("M_ForceField já existe (mantido)")
        return EAL.load_asset(path)
    b = B(path)
    b.m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    b.m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    b.m.set_editor_property("two_sided", True)
    color = b.node(unreal.MaterialExpressionVectorParameter, parameter_name="Color", default_value=unreal.LinearColor(0.15, 0.6, 1.0, 1))
    inten = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="Intensity", default_value=2.2)
    # ruído que sobe devagar (posição do mundo + tempo)
    wp = b.node(unreal.MaterialExpressionWorldPosition)
    t = b.node(unreal.MaterialExpressionTime)
    rise = b.node(unreal.MaterialExpressionMultiply, const_b=60.0)
    b.link(t, "", rise, "A")
    up = b.node(unreal.MaterialExpressionAppendVector)
    zero2 = b.node(unreal.MaterialExpressionConstant2Vector, r=0.0, g=0.0)
    b.link(zero2, "", up, "A")
    b.link(rise, "", up, "B")
    pos = b.op(unreal.MaterialExpressionSubtract, wp, up)
    noise = b.node(unreal.MaterialExpressionNoise, scale=0.012, levels=3, output_min=0.25, output_max=1.0)
    b.link(pos, "", noise, "Position")
    # linhas de varredura horizontais correndo para cima: (0,5 + 0,5 x seno(z x 0,05 - subida))^8
    zs = b.node(unreal.MaterialExpressionMultiply, const_b=0.05)
    b.link(b.mask(wp, "b"), "", zs, "A")
    scan = b.one(unreal.MaterialExpressionSine, b.op(unreal.MaterialExpressionSubtract, zs, rise))
    half = b.node(unreal.MaterialExpressionMultiply, const_b=0.5)
    b.link(scan, "", half, "A")
    scan01 = b.node(unreal.MaterialExpressionAdd, const_b=0.5)
    b.link(half, "", scan01, "A")
    scanp = b.node(unreal.MaterialExpressionPower, const_exponent=8.0)
    b.link(scan01, "", scanp, "Base")
    # borda forte (fresnel) + miolo quase transparente
    fres = b.node(unreal.MaterialExpressionFresnel, exponent=2.5, base_reflect_fraction=0.15)
    nz = b.node(unreal.MaterialExpressionMultiply, const_b=0.35)
    b.link(noise, "", nz, "A")
    sum2 = b.op(unreal.MaterialExpressionAdd, b.op(unreal.MaterialExpressionAdd, nz, scanp), fres)
    em = b.op(unreal.MaterialExpressionMultiply, b.op(unreal.MaterialExpressionMultiply, color, inten), sum2)
    b.out(em, MP.MP_EMISSIVE_COLOR)
    log("M_ForceField criado")
    return b.finish()


INTERIOR_MI = "/Game/Environment/User/Interior/Materials"
INTERIOR = ("INT_Balcao", "INT_Prateleira", "INT_Bancada", "INT_SuporteArmas", "INT_Cama", "INT_Mesa", "INT_Cadeira",
            "INT_Armario", "INT_Caixotes", "INT_Luminaria")


def reparent(parent):
    # [A-093] móveis do Forge: faixas ciano e cristais roxos brilham pelo mesmo M_User_PropGlow
    names = [f"{VILA_MI}/{n}" for n in ("MI_BLD_PortaoArena", "MI_BLD_MuroArena", "MI_BLD_TorreArena")]
    names += [f"{INTERIOR_MI}/MI_{n}" for n in INTERIOR]
    for p in names:
        name = p.rsplit("/", 1)[1]
        if not EAL.does_asset_exist(p):
            warn(f"não existe {p}")
            continue
        mi = EAL.load_asset(p)
        if mi.get_editor_property("parent") == parent:
            log(f"{name} já é filho do M_User_PropGlow")
            continue
        MEL.set_material_instance_parent(mi, parent)
        MEL.update_material_instance(mi)
        EAL.save_loaded_asset(mi)
        log(f"{name} agora brilha nos cristais")


def main():
    import stat
    content = os.path.join(REPO, "unreal", "JogoResgate", "Content")
    for sub in (("Environment", "User", "Vila", "Materials"), ("Environment", "User", "Materials"), ("Materials", "Remap"),
                ("Environment", "User", "Interior", "Materials")):
        d = os.path.join(content, *sub)
        if os.path.isdir(d):
            for f in os.listdir(d):
                try:
                    os.chmod(os.path.join(d, f), stat.S_IWRITE | stat.S_IREAD)
                except OSError:
                    pass
    glow = prop_glow()
    force_field()
    reparent(glow)


try:
    main()
except Exception as exc:  # noqa: BLE001
    R["errors"].append(str(exc))
    unreal.log_error(f"[vila_glow] {exc}\n{traceback.format_exc()[-1500:]}")
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_vila_glow.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[vila_glow] fim | avisos {len(R['warnings'])} | erros {len(R['errors'])}")
