"""[A-086] Materiais do pacote v3. Pode rodar de novo (recria do zero).

RODA NO EDITOR (caixa Cmd, sem Play):  py "E:/game/utrazin-game/tools/unreal/setup_v3_materials.py"
  /Game/Materials/Remap/M_Pickup_Beam   feixe de luz vertical dos itens no chão (aditivo, apaga para cima).
                                        Parâmetros: Color (o C++ põe a cor do item), Intensity.
O AJRPickup usa um cilindro da engine (100 cm, origem no centro) com este material; sem ele, o feixe não aparece.
"""
import unreal

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
DIR = "/Game/Materials/Remap"


def node(m, cls, x, y, **props):
    e = MEL.create_material_expression(m, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def link(a, a_out, b, b_in):
    if not MEL.connect_material_expressions(a, a_out, b, b_in):
        unreal.log_warning(f"[v3_mat] ligação {a.get_name()}.{a_out} -> {b.get_name()}.{b_in} falhou")


def beam():
    name = "M_Pickup_Beam"
    path = f"{DIR}/{name}"
    EAL.make_directory(DIR)
    if EAL.does_asset_exist(path):
        # [A-087] recriar um material em uso derruba a Unreal (assert !IsRooted): mantém o que existe
        unreal.log(f"[v3_mat] {path} já existe (apague no Content Browser para recriar)")
        return
    else:
        m = TOOLS.create_asset(name, DIR, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("two_sided", True)
    color = node(m, unreal.MaterialExpressionVectorParameter, -900, -200, parameter_name="Color",
                 default_value=unreal.LinearColor(0.4, 0.9, 1.0, 1.0))
    inten = node(m, unreal.MaterialExpressionScalarParameter, -900, -60, parameter_name="Intensity", default_value=3.5)
    # altura no cilindro: -50 (base) a +50 (topo) -> 0 a 1
    lp = node(m, unreal.MaterialExpressionLocalPosition, -1300, 150)
    z = node(m, unreal.MaterialExpressionComponentMask, -1100, 150, r=False, g=False, b=True, a=False)
    link(lp, "", z, "")
    t = node(m, unreal.MaterialExpressionMultiply, -950, 150, const_b=0.01)
    link(z, "", t, "A")
    t2 = node(m, unreal.MaterialExpressionAdd, -820, 150, const_b=0.5)
    link(t, "", t2, "A")
    sat = node(m, unreal.MaterialExpressionSaturate, -700, 150)
    link(t2, "", sat, "")
    inv = node(m, unreal.MaterialExpressionOneMinus, -580, 150)
    link(sat, "", inv, "")
    fade = node(m, unreal.MaterialExpressionPower, -460, 150, const_exponent=2.2)
    link(inv, "", fade, "Base")
    # miolo mais forte, borda suave (não parece um tubo sólido)
    fres = node(m, unreal.MaterialExpressionFresnel, -700, 320, exponent=1.2, base_reflect_fraction=0.0)
    core = node(m, unreal.MaterialExpressionOneMinus, -580, 320)
    link(fres, "", core, "")
    a = node(m, unreal.MaterialExpressionMultiply, -500, -150)
    link(color, "", a, "A")
    link(inten, "", a, "B")
    b = node(m, unreal.MaterialExpressionMultiply, -350, 0)
    link(a, "", b, "A")
    link(fade, "", b, "B")
    c = node(m, unreal.MaterialExpressionMultiply, -220, 100)
    link(b, "", c, "A")
    link(core, "", c, "B")
    MEL.connect_material_property(c, "", MP.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    unreal.log(f"[v3_mat] {path} pronto")


beam()
