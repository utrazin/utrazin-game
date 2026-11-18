"""Materiais da pistola (item 17) e do terreno da L01 (item 16), sem refazer o resto (A-066). Pode rodar de novo.

RODA NO EDITOR (caixa Cmd, sem Play):
  py "E:/game/utrazin-game/tools/unreal/fix_l01_materiais.py"
Relatório: reports/fix_l01_materiais.json. O setup_wave1.py (mat_pistol e mat_terrain) usa as mesmas funções.

Item 17, pistola sem cor. Causa (reports/setup_wave1.json, erro em mat_pistol): a importação do FBX criou
M_Pistol_Body/Trim/Glow como MaterialInstanceConstant, e o setup_wave1 tentava apagar os nós delas como se
fossem Material ("Cannot nativize 'MaterialInstanceConstant' as 'Material'"). A textura
T_AlienPistol_BaseColor nunca foi ligada. Agora: material mestre M_AlienPistol_Master (textura como parâmetro
BaseColor) e cada M_Pistol_* vira instância dele; os slots da malha SM_AlienPistol são conferidos.

Item 16, terreno repetindo nos morros. Causa: M_L01_Terrain projetava tudo de cima (X e Y do mundo) com
ladrilho de 4 m, inclusive a rocha das encostas: nos morros a textura estica e o mosaico aparece. Agora:
 - cada camada de cor é lida em DUAS escalas (4 m e 10,84 m, razão não inteira) misturadas por ruído de 37 m;
 - a rocha das encostas usa projeção de lado (X/Z e Y/Z, misturadas pela normal) em vez de esticar a de cima;
 - normal da rocha suavizada na encosta (a normal de cima esticada fazia listras);
 - variação grande de cor em 60 m (como antes);
 - amostradores compartilhados (Shared: Wrap) para passar do limite de 16 texturas.
"""
import json
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
TEX = "/Game/Environment/Textures"
MATS = "/Game/Environment/L01/Materials"
WEAPONS = "/Game/Weapons"
PISTOL_MESH = f"{WEAPONS}/SM_AlienPistol"
PISTOL_TEX = f"{WEAPONS}/T_AlienPistol_BaseColor"
PISTOL_MASTER = f"{WEAPONS}/M_AlienPistol_Master"
# nome: (rugosidade, metálico, brilho). Brilho da parte Glow 2,0 (era 5; a exposição fixa estoura; ver A-063)
PISTOL_PARTS = {"M_Pistol_Body": (0.45, 0.2, 0.0), "M_Pistol_Trim": (0.45, 0.6, 0.0), "M_Pistol_Glow": (0.3, 0.2, 2.0)}
TERRAIN_TILE_CM = 400.0
TERRAIN_TILE2_CM = 1084.0          # 2,71 x: não alinha com a escala de 4 m
TERRAIN_MIX_CM = 3700.0
ROCK_TILE_CM = 600.0
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "pistol": {}, "terrain": {}}


def _log(m):
    R["steps"].append(m)
    unreal.log(f"[fix_l01_materiais] {m}")


def _warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[fix_l01_materiais] {m}")


class Builder:
    """Monta um Material por nós. Só aceita Material (instância não tem nós: era o bug da pistola)."""

    def __init__(self, path, warn=_warn):
        self.warn = warn
        folder, name = path.rsplit("/", 1)
        EAL.make_directory(folder)
        if EAL.does_asset_exist(path):
            m = EAL.load_asset(path)
            if not isinstance(m, unreal.Material):
                raise TypeError(f"{path} é {type(m).__name__}, não Material: não dá para refazer os nós")
            self.m = m
            MEL.delete_all_material_expressions(self.m)
        else:
            self.m = TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
        self.x, self.y = -2200, 0

    def node(self, cls, **props):
        e = MEL.create_material_expression(self.m, cls, self.x, self.y)
        self.y += 140
        if self.y > 3000:
            self.y, self.x = 0, self.x + 280
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def link(self, a, a_out, b, b_in):
        if not MEL.connect_material_expressions(a, a_out, b, b_in):
            self.warn(f"{self.m.get_name()}: ligação {a.get_name()}.{a_out} -> {b.get_name()}.{b_in} falhou")

    def out(self, e, prop, e_out=""):
        MEL.connect_material_property(e, e_out, prop)

    def const(self, v):
        return self.node(unreal.MaterialExpressionConstant, r=float(v))

    def op(self, cls, a, b=None, cb=None, a_out="", b_out=""):
        e = self.node(cls)
        self.link(a, a_out, e, "A")
        if b is not None:
            self.link(b, b_out, e, "B")
        elif cb is not None:
            e.set_editor_property("const_b", float(cb))
        return e

    def mul(self, a, b=None, cb=None, a_out="", b_out=""):
        return self.op(unreal.MaterialExpressionMultiply, a, b, cb, a_out, b_out)

    def lerp(self, a, b, alpha, a_out="", b_out="", al_out="", ca=None, cb=None):
        e = self.node(unreal.MaterialExpressionLinearInterpolate)
        if a is not None:
            self.link(a, a_out, e, "A")
        else:
            e.set_editor_property("const_a", float(ca))
        if b is not None:
            self.link(b, b_out, e, "B")
        else:
            e.set_editor_property("const_b", float(cb))
        self.link(alpha, al_out, e, "Alpha")
        return e

    def sat(self, a, a_out=""):
        e = self.node(unreal.MaterialExpressionSaturate)
        self.link(a, a_out, e, "")
        return e

    def tex(self, name, uv=None, normal=False, mask=False):
        t = EAL.load_asset(name if "/" in name else f"{TEX}/{name}")
        if t is None:
            raise RuntimeError(f"textura ausente: {name}")
        e = self.node(unreal.MaterialExpressionTextureSample, texture=t)
        st = unreal.MaterialSamplerType
        if normal:
            e.set_editor_property("sampler_type", st.SAMPLERTYPE_NORMAL)
        elif mask:
            e.set_editor_property("sampler_type", st.SAMPLERTYPE_LINEAR_GRAYSCALE)
        try:   # amostrador compartilhado: libera mais de 16 texturas no material
            e.set_editor_property("sampler_source", unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        except Exception as exc:  # noqa: BLE001
            self.warn(f"sampler_source: {exc}")
        if uv is not None:
            self.link(uv, "", e, "UVs")
        return e

    def proj(self, tile_cm, axes="xy"):
        """UV alinhado ao mundo: 'xy' (de cima), 'xz' (de frente), 'yz' (de lado), em ladrilhos de tile_cm."""
        wp = self.node(unreal.MaterialExpressionWorldPosition)
        mask = self.node(unreal.MaterialExpressionComponentMask, r="x" in axes, g="y" in axes, b="z" in axes, a=False)
        self.link(wp, "", mask, "")
        d = self.node(unreal.MaterialExpressionDivide, const_b=float(tile_cm))
        self.link(mask, "", d, "A")
        return d

    def finish(self):
        MEL.recompile_material(self.m)
        EAL.save_loaded_asset(self.m, only_if_is_dirty=False)
        return self.m


# ====================================================================== item 17: pistola
def build_pistol(log=_log, warn=_warn):
    if not EAL.does_asset_exist(PISTOL_TEX):
        warn(f"{PISTOL_TEX} ausente (setup_wave1.py importa de assets/work/weapons/SM_AlienPistol.fbm): pistola sem cor")
        return None
    b = Builder(PISTOL_MASTER, warn)
    uv = b.node(unreal.MaterialExpressionTextureCoordinate)
    col = b.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="BaseColor",
                 texture=EAL.load_asset(PISTOL_TEX))
    b.link(uv, "", col, "UVs")
    b.out(col, MP.MP_BASE_COLOR)
    rough = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="Roughness", default_value=0.45)
    metal = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="Metallic", default_value=0.2)
    glow = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="EmissiveStrength", default_value=0.0)
    b.out(rough, MP.MP_ROUGHNESS)
    b.out(metal, MP.MP_METALLIC)
    b.out(b.mul(col, glow, a_out="RGB"), MP.MP_EMISSIVE_COLOR)
    master = b.finish()
    log("M_AlienPistol_Master pronto (textura T_AlienPistol_BaseColor)")
    tex = EAL.load_asset(PISTOL_TEX)
    parts = {}
    for name, (r, m, e) in PISTOL_PARTS.items():
        path = f"{WEAPONS}/{name}"
        asset = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
        if isinstance(asset, unreal.Material):
            # sobra de uma versão antiga em que M_Pistol_* era Material: refaz com a textura (sem trocar o tipo)
            bm = Builder(path, warn)
            d = bm.tex(PISTOL_TEX, bm.node(unreal.MaterialExpressionTextureCoordinate))
            bm.out(d, MP.MP_BASE_COLOR)
            bm.out(bm.const(r), MP.MP_ROUGHNESS)
            bm.out(bm.const(m), MP.MP_METALLIC)
            if e:
                bm.out(bm.mul(d, cb=e), MP.MP_EMISSIVE_COLOR)
            parts[name] = bm.finish()
            R["pistol"][name] = "Material refeito com a textura"
            continue
        if asset is None:
            asset = TOOLS.create_asset(name, WEAPONS, unreal.MaterialInstanceConstant,
                                       unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(asset, master)
        MEL.set_material_instance_texture_parameter_value(asset, "BaseColor", tex)
        MEL.set_material_instance_scalar_parameter_value(asset, "Roughness", float(r))
        MEL.set_material_instance_scalar_parameter_value(asset, "Metallic", float(m))
        MEL.set_material_instance_scalar_parameter_value(asset, "EmissiveStrength", float(e))
        MEL.update_material_instance(asset)
        EAL.save_loaded_asset(asset, only_if_is_dirty=False)
        parts[name] = asset
        R["pistol"][name] = "instância de M_AlienPistol_Master"
    log("M_Pistol_Body/Trim/Glow com a textura da pistola")
    # slots da malha: cada um precisa apontar para uma das 3 (nome do slot decide; o resto vira Body)
    if EAL.does_asset_exist(PISTOL_MESH):
        sm = EAL.load_asset(PISTOL_MESH)
        slots = []
        changed = False
        for i, s in enumerate(sm.get_editor_property("static_materials")):
            slot = str(s.get_editor_property("material_slot_name"))
            cur = s.get_editor_property("material_interface")
            curp = cur.get_path_name().split(".")[0] if cur else ""
            want = next((parts[n] for n in parts if n.split("_")[-1].lower() in slot.lower()), parts.get("M_Pistol_Body"))
            if want is not None and not any(curp.endswith(n) for n in parts):
                sm.set_material(i, want)
                changed = True
            slots.append({"slot": slot, "antes": curp,
                          "depois": want.get_path_name().split(".")[0] if (want and changed) else curp})
        if changed:
            EAL.save_loaded_asset(sm, only_if_is_dirty=False)
        R["pistol"]["slots"] = slots
        log(f"SM_AlienPistol: {len(slots)} slots conferidos{' (corrigidos)' if changed else ''}")
    return master


# ====================================================================== item 16: terreno
def build_terrain(log=_log, warn=_warn):
    b = Builder(f"{MATS}/M_L01_Terrain", warn)
    uv1 = b.proj(TERRAIN_TILE_CM)
    uv2 = b.proj(TERRAIN_TILE2_CM)
    # máscara que troca entre as duas escalas (ruído de 37 m, contraste alto)
    mix_n = b.tex("T_Detail_Grunge", b.proj(TERRAIN_MIX_CM), mask=True)
    mix = b.sat(b.mul(b.op(unreal.MaterialExpressionSubtract, mix_n, cb=0.35), cb=2.5))
    vc = b.node(unreal.MaterialExpressionVertexColor)
    layers = [("T_AlienMoss", None), ("T_RedSand", "R"), ("T_AlienGrass", "G"), ("T_Dirt", "B")]
    col = nrm = None
    for name, ch in layers:
        d = b.lerp(b.tex(f"{name}_D", uv1), b.tex(f"{name}_D", uv2), mix)
        n = b.tex(f"{name}_N", uv1, normal=True)
        if col is None:
            col, nrm = d, n
        else:
            col = b.lerp(col, d, vc, al_out=ch)
            nrm = b.lerp(nrm, n, vc, al_out=ch)
    # normal do mundo: z para a máscara de rocha, x/y para escolher a projeção de lado
    vn = b.node(unreal.MaterialExpressionVertexNormalWS)
    nz = b.node(unreal.MaterialExpressionComponentMask, r=False, g=False, b=True, a=False)
    b.link(vn, "", nz, "")
    rk = b.sat(b.mul(b.op(unreal.MaterialExpressionSubtract, b.const(0.82), nz), cb=6.0))      # 1 = encosta
    side = b.sat(b.mul(b.op(unreal.MaterialExpressionSubtract, b.const(0.9), nz), cb=3.0))     # 1 = parede
    ab = b.node(unreal.MaterialExpressionAbs)
    b.link(vn, "", ab, "")
    ax = b.node(unreal.MaterialExpressionComponentMask, r=True, g=False, b=False, a=False)
    ay = b.node(unreal.MaterialExpressionComponentMask, r=False, g=True, b=False, a=False)
    b.link(ab, "", ax, "")
    b.link(ab, "", ay, "")
    den = b.op(unreal.MaterialExpressionAdd, b.op(unreal.MaterialExpressionAdd, ax, ay), cb=0.001)
    wy = b.op(unreal.MaterialExpressionDivide, ay, den)          # normal mais em Y = olha de frente (plano XZ)
    rock_top = b.tex("T_CrystalRock_D", b.proj(ROCK_TILE_CM, "xy"))
    rock_yz = b.tex("T_CrystalRock_D", b.proj(ROCK_TILE_CM, "yz"))
    rock_xz = b.tex("T_CrystalRock_D", b.proj(ROCK_TILE_CM, "xz"))
    rock_side = b.lerp(rock_yz, rock_xz, wy)
    rock = b.lerp(rock_top, rock_side, side)
    flat = b.node(unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(0.0, 0.0, 1.0, 1.0))
    rock_n = b.lerp(b.tex("T_CrystalRock_N", b.proj(ROCK_TILE_CM, "xy"), normal=True), flat,
                    b.mul(side, cb=0.7))
    col = b.lerp(col, rock, rk)
    nrm = b.lerp(nrm, rock_n, rk)
    # variação grande (quebra a repetição de longe)
    macro = b.tex("T_Detail_Grunge", b.proj(6000.0), mask=True)
    var = b.lerp(None, None, macro, ca=0.72, cb=1.15)
    b.out(b.mul(col, var), MP.MP_BASE_COLOR)
    b.out(nrm, MP.MP_NORMAL)
    b.out(b.const(0.92), MP.MP_ROUGHNESS)
    m = b.finish()
    R["terrain"] = {"material": f"{MATS}/M_L01_Terrain", "escalas_cm": [TERRAIN_TILE_CM, TERRAIN_TILE2_CM],
                    "mistura_cm": TERRAIN_MIX_CM, "rocha": "cima + lado (XZ/YZ)", "amostras": 18}
    log("M_L01_Terrain refeito (duas escalas + rocha projetada de lado)")
    return m


def main():
    for name, fn in (("pistola", build_pistol), ("terreno", build_terrain)):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            R["errors"].append({"where": name, "e": str(exc), "t": traceback.format_exc()[-800:]})
            unreal.log_error(f"[fix_l01_materiais] {name}: {exc}")
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception as exc:  # noqa: BLE001
        R["errors"].append({"where": "salvar", "e": str(exc)})
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "fix_l01_materiais.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[fix_l01_materiais] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")


# importado pelo setup_wave1.py (mat_pistol/mat_terrain) só usa as funções; rodado com py, faz tudo
if __name__ != "fix_l01_materiais":
    main()
