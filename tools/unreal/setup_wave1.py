"""Retrabalho "Vale Alienígena" (onda 1): texturas, materiais, armas, animações novas, nitro, carro novo, elite.

RODA NO EDITOR (caixa Cmd), depois de compilar o C++ novo:
  py "E:/game/utrazin-game/tools/unreal/setup_wave1.py"
(ou rode tudo de uma vez com tools/unreal/run_all_wave1.py)

Faz (cada parte é independente: se uma falhar, as outras continuam; ver reports/setup_wave1.json):
 1. Texturas  assets/work/textures/*.png  -> /Game/Environment/Textures   (normais em modo NormalMap)
 2. Ícones    assets/work/ui/T_UI_*.png   -> /Game/UI/HUD                 (sem mipmap, grupo UI)
 3. Materiais M_L01_Terrain (biomas pela cor do vértice + rocha pela inclinação), M_L01_Road, M_L01_Glow,
              M_L01_Toxic, M_L01_VertexColor (props, agora com sujeira), M_Zombie + 4 instâncias,
              pistola com a textura dela (antes ficava "sem cor")
 4. Graveto   assets/work/weapons/SM_AlienStick.fbx -> /Game/Weapons/SM_AlienStick
 5. Animações novas (pegar do chão, 2 golpes, abrir baú) -> retarget para Enzo e Victoria (pasta Anims/Wave1)
 6. BPs dos heróis: golpes, pegar, baú, pistola/escopeta, graveto na mão, começa SEM arma
 7. DA_Weapon_AlienShotgun (7 projéteis), DA_Enemy_ZombieElite + BP_Enemy_ZombieElite (deixa a escopeta)
 8. Nitro: IA_Nitro (Shift esquerdo / gatilho esquerdo) no IMC do carro + BP do carro
 9. Carro: chassi novo SM_Car_AlienBuggy no BP_Vehicle_SUV (escala ajustada ao chassi antigo)
Pode rodar de novo.
"""
import json
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MEL = unreal.MaterialEditingLibrary
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "info": {}}
TEX = "/Game/Environment/Textures"
MATS = "/Game/Environment/L01/Materials"
HEROES = ("01", "02")
NEW_ANIMS = ("PickUp_Gun", "Melee_Slash_Out", "Melee_Slash_In", "Open_Chest")
VEHICLE_BP = "/Game/Vehicles/SUV/BP_Vehicle_SUV"


def log(m):
    R["steps"].append(m)
    unreal.log(f"[wave1] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[wave1] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-1200:]})
    unreal.log_error(f"[wave1] {where}: {exc}")


def save(a):
    EAL.save_loaded_asset(a, only_if_is_dirty=False)


def step(fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        err(fn.__name__, exc)


def setp(obj, k, v, where=""):
    try:
        obj.set_editor_property(k, v)
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"{where}.{k}: {exc}")
        return False


def cdo_of(bp_path):
    bp = EAL.load_asset(bp_path)
    return bp, unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))


def compile_save(bp):
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)


# ------------------------------------------------------------------ 1/2. texturas
def import_png(path, folder, kind):
    name = os.path.splitext(os.path.basename(path))[0]
    task = unreal.AssetImportTask()
    task.filename = path
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    TOOLS.import_asset_tasks([task])
    t = EAL.load_asset(f"{folder}/{name}")
    if t is None:
        raise RuntimeError(f"textura não importada: {path}")
    if kind == "normal":
        setp(t, "compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP, name)
        setp(t, "srgb", False, name)
        setp(t, "flip_green_channel", False, name)  # já está no padrão DirectX (o da Unreal)
    elif kind == "mask":
        setp(t, "srgb", False, name)
        setp(t, "compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE, name)
    elif kind == "ui":
        setp(t, "compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON, name)
        setp(t, "mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS, name)
        setp(t, "lod_group", unreal.TextureGroup.TEXTUREGROUP_UI, name)
        setp(t, "never_stream", True, name)
    save(t)
    return t


def textures():
    src = os.path.join(REPO, "assets", "work", "textures")
    n = 0
    for f in sorted(os.listdir(src)):
        if not f.lower().endswith(".png") or "preview" in f:
            continue
        kind = "normal" if f.endswith("_N.png") else ("mask" if f.startswith(("T_Detail", "T_Emissive")) else "color")
        import_png(os.path.join(src, f), TEX, kind)
        n += 1
    log(f"{n} texturas importadas em {TEX}")
    pistol_png = os.path.join(REPO, "assets", "work", "weapons", "SM_AlienPistol.fbm", "T_AlienPistol_BaseColor.png")
    if os.path.exists(pistol_png):
        import_png(pistol_png, "/Game/Weapons", "color")
        log("textura da pistola importada")


def ui_textures():
    src = os.path.join(REPO, "assets", "work", "ui")
    n = 0
    for f in sorted(os.listdir(src)):
        if f.startswith("T_UI_") and f.endswith(".png"):
            import_png(os.path.join(src, f), "/Game/UI/HUD", "ui")
            n += 1
    log(f"{n} ícones do HUD importados")


# ------------------------------------------------------------------ 3. materiais
class MB:
    """Ajudante para montar materiais por nós (MaterialEditingLibrary)."""

    def __init__(self, path):
        folder, name = path.rsplit("/", 1)
        EAL.make_directory(folder)
        if EAL.does_asset_exist(path):
            self.m = EAL.load_asset(path)
            MEL.delete_all_material_expressions(self.m)
        else:
            self.m = TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
        self.x = -1800
        self.y = 0

    def node(self, cls, **props):
        e = MEL.create_material_expression(self.m, cls, self.x, self.y)
        self.y += 140
        if self.y > 2600:
            self.y = 0
            self.x += 260
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def link(self, a, a_out, b, b_in):
        if not MEL.connect_material_expressions(a, a_out, b, b_in):
            warn(f"{self.m.get_name()}: ligação {a.get_name()}.{a_out} -> {b.get_name()}.{b_in} falhou")

    def out(self, e, prop, e_out=""):
        MEL.connect_material_property(e, e_out, prop)

    def const(self, v):
        return self.node(unreal.MaterialExpressionConstant, r=float(v))

    def tex(self, name, uv=None, normal=False):
        t = EAL.load_asset(f"{TEX}/{name}") if "/" not in name else EAL.load_asset(name)
        if t is None:
            raise RuntimeError(f"textura ausente: {name}")
        e = self.node(unreal.MaterialExpressionTextureSample, texture=t)
        st = unreal.MaterialSamplerType
        if normal:
            e.set_editor_property("sampler_type", st.SAMPLERTYPE_NORMAL)
        elif name.startswith(("T_Detail", "T_Emissive")):
            e.set_editor_property("sampler_type", st.SAMPLERTYPE_LINEAR_GRAYSCALE)
        if uv is not None:
            self.link(uv, "", e, "UVs")
        return e

    def mul(self, a, b=None, cb=None, a_out="", b_out=""):
        e = self.node(unreal.MaterialExpressionMultiply)
        self.link(a, a_out, e, "A")
        if b is not None:
            self.link(b, b_out, e, "B")
        else:
            e.set_editor_property("const_b", float(cb))
        return e

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

    def world_uv(self, tile_cm, xy=True):
        wp = self.node(unreal.MaterialExpressionWorldPosition)
        mask = self.node(unreal.MaterialExpressionComponentMask, r=True, g=True, b=False, a=False)
        self.link(wp, "", mask, "")
        d = self.node(unreal.MaterialExpressionDivide, const_b=float(tile_cm))
        self.link(mask, "", d, "A")
        return d

    def finish(self):
        MEL.recompile_material(self.m)
        save(self.m)
        log(f"material {self.m.get_name()} pronto")
        return self.m


MP = unreal.MaterialProperty


def mat_terrain():
    """[A-066] Duas escalas + rocha projetada de lado (item 16). Fonte única: fix_l01_materiais.build_terrain."""
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.append(here)
    import fix_l01_materiais as FM  # noqa: E402
    FM.build_terrain(log=log, warn=warn)


def mat_road():
    b = MB(f"{MATS}/M_L01_Road")
    uv = b.world_uv(300.0)
    vc = b.node(unreal.MaterialExpressionVertexColor)
    b.out(b.mul(b.tex("T_Gravel_D", uv), vc), MP.MP_BASE_COLOR)
    b.out(b.tex("T_Gravel_N", uv, normal=True), MP.MP_NORMAL)
    b.out(b.const(0.85), MP.MP_ROUGHNESS)
    b.finish()


def mat_props():
    b = MB(f"{MATS}/M_L01_VertexColor")
    vc = b.node(unreal.MaterialExpressionVertexColor)
    g = b.tex("T_Detail_Grunge", b.world_uv(180.0))
    var = b.lerp(None, None, g, ca=0.68, cb=1.12)
    b.out(b.mul(vc, var), MP.MP_BASE_COLOR)
    b.out(b.const(0.85), MP.MP_ROUGHNESS)
    b.finish()


def mat_glow():
    b = MB(f"{MATS}/M_L01_Glow")
    vc = b.node(unreal.MaterialExpressionVertexColor)
    b.out(vc, MP.MP_BASE_COLOR)
    # [A-063] era 6 (estourava com a exposição fixa do céu; print_08). Parâmetro para ajustar sem refazer.
    glow = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="GlowStrength", default_value=1.5)
    b.out(b.mul(vc, glow), MP.MP_EMISSIVE_COLOR)
    b.out(b.const(0.4), MP.MP_ROUGHNESS)
    b.finish()


def mat_toxic():
    b = MB(f"{MATS}/M_L01_Toxic")
    pan = b.node(unreal.MaterialExpressionPanner, speed_x=0.02, speed_y=0.035)
    b.link(b.world_uv(500.0), "", pan, "Coordinate")
    d = b.tex("T_Toxic_D", pan)
    b.out(d, MP.MP_BASE_COLOR)
    b.out(b.mul(d, cb=1.6), MP.MP_EMISSIVE_COLOR)
    b.out(b.tex("T_Toxic_N", pan, normal=True), MP.MP_NORMAL)
    b.out(b.const(0.15), MP.MP_ROUGHNESS)
    b.finish()


def mat_zombie():
    b = MB("/Game/Enemies/Materials/M_Zombie")
    tc = b.node(unreal.MaterialExpressionTextureCoordinate, u_tiling=2.0, v_tiling=2.0)
    tint = b.node(unreal.MaterialExpressionVectorParameter, parameter_name="Tint",
                  default_value=unreal.LinearColor(0.8, 0.95, 0.85, 1))
    glow = b.node(unreal.MaterialExpressionVectorParameter, parameter_name="GlowColor",
                  default_value=unreal.LinearColor(0.1, 1.0, 0.85, 1))
    power = b.node(unreal.MaterialExpressionScalarParameter, parameter_name="GlowStrength", default_value=4.0)
    b.out(b.mul(b.tex("T_ZombieAlien_D", tc), tint), MP.MP_BASE_COLOR)
    b.out(b.tex("T_ZombieAlien_N", tc, normal=True), MP.MP_NORMAL)
    veins = b.tex("T_Emissive_Mask_Veins", tc)
    b.out(b.mul(b.mul(veins, glow), power), MP.MP_EMISSIVE_COLOR)
    b.out(b.const(0.7), MP.MP_ROUGHNESS)
    m = b.finish()
    for name, t, g, s in (("Melee", (0.75, 0.95, 0.8), (0.1, 1.0, 0.8), 4.0),
                          ("Archer", (0.85, 0.8, 1.0), (0.7, 0.25, 1.0), 5.0),
                          ("Gunner", (1.0, 0.85, 0.7), (1.0, 0.5, 0.1), 5.0),
                          ("Elite", (0.55, 0.5, 0.5), (1.0, 0.1, 0.05), 8.0)):
        path = f"/Game/Enemies/Materials/MI_Zombie_{name}"
        mi = EAL.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
            f"MI_Zombie_{name}", "/Game/Enemies/Materials", unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, m)
        MEL.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(*t, 1))
        MEL.set_material_instance_vector_parameter_value(mi, "GlowColor", unreal.LinearColor(*g, 1))
        MEL.set_material_instance_scalar_parameter_value(mi, "GlowStrength", s)
        save(mi)
    log("instâncias MI_Zombie_* prontas")


def mat_pistol():
    """[A-066] M_Pistol_* vêm do FBX como MaterialInstanceConstant: o MB() antigo falhava (reports/setup_wave1.json,
    "Cannot nativize 'MaterialInstanceConstant' as 'Material'") e a pistola ficava sem cor (item 17).
    Fonte única: fix_l01_materiais.build_pistol (mestre com a textura + instâncias + slots da malha)."""
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.append(here)
    import fix_l01_materiais as FM  # noqa: E402
    FM.build_pistol(log=log, warn=warn)


def materials():
    for f in (mat_terrain, mat_road, mat_props, mat_glow, mat_toxic, mat_zombie, mat_pistol):
        step(f)


def zombie_skins():
    """Aplica as instâncias nos zumbis atuais (malha Manny). Se setup_zombie_skin.py trocar a malha, ele refaz."""
    for kind in ("Melee", "Archer", "Gunner"):
        bp_path = f"/Game/Enemies/BP_Enemy_Zombie{kind}"
        if not EAL.does_asset_exist(bp_path):
            continue
        bp, cdo = cdo_of(bp_path)
        mesh = cdo.get_editor_property("mesh")
        skm = mesh.get_editor_property("skeletal_mesh_asset") if hasattr(mesh, "get_editor_property") else None
        n = len(skm.get_editor_property("materials")) if skm else 2
        mi = EAL.load_asset(f"/Game/Enemies/Materials/MI_Zombie_{kind}")
        mesh.set_editor_property("override_materials", [mi] * n)
        compile_save(bp)
        log(f"BP_Enemy_Zombie{kind}: pele alienígena ({n} slots)")


# ------------------------------------------------------------------ 4. graveto
def import_static(fbx, folder, name):
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    o = unreal.FbxImportUI()
    o.import_mesh = True
    o.import_as_skeletal = False
    o.import_animations = False
    o.import_materials = False
    o.import_textures = False
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    d = o.static_mesh_import_data
    for k, v in (("combine_meshes", True), ("auto_generate_collision", True), ("generate_lightmap_u_vs", False),
                 ("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)):
        setp(d, k, v, name)
    task.options = o
    TOOLS.import_asset_tasks([task])
    sm = EAL.load_asset(f"{folder}/{name}")
    if sm is None:
        raise RuntimeError(f"não importou {fbx}: {list(task.imported_object_paths)}")
    return sm


def assign_slots(sm):
    glow = EAL.load_asset(f"{MATS}/M_L01_Glow")
    base = EAL.load_asset(f"{MATS}/M_L01_VertexColor")
    mats = sm.get_editor_property("static_materials")
    for i, s in enumerate(mats):
        slot = str(s.get_editor_property("material_slot_name"))
        sm.set_material(i, glow if "Glow" in slot else base)
    save(sm)


def stick():
    sm = import_static(os.path.join(REPO, "assets", "work", "weapons", "SM_AlienStick.fbx"), "/Game/Weapons", "SM_AlienStick")
    assign_slots(sm)
    log("SM_AlienStick importado")


# ------------------------------------------------------------------ 5. animações novas
def import_anim(fbx, skeleton):
    name = "A_" + os.path.splitext(os.path.basename(fbx))[0]
    folder = "/Game/Characters/Mixamo/Anims/hero"
    target = f"{folder}/{name}"
    if EAL.does_asset_exist(target):
        return target
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    o = unreal.FbxImportUI()
    o.import_mesh = False
    o.import_as_skeletal = True
    o.import_animations = True
    o.import_materials = False
    o.import_textures = False
    o.skeleton = skeleton
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
    task.options = o
    TOOLS.import_asset_tasks([task])
    if not EAL.does_asset_exist(target):
        for p in task.imported_object_paths:
            a = EAL.load_asset(p.split(".")[0])
            if isinstance(a, unreal.AnimSequence):
                EAL.rename_asset(p.split(".")[0], target)
                break
    if not EAL.does_asset_exist(target):
        raise RuntimeError(f"animação não importada: {fbx}")
    return target


def anims():
    xbot = EAL.load_asset("/Game/Characters/Mixamo/SK_XBot")
    raw = os.path.join(REPO, "assets", "raw", "mixamo", "hero")
    srcs = [import_anim(os.path.join(raw, f"{n}.fbx"), xbot.skeleton) for n in NEW_ANIMS]
    for nn in HEROES:
        folder = f"/Game/Characters/Hero{nn}/Anims/Wave1"
        # a Unreal NÃO sobrescreve: retarget só do que falta (rodar de novo não cria cópias renomeadas)
        missing = [s for s in srcs if not EAL.does_asset_exist(f"{folder}/{s.split('/')[-1]}_H{nn}")]
        if not missing:
            log(f"Hero{nn}: animações novas já existem")
            continue
        EAL.make_directory(folder)
        mesh = EAL.load_asset(f"/Game/Characters/Hero{nn}/Mesh/SK_Hero{nn}")
        rtg = EAL.load_asset(f"/Game/Characters/Rigs/RTG_Mixamo_Hero{nn}")
        out = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
            [EAL.find_asset_data(p) for p in missing], xbot, mesh, rtg, search="", replace="", prefix="",
            suffix=f"_H{nn}", target_path=folder, use_source_path=False, include_referenced_assets=False,
            overwrite_existing_files=True)
        for a in out:
            p = str(getattr(a, "package_name", "") or "")
            if p and EAL.does_asset_exist(p):
                save(EAL.load_asset(p))
        log(f"Hero{nn}: {len(out)} animações novas em {folder}")


# ------------------------------------------------------------------ 6. heróis
def weapons_data():
    pistol = "/Game/Data/DA_Weapon_AlienPistol"
    sg = "/Game/Data/DA_Weapon_AlienShotgun"
    if not EAL.does_asset_exist(sg):
        EAL.duplicate_asset(pistol, sg)
    a = EAL.load_asset(sg)
    for k, v in (("weapon_id", "WPN-002"), ("display_name", "Escopeta Alien"), ("damage", 14.0), ("fire_rate", 1.3),
                 ("magazine_size", 5), ("starting_reserve", 15), ("reload_time", 2.1), ("range", 2500.0),
                 ("spread_half_angle_degrees", 1.0), ("pellet_count", 7), ("pellet_spread_degrees", 6.0)):
        setp(a, k, v, "DA_Weapon_AlienShotgun")
    save(a)
    log("DA_Weapon_AlienShotgun pronto (7 projéteis, 5 no pente)")


def heroes():
    for nn in HEROES:
        bp, cdo = cdo_of(f"/Game/Characters/Hero{nn}/BP_Character_Hero{nn}")
        f = f"/Game/Characters/Hero{nn}/Anims/Wave1"

        def A(n):
            p = f"{f}/A_{n}_H{nn}"
            if not EAL.does_asset_exist(p):
                warn(f"Hero{nn}: falta {p}")
                return None
            return EAL.load_asset(p)
        melee = [x for x in (A("Melee_Slash_Out"), A("Melee_Slash_In")) if x]
        where = f"Hero{nn}"
        if melee:
            setp(cdo, "melee_anims", melee, where)
        if A("PickUp_Gun"):
            setp(cdo, "pickup_anim", A("PickUp_Gun"), where)
        if A("Open_Chest"):
            setp(cdo, "open_chest_anim", A("Open_Chest"), where)
        setp(cdo, "pistol_definition", EAL.load_asset("/Game/Data/DA_Weapon_AlienPistol"), where)
        setp(cdo, "shotgun_definition", EAL.load_asset("/Game/Data/DA_Weapon_AlienShotgun"), where)
        gun = EAL.load_asset("/Game/Weapons/SM_AlienPistol")
        setp(cdo, "pistol_static_mesh", gun, where)
        setp(cdo, "shotgun_static_mesh", gun, where)  # sem malha própria ainda: pistola 1,35x maior
        setp(cdo, "start_with_weapon_equipped", False, where)
        try:
            wm = cdo.get_editor_property("weapon_mesh")
            mm = cdo.get_editor_property("melee_mesh")
            mm.set_editor_property("static_mesh", EAL.load_asset("/Game/Weapons/SM_AlienStick"))
            # mesma pegada da pistola, com a lâmina inclinada 65° para cima
            pist = unreal.Transform(wm.get_editor_property("relative_location"), wm.get_editor_property("relative_rotation"),
                                    unreal.Vector(1, 1, 1))
            tilt = unreal.Transform(unreal.Vector(0, 0, 0), unreal.Rotator(0, 65, 0), unreal.Vector(1, 1, 1))
            rel = unreal.MathLibrary.compose_transforms(tilt, pist)
            mm.set_editor_property("relative_location", rel.translation)
            mm.set_editor_property("relative_rotation", rel.rotation.rotator())
            R["info"][f"stick_grip_H{nn}"] = {"loc": str(rel.translation), "rot": str(rel.rotation.rotator())}
        except Exception as exc:  # noqa: BLE001
            err(f"Hero{nn}.melee_mesh", exc)
        compile_save(bp)
        log(f"Hero{nn}: golpes, pegar, baú, armas e graveto configurados (começa desarmado)")


# ------------------------------------------------------------------ 7. elite
def elite():
    da_src, da = "/Game/Data/DA_Enemy_ZombieMelee", "/Game/Data/DA_Enemy_ZombieElite"
    if not EAL.does_asset_exist(da):
        EAL.duplicate_asset(da_src, da)
    d = EAL.load_asset(da)
    for k, v in (("archetype_id", "ENM-010"), ("max_health", 450.0), ("move_speed", 300.0), ("attack_range", 210.0),
                 ("attack_damage", 30.0), ("attack_interval", 1.6), ("aggro_radius", 3000.0)):
        setp(d, k, v, "DA_Enemy_ZombieElite")
    save(d)
    bp_src, bp_path = "/Game/Enemies/BP_Enemy_ZombieMelee", "/Game/Enemies/BP_Enemy_ZombieElite"
    if not EAL.does_asset_exist(bp_path):
        EAL.duplicate_asset(bp_src, bp_path)
    bp, cdo = cdo_of(bp_path)
    setp(cdo, "archetype", d, "Elite")
    setp(cdo, "has_guaranteed_drop", True, "Elite")
    setp(cdo, "guaranteed_drop", unreal.JRPickupType.WEAPON_SHOTGUN, "Elite")
    setp(cdo, "guaranteed_drop_mesh", EAL.load_asset("/Game/Weapons/SM_AlienPistol"), "Elite")
    try:
        cdo.get_editor_property("capsule_component").set_editor_property("relative_scale3d", unreal.Vector(1.5, 1.5, 1.5))
    except Exception as exc:  # noqa: BLE001
        warn(f"Elite escala: {exc}")
    try:
        mesh = cdo.get_editor_property("mesh")
        mi = EAL.load_asset("/Game/Enemies/Materials/MI_Zombie_Elite")
        n = len(mesh.get_editor_property("override_materials")) or 2
        mesh.set_editor_property("override_materials", [mi] * n)
    except Exception as exc:  # noqa: BLE001
        warn(f"Elite material: {exc}")
    compile_save(bp)
    log("BP_Enemy_ZombieElite pronto (1,5x, 450 de vida, deixa a escopeta)")


# ------------------------------------------------------------------ 8. nitro
def nitro():
    path = "/Game/Core/Input/IA_Nitro"
    if EAL.does_asset_exist(path):
        ia = EAL.load_asset(path)
    else:
        fc = getattr(unreal, "InputAction_Factory", None)
        ia = TOOLS.create_asset("IA_Nitro", "/Game/Core/Input", unreal.InputAction, fc() if fc else None)
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
        save(ia)
    bp, cdo = cdo_of(VEHICLE_BP)
    setp(cdo, "nitro_action", ia, "Vehicle")
    # IMC que o carro usa: o primeiro de BP_PlayerController.vehicle_mapping_contexts
    imc = None
    try:
        _, pc = cdo_of("/Game/Core/BP_PlayerController")
        lst = list(pc.get_editor_property("vehicle_mapping_contexts"))
        imc = lst[0] if lst else None
    except Exception as exc:  # noqa: BLE001
        warn(f"vehicle_mapping_contexts: {exc}")
    if imc is None:
        imc = EAL.load_asset("/Game/VehicleTemplate/Input/IMC_Vehicle_Default")
    already = []
    try:
        already = [m.get_editor_property("action").get_name() for m in imc.get_editor_property("mappings")
                   if m.get_editor_property("action")]
    except Exception as exc:  # noqa: BLE001
        warn(f"lendo teclas do {imc.get_name()}: {exc}")
    if "IA_Nitro" not in already:
        for key in ("LeftShift", "Gamepad_LeftTrigger"):
            k = unreal.Key()
            try:
                k.set_editor_property("key_name", key)
            except Exception:  # noqa: BLE001
                k.import_text(key)
            imc.map_key(ia, k)
        save(imc)
    compile_save(bp)
    R["info"]["vehicle_imc"] = imc.get_path_name()
    log(f"nitro: IA_Nitro em {imc.get_name()} (Shift esquerdo)")


# ------------------------------------------------------------------ 9. carro
def car():
    fbx = os.path.join(REPO, "assets", "work", "vehicles", "SM_Car_AlienBuggy.fbx")
    sm = import_static(fbx, "/Game/Vehicles/AlienBuggy", "SM_Car_AlienBuggy")
    assign_slots(sm)
    bp, cdo = cdo_of(VEHICLE_BP)
    ch = cdo.get_editor_property("chassis_mesh")
    old = ch.get_editor_property("static_mesh")
    scale = 1.0
    if old and old.get_name() != "SM_Car_AlienBuggy":
        ob = old.get_bounds().box_extent
        nb = sm.get_bounds().box_extent
        scale = round(float(ob.x / max(nb.x, 1.0)), 3)
        R["info"]["chassis_old"] = {"mesh": old.get_path_name(), "extent": str(ob)}
        R["info"]["chassis_new_extent"] = str(nb)
    ch.set_editor_property("static_mesh", sm)
    ch.set_editor_property("relative_scale3d", unreal.Vector(scale, scale, scale))
    compile_save(bp)
    R["info"]["chassis_scale"] = scale
    log(f"carro: chassi SM_Car_AlienBuggy (escala {scale})")


def main():
    for f in (textures, ui_textures, materials, zombie_skins, stick, anims, weapons_data, heroes, elite, nitro, car):
        step(f)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception as exc:  # noqa: BLE001
        err("save", exc)
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_wave1.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[wave1] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
