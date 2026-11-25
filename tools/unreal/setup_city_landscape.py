"""[A-091] Material do chão da cidade (Landscape) a partir da máscara gerada (assets/work/city_v4/city_mask.png).

RODA NO EDITOR (caixa Cmd, sem Play), com L_Cidade aberto e o Landscape já importado (passo a passo no fim do
docs/design/CIDADE_V4.md):
  py "E:/game/utrazin-game/tools/unreal/setup_city_landscape.py"

Rodar ANTES: setup_grass.py (a grama entra pelo material). Faz:
  [A-098] material novo M_Cidade_Chao3 (o 2 fica parado; recriar com o mesmo nome derruba a Unreal):
     - MaskOrigin/MaskSizeCm já nascem com os números da planta (antes o padrão era o da v4, 1008 m: se o mapa de
       grama fosse feito com o padrão, a grama saía no meio da rua)
     - grama com MARGEM: o peso da grama olha a máscara crua (sem ruído) em 13 pontos até GrassMarginCm (120 cm) em
       volta; asfalto, calçada/praça ou lama acima de 0,2 em qualquer um deles = zero grama. Terra apaga a grama
       (terra 0,85 em volta dos prédios = nada; terra 0,55 fora da muralha = grama rala), rocha também
     - no fim limpa o cache de grama (grass.FlushCache)
  1. importa a máscara como T_Cidade_Mascara (sem sRGB, sem compressão de cor: R asfalto, G concreto, B terra, A lama)
  2. cria M_Cidade_Chao (NOVO; se já existir, só é reaproveitado): grama alienígena por baixo, terra com borda
     irregular (ruído), concreto e asfalto com borda limpa, lama tóxica brilhando de leve, rocha nas encostas
     (pela inclinação). Duas escalas da mesma textura para não repetir. Samplers compartilhados (limite de 16).
  3. MI_Cidade_Chao com a posição/tamanho do Landscape real e aplica no Landscape do mapa aberto.
Relatório: reports/setup_city_landscape.json
"""
import json
import os
import traceback

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
DIR = "/Game/Environment/Cidade"
TEX = "/Game/Environment/Textures/User"
# [A-096] planta v5 (200 x 200 m) quando existir
_WORK = os.path.join(REPO, "assets", "work", "city_v6")  # [A-098]
if not os.path.isfile(os.path.join(_WORK, "city_layout.json")):
    _WORK = os.path.join(REPO, "assets", "work", "city_v5")
if not os.path.isfile(os.path.join(_WORK, "city_layout.json")):
    _WORK = os.path.join(REPO, "assets", "work", "city_v4")
MASK_FILE = os.path.join(_WORK, "city_mask.png")
LAYOUT_FILE = os.path.join(_WORK, "city_layout.json")
R = {"steps": [], "warnings": [], "errors": []}
# [A-095] o nome do enum muda entre versões; pega o primeiro que existir (sampler compartilhado evita o limite de 16)
SHARED = next(getattr(unreal.SamplerSourceMode, n) for n in
              ("SSM_WRAP_WORLD_GROUP_SETTINGS", "SSM_WRAP_WORLD_GROUP_SHARED", "SSM_FROM_TEXTURE_ASSET")
              if hasattr(unreal.SamplerSourceMode, n))
# camada: (textura, tamanho do ladrilho em cm)
LAYERS = {
    "grama": ("T_User_GramaAlien", 420.0),
    "terra": ("T_User_Terra", 380.0),
    "concreto": ("T_User_Concreto", 300.0),
    "asfalto": ("T_User_Asfalto", 520.0),
    "lama": ("T_User_LamaToxica", 450.0),
    "rocha": ("T_User_Pedra", 900.0),
}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[city_land] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[city_land] {m}")


def import_mask():
    path = f"{DIR}/T_Cidade_Mascara"
    task = unreal.AssetImportTask()
    task.filename = MASK_FILE
    task.destination_path = DIR
    task.destination_name = "T_Cidade_Mascara"
    task.automated = True
    task.replace_existing = True
    task.save = True
    TOOLS.import_asset_tasks([task])
    tex = EAL.load_asset(path)
    if tex is None:
        raise RuntimeError("máscara não importou")
    tex.set_editor_property("srgb", False)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP)
    tex.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
    tex.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
    EAL.save_loaded_asset(tex)
    log("T_Cidade_Mascara importada (sem sRGB, sem compressão de cor)")
    return tex


class B:
    def __init__(self, path):
        folder, name = path.rsplit("/", 1)
        EAL.make_directory(folder)
        self.m = TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
        self.x = -3000
        self.y = 0

    def node(self, cls, **props):
        n = MEL.create_material_expression(self.m, cls, self.x, self.y)
        self.y += 60
        if self.y > 3000:
            self.y = 0
            self.x += 260
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

    def opc(self, cls, a, const_b, a_out=""):
        n = self.node(cls, const_b=const_b)
        self.link(a, a_out, n, "A")
        return n

    def mask(self, src, ch, out=""):
        n = self.node(unreal.MaterialExpressionComponentMask, r="r" in ch, g="g" in ch, b="b" in ch, a="a" in ch)
        self.link(src, out, n, "")
        return n

    def link_any(self, a, outs, b, b_in):
        """[A-096] tenta os nomes de saída na ordem (o nome muda entre versões)."""
        for o in outs:
            if MEL.connect_material_expressions(a, o, b, b_in):
                return True
        warn(f"ligação {a.get_name()}.{outs} -> {b.get_name()}.{b_in} falhou")
        return False

    def one(self, cls, src, out=""):
        n = self.node(cls)
        self.link(src, out, n, "")
        return n

    def lerp(self, a, b_, alpha, a_out="", b_out=""):
        n = self.node(unreal.MaterialExpressionLinearInterpolate)
        self.link(a, a_out, n, "A")
        self.link(b_, b_out, n, "B")
        self.link(alpha, "", n, "Alpha")
        return n

    def tex(self, param, texture, uv, normal=False):
        t = self.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=param, texture=texture,
                      sampler_source=SHARED)
        if normal:
            t.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        self.link(uv, "", t, "UVs")
        return t

    def scalar(self, name, v):
        return self.node(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=v)


def build_material(mask_tex, layout):
    # [A-096] o M_Cidade_Chao antigo não compila (máscara A numa saída RGB) e recriar material com o mesmo nome
    # derruba a Unreal: o novo tem outro nome
    path = f"{DIR}/M_Cidade_Chao3"
    if EAL.does_asset_exist(path):
        log("M_Cidade_Chao3 já existe (mantido)")
        return EAL.load_asset(path)
    b = B(path)
    wp = b.node(unreal.MaterialExpressionWorldPosition)
    xy = b.mask(wp, "rg")
    # UV da máscara: (XY - origem) / tamanho
    # [A-098] padrão = planta atual (o MI sobrescreve com a posição real do Landscape)
    size_def = float(layout["landscape"]["size_m"]) * 100.0
    org = b.node(unreal.MaterialExpressionVectorParameter, parameter_name="MaskOrigin",
                 default_value=unreal.LinearColor(-size_def / 2.0, -size_def / 2.0, 0, 0))
    size = b.scalar("MaskSizeCm", size_def)
    muv = b.op(unreal.MaterialExpressionDivide, b.op(unreal.MaterialExpressionSubtract, xy, b.mask(org, "rg")), size)
    m = b.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="Mask", texture=mask_tex,
               sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    b.link(muv, "", m, "UVs")
    # ruído para bordas orgânicas
    nz = b.node(unreal.MaterialExpressionNoise, scale=0.0035, levels=4, output_min=-0.5, output_max=0.5)
    b.link_any(wp, ("", "XYZ", "Output"), nz, "Position")

    def edge(ch, sharp, noise_amt):
        w = b.mask(m, ch, "RGBA")  # [A-096] a máscara A precisa da saída RGBA (a "" é só RGB)
        w = b.op(unreal.MaterialExpressionAdd, w, b.opc(unreal.MaterialExpressionMultiply, nz, noise_amt))
        w = b.opc(unreal.MaterialExpressionSubtract, w, 0.5)
        w = b.opc(unreal.MaterialExpressionMultiply, w, sharp)
        w = b.opc(unreal.MaterialExpressionAdd, w, 0.5)
        return b.one(unreal.MaterialExpressionSaturate, w)

    w_asf = edge("r", 6.0, 0.08)
    w_con = edge("g", 6.0, 0.08)
    w_ter = edge("b", 3.0, 0.45)
    w_lam = edge("a", 3.0, 0.35)
    # inclinação: rocha onde a normal do mundo aponta pouco para cima
    vn = b.node(unreal.MaterialExpressionVertexNormalWS)
    nzc = b.mask(vn, "b")
    w_roc = b.one(unreal.MaterialExpressionSaturate,
                  b.opc(unreal.MaterialExpressionMultiply, b.op(unreal.MaterialExpressionSubtract, b.scalar("RockSlope", 0.82), nzc), 6.0))

    cols, nors = {}, {}
    for key, (tname, tile) in LAYERS.items():
        d = EAL.load_asset(f"{TEX}/{tname}_D")
        n = EAL.load_asset(f"{TEX}/{tname}_N")
        if d is None:
            warn(f"falta {TEX}/{tname}_D")
        uv = b.op(unreal.MaterialExpressionDivide, xy, b.scalar(f"Tile_{key}", tile))
        uv2 = b.opc(unreal.MaterialExpressionMultiply, uv, 0.23)  # segunda escala (quebra a repetição)
        c1 = b.tex(f"D_{key}", d, uv)
        c2 = b.tex(f"D_{key}_Macro", d, uv2)
        cols[key] = b.lerp(c1, c2, b.scalar(f"Macro_{key}", 0.35), a_out="RGB", b_out="RGB")
        nors[key] = b.tex(f"N_{key}", n, uv, normal=True) if n is not None else None

    order = (("terra", w_ter), ("lama", w_lam), ("concreto", w_con), ("asfalto", w_asf), ("rocha", w_roc))
    col = cols["grama"]
    nor = nors["grama"]
    for key, w in order:
        col = b.lerp(col, cols[key], w)
        if nor is not None and nors[key] is not None:
            nor = b.lerp(nor, nors[key], w, a_out="RGB" if nor is nors["grama"] else "", b_out="RGB")
    tint = b.node(unreal.MaterialExpressionVectorParameter, parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
    MEL.connect_material_property(b.op(unreal.MaterialExpressionMultiply, col, tint), "", MP.MP_BASE_COLOR)
    if nor is not None:
        MEL.connect_material_property(nor, "", MP.MP_NORMAL)
    rough = b.lerp(b.scalar("Roughness", 0.88), b.scalar("RoughnessLama", 0.25), w_lam)
    MEL.connect_material_property(rough, "", MP.MP_ROUGHNESS)
    glow = b.opc(unreal.MaterialExpressionMultiply, b.op(unreal.MaterialExpressionMultiply, cols["lama"], w_lam), 0.6)
    MEL.connect_material_property(glow, "", MP.MP_EMISSIVE_COLOR)
    # [A-098] grama só onde é grama, com margem: máscara crua em 13 pontos (centro, 4 a 50%, 4 a 100%, 4 diagonais)
    lgt_path = "/Game/Environment/Cidade/Grama/LGT_Cidade_Grama"
    if EAL.does_asset_exist(lgt_path):
        du = b.op(unreal.MaterialExpressionDivide, b.scalar("GrassMarginCm", 120.0), size)
        hard = None
        hard_w = b.node(unreal.MaterialExpressionConstant4Vector, constant=unreal.LinearColor(1, 1, 0, 1))  # R+G+A
        taps = ((0, 0), (0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5), (1, 0), (-1, 0), (0, 1), (0, -1),
                (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7))
        center = None
        for dx, dy in taps:
            if dx == 0 and dy == 0:
                uvt = muv
            else:
                off = b.op(unreal.MaterialExpressionMultiply,
                           b.node(unreal.MaterialExpressionConstant2Vector, r=float(dx), g=float(dy)), du)
                uvt = b.op(unreal.MaterialExpressionAdd, muv, off)
            tap = b.node(unreal.MaterialExpressionTextureSample, texture=mask_tex,
                         sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR, sampler_source=SHARED)
            b.link(uvt, "", tap, "UVs")
            if center is None:
                center = tap
            hi = b.op(unreal.MaterialExpressionDotProduct, tap, hard_w, a_out="RGBA")
            hard = hi if hard is None else b.op(unreal.MaterialExpressionMax, hard, hi)
        k_hard = b.one(unreal.MaterialExpressionSaturate, b.op(unreal.MaterialExpressionSubtract, b.node(unreal.MaterialExpressionConstant, r=1.0),
                                                              b.op(unreal.MaterialExpressionMultiply, hard, b.scalar("GrassHardK", 5.0))))
        dirt_c = b.mask(center, "b", "RGBA")
        k_dirt = b.one(unreal.MaterialExpressionSaturate, b.op(unreal.MaterialExpressionSubtract, b.node(unreal.MaterialExpressionConstant, r=1.0),
                                                              b.op(unreal.MaterialExpressionMultiply, dirt_c, b.scalar("GrassDirtK", 1.4))))
        k_rock = b.one(unreal.MaterialExpressionOneMinus, w_roc)
        grass_w = b.op(unreal.MaterialExpressionMultiply, b.op(unreal.MaterialExpressionMultiply, k_hard, k_dirt), k_rock)
        try:
            go = b.node(unreal.MaterialExpressionLandscapeGrassOutput)
            gi = unreal.GrassInput()
            gi.set_editor_property("name", "Grama")
            gi.set_editor_property("grass_type", EAL.load_asset(lgt_path))
            go.set_editor_property("grass_types", [gi])
            b.link(grass_w, "", go, "Grama")
            log("saída de grama ligada (LGT_Cidade_Grama)")
        except Exception as exc:  # noqa: BLE001
            warn(f"saída de grama: {exc}")
    else:
        warn("LGT_Cidade_Grama não existe: rode setup_grass.py antes (o chão sai sem grama)")
    MEL.recompile_material(b.m)
    EAL.save_loaded_asset(b.m)
    log("M_Cidade_Chao3 criado (grama com margem de rua/calçada)")
    return b.m


def find_landscape():
    ss = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in ss.get_all_level_actors():
        if isinstance(a, unreal.LandscapeProxy):
            return a
    return None


def main():
    land = find_landscape()
    if land is None:
        raise RuntimeError("não há Landscape no mapa aberto: importe o city_height.png primeiro (docs/design/CIDADE_V4.md)")
    mask_tex = import_mask()
    with open(LAYOUT_FILE, encoding="utf-8") as fh:
        layout0 = json.load(fh)
    mat = build_material(mask_tex, layout0)
    mi_path = f"{DIR}/MI_Cidade_Chao"
    mi = EAL.load_asset(mi_path) if EAL.does_asset_exist(mi_path) else TOOLS.create_asset(
        "MI_Cidade_Chao", DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, mat)
    loc = land.get_actor_location()
    scale = land.get_actor_scale3d()
    with open(LAYOUT_FILE, encoding="utf-8") as fh:
        layout = json.load(fh)
    size_cm = float(layout["landscape"]["size_m"]) * 100.0 * (scale.x / 100.0)
    MEL.set_material_instance_vector_parameter_value(mi, "MaskOrigin", unreal.LinearColor(loc.x, loc.y, 0, 0))
    MEL.set_material_instance_scalar_parameter_value(mi, "MaskSizeCm", size_cm)
    EAL.save_loaded_asset(mi)
    land.set_editor_property("landscape_material", mi)
    try:
        land.post_edit_change()
    except Exception:  # noqa: BLE001
        pass
    R["landscape"] = {"label": land.get_actor_label(), "loc": [loc.x, loc.y, loc.z], "scale": [scale.x, scale.y, scale.z], "size_cm": size_cm}
    if abs(scale.x - 100) > 0.5 or abs(scale.z - 100) > 0.5:
        warn(f"escala do Landscape {scale} (o esperado é 100, 100, 100): a cidade fica fora de medida")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log(f"MI_Cidade_Chao aplicado em {land.get_actor_label()} (origem {loc.x:.0f}, {loc.y:.0f}; {size_cm / 100:.0f} m)")
    # [A-098] confere o alinhamento máscara x Landscape (v5/v6: origem -25200, 504 m)
    exp_half = float(layout["landscape"]["size_m"]) * 50.0
    if abs(loc.x + exp_half) > 1 or abs(loc.y + exp_half) > 1:
        warn(f"Landscape fora da origem da planta ({loc.x:.0f}, {loc.y:.0f}; esperado {-exp_half:.0f}): rode fix_city_landscape.py")
    try:
        unreal.SystemLibrary.execute_console_command(None, "grass.FlushCache")
        log("grass.FlushCache (tufos refeitos com o material novo)")
    except Exception as exc:  # noqa: BLE001
        warn(f"grass.FlushCache: {exc}")


try:
    main()
except Exception as exc:  # noqa: BLE001
    R["errors"].append(str(exc))
    unreal.log_error(f"[city_land] {exc}\n{traceback.format_exc()[-1500:]}")
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_city_landscape.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[city_land] fim | avisos {len(R['warnings'])} | erros {len(R['errors'])}")
