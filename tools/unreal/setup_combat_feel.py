"""Sensação de combate (A-057): materiais de efeito, sons de plasma, valores das armas e câmera. Pode rodar de novo.

RODA NO EDITOR (caixa Cmd, sem Play), DEPOIS de compilar o C++ novo (FX/JRFXSubsystem, FX/JRDamageFXComponent,
campos novos em UJRWeaponDefinition e AJRCharacter):
  py "E:/game/utrazin-game/tools/unreal/setup_combat_feel.py"
Depois rode setup_anims_wave2.py e fix_weapon_grips.py (eles preenchem as propriedades novas de animação/encaixe).

O que faz (cada parte independente; ver reports/setup_combat_feel.json):
 1. Texturas das decals (assets/work/vfx/textures: T_FX_BloodSplat, T_FX_Scorch) -> /Game/VFX/Textures.
 2. Materiais em /Game/VFX/Materials (nomes fixos lidos pelo C++):
      M_FX_Plasma       translúcido aditivo, sem luz: Color, Intensity, Opacity; núcleo branco e borda suave (fresnel)
      M_FX_HitFlash     aditivo de borda (fresnel) para o flash no corpo (overlay em malha esquelética)
      M_FX_Blood        opaco brilhante (gotas e manchas presas no corpo): Color, Emissive
      M_FX_BloodDecal   decal translúcido com a máscara T_FX_BloodSplat: Color, Emissive (+ fade de vida)
      M_FX_ScorchDecal  decal de queimado do plasma com centro brilhando na cor da arma
    e instâncias de referência MI_FX_Blood_Red/Blue e MI_FX_BloodDecal_Red/Blue (as cores valem no C++).
 3. Sons (assets/work/audio/weapons/*.wav, sintetizados por tools/pipeline/gen_weapon_sfx.py) -> /Game/Audio/SFX/Weapons
    + atenuação ATT_JR_Weapons (some a ~60 m).
 4. DA_Weapon_AlienPistol e DA_Weapon_AlienShotgun: coice, plasma (cor da arma), sons.
 5. BP_Character_Hero01/02: câmera mais perto (300), FOV 90 / mira 70 / correr +5 e ArmedIdleAnim se achar uma.
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
TEX_DIR = "/Game/VFX/Textures"
MAT_DIR = "/Game/VFX/Materials"
SFX_DIR = "/Game/Audio/SFX/Weapons"
HEROES = ("01", "02")
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "info": {}, "cpp_needed": []}

# Cores (linear) conferidas nas texturas das armas: pistola violeta (T_AlienPistol_BaseColor ~ #9A1CBB),
# escopeta laranja (T_ARM_Escopeta_D ~ #BC4E1C, núcleo amarelo).
PISTOL_COLOR = (0.55, 0.12, 1.0)
SHOTGUN_COLOR = (1.0, 0.35, 0.04)
HUMAN_BLOOD = (0.32, 0.01, 0.01)
ZOMBIE_BLOOD = (0.02, 0.45, 1.0)

WEAPONS = {
    "/Game/Data/DA_Weapon_AlienPistol": {
        "recoil_pitch": 1.0, "recoil_yaw": 0.3, "recoil_recovery": 10.0, "recoil_keep_fraction": 0.2,
        "kick_back": 2.5, "kick_pitch": 6.0, "kick_recovery": 16.0, "shake_scale": 0.12, "crosshair_bloom": 0.3,
        "follow_up_delay": 0.0,
        "plasma_color": PISTOL_COLOR, "plasma_intensity": 25.0, "bolt_speed": 12000.0, "bolt_length": 70.0,
        "bolt_width": 6.0, "trail_length": 400.0, "muzzle_flash_scale": 1.0, "impact_scale": 1.0,
        "fire_volume": 0.9, "pitch_variance": 0.06,
        "sounds": {"fire_sound": "SFX_Plasma_Pistol_Fire", "reload_sound": "SFX_Plasma_Reload_Pistol",
                   "impact_sound": "SFX_Plasma_Impact", "dry_fire_sound": "SFX_Plasma_DryFire"},
    },
    "/Game/Data/DA_Weapon_AlienShotgun": {
        "recoil_pitch": 4.5, "recoil_yaw": 1.2, "recoil_recovery": 6.0, "recoil_keep_fraction": 0.3,
        "kick_back": 8.0, "kick_pitch": 16.0, "kick_recovery": 9.0, "shake_scale": 0.45, "crosshair_bloom": 0.8,
        "follow_up_delay": 0.38,
        "plasma_color": SHOTGUN_COLOR, "plasma_intensity": 30.0, "bolt_speed": 9000.0, "bolt_length": 45.0,
        "bolt_width": 5.0, "trail_length": 250.0, "muzzle_flash_scale": 1.8, "impact_scale": 0.8,
        "fire_volume": 1.0, "pitch_variance": 0.05,
        "sounds": {"fire_sound": "SFX_Plasma_Shotgun_Fire", "reload_sound": "SFX_Plasma_Reload_Shotgun",
                   "impact_sound": "SFX_Plasma_Impact", "dry_fire_sound": "SFX_Plasma_DryFire",
                   "follow_up_sound": "SFX_Plasma_Shotgun_Pump"},
    },
}

# Candidatos a ArmedIdleAnim (pose baixa segurando a arma). Nenhum vem do template/Mixamo atual:
# baixe no mixamo.com (ver relatório) e importe; o script liga o primeiro que existir.
ARMED_IDLE_NAMES = ("A_Pistol_Idle_Low", "A_Armed_Idle", "A_Pistol_Idle_Down", "A_Pistol_LowReady", "A_Gun_Idle_Low")


def log(m):
    R["steps"].append(m)
    unreal.log(f"[setup_combat_feel] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[setup_combat_feel] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-900:]})
    unreal.log_error(f"[setup_combat_feel] {where}: {exc}")


def save(asset):
    EAL.save_loaded_asset(asset, only_if_is_dirty=False)


def setp(obj, prop, value, where):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception:  # noqa: BLE001
        R["cpp_needed"].append(f"{where}.{prop}")
        warn(f"{where}: propriedade {prop} não existe (compilou o C++ novo?)")
        return False


def lc(rgb, a=1.0):
    return unreal.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), float(a))


# ------------------------------------------------------------------ 1. texturas

def import_file(path, folder, name):
    task = unreal.AssetImportTask()
    task.filename = path
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    TOOLS.import_asset_tasks([task])
    asset = EAL.load_asset(f"{folder}/{name}")
    if asset is None:
        raise RuntimeError(f"não importou {path}")
    return asset


def textures():
    src = os.path.join(REPO, "assets", "work", "vfx", "textures")
    EAL.make_directory(TEX_DIR)
    for name in ("T_FX_BloodSplat", "T_FX_Scorch"):
        f = os.path.join(src, name + ".png")
        if not os.path.exists(f):
            warn(f"falta {f} (rode tools/pipeline/gen_fx_textures.py)")
            continue
        tex = import_file(f, TEX_DIR, name)
        tex.set_editor_property("srgb", False)  # máscara (valor linear)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
        save(tex)
        log(f"textura {name}")


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
        self.x, self.y = -1400, -200

    def node(self, cls, **props):
        e = MEL.create_material_expression(self.m, cls, self.x, self.y)
        self.y += 130
        if self.y > 1400:
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

    def const(self, v):
        return self.node(unreal.MaterialExpressionConstant, r=float(v))

    def color(self, rgb):
        return self.node(unreal.MaterialExpressionConstant3Vector, constant=lc(rgb))

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

    def power(self, a, exp):
        e = self.node(unreal.MaterialExpressionPower, const_exponent=float(exp))
        self.link(a, "", e, "Base")
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

    def fresnel(self, exponent):
        return self.node(unreal.MaterialExpressionFresnel, exponent=float(exponent), base_reflect_fraction=0.0)

    def tex(self, name):
        t = EAL.load_asset(f"{TEX_DIR}/{name}")
        if t is None:
            raise RuntimeError(f"textura ausente: {TEX_DIR}/{name}")
        e = self.node(unreal.MaterialExpressionTextureSample, texture=t)
        e.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        return e

    def finish(self):
        MEL.recompile_material(self.m)
        save(self.m)
        log(f"material {self.m.get_name()}")
        return self.m


def mat_plasma():
    b = MB("M_FX_Plasma")
    b.m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    b.m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    color = b.vparam("Color", PISTOL_COLOR)
    inten = b.sparam("Intensity", 25.0)
    opac = b.sparam("Opacity", 1.0)
    core = b.one_minus(b.fresnel(2.0))         # 1 no meio da esfera, 0 na borda
    soft = b.power(core, 1.5)                  # borda suave
    hot = b.mul(b.power(core, 6.0), cb=0.65)   # núcleo quase branco
    tint = b.lerp(color, b.color((1, 1, 1)), hot)
    e = b.mul(b.mul(b.mul(tint, inten), opac), soft)
    b.out(e, MP.MP_EMISSIVE_COLOR)
    return b.finish()


def mat_hitflash():
    b = MB("M_FX_HitFlash")
    b.m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    b.m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    setp(b.m, "used_with_skeletal_mesh", True, "M_FX_HitFlash")
    color = b.vparam("Color", (0.6, 0.9, 1.0))
    inten = b.sparam("Intensity", 4.0)
    rim = b.add(b.fresnel(2.0), cb=0.25)
    b.out(b.mul(b.mul(color, inten), rim), MP.MP_EMISSIVE_COLOR)
    return b.finish()


def mat_blood():
    b = MB("M_FX_Blood")
    color = b.vparam("Color", HUMAN_BLOOD)
    emis = b.sparam("Emissive", 0.0)
    b.out(color, MP.MP_BASE_COLOR)
    b.out(b.const(0.22), MP.MP_ROUGHNESS)
    b.out(b.const(0.6), MP.MP_SPECULAR)
    b.out(b.mul(color, emis), MP.MP_EMISSIVE_COLOR)
    return b.finish()


def decal_base(b):
    b.m.set_editor_property("material_domain", unreal.MaterialDomain.MD_DEFERRED_DECAL)
    b.m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    try:  # UE 5.0 ainda tinha "decal blend mode"; nas versões novas o modo vem das saídas ligadas
        b.m.set_editor_property("decal_blend_mode", unreal.DecalBlendMode.DBM_TRANSLUCENT)
    except Exception:  # noqa: BLE001
        pass


def mat_blood_decal():
    b = MB("M_FX_BloodDecal")
    decal_base(b)
    color = b.vparam("Color", HUMAN_BLOOD)
    emis = b.sparam("Emissive", 0.0)
    mask = b.tex("T_FX_BloodSplat")
    life = b.node(unreal.MaterialExpressionDecalLifetimeOpacity)
    b.out(b.mul(color, cb=0.8), MP.MP_BASE_COLOR)
    b.out(b.const(0.2), MP.MP_ROUGHNESS)
    b.out(b.const(0.5), MP.MP_SPECULAR)
    b.out(b.mul(b.mul(mask, life, a_out="R"), cb=0.95), MP.MP_OPACITY)
    b.out(b.mul(b.mul(color, emis), mask, b_out="R"), MP.MP_EMISSIVE_COLOR)
    return b.finish()


def mat_scorch_decal():
    b = MB("M_FX_ScorchDecal")
    decal_base(b)
    color = b.vparam("Color", PISTOL_COLOR)
    emis = b.sparam("Emissive", 3.0)
    mask = b.tex("T_FX_Scorch")
    life = b.node(unreal.MaterialExpressionDecalLifetimeOpacity)
    b.out(b.color((0.02, 0.016, 0.014)), MP.MP_BASE_COLOR)
    b.out(b.const(0.9), MP.MP_ROUGHNESS)
    b.out(b.mul(b.mul(mask, life, a_out="R"), cb=0.85), MP.MP_OPACITY)
    glow = b.power(b.mul(mask, life, a_out="R"), 4.0)  # só o centro brilha e apaga junto com a decal
    b.out(b.mul(b.mul(color, emis), glow), MP.MP_EMISSIVE_COLOR)
    return b.finish()


def make_mi(name, parent, color, emissive):
    path = f"{MAT_DIR}/{name}"
    mi = EAL.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        name, MAT_DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    MEL.set_material_instance_vector_parameter_value(mi, "Color", lc(color))
    MEL.set_material_instance_scalar_parameter_value(mi, "Emissive", float(emissive))
    save(mi)
    log(f"instância {name}")


def materials():
    for fn in (mat_plasma, mat_hitflash, mat_blood):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            err(fn.__name__, exc)
    blood = EAL.load_asset(f"{MAT_DIR}/M_FX_Blood")
    if blood:
        make_mi("MI_FX_Blood_Red", blood, HUMAN_BLOOD, 0.0)
        make_mi("MI_FX_Blood_Blue", blood, ZOMBIE_BLOOD, 2.5)
    for fn in (mat_blood_decal, mat_scorch_decal):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            err(fn.__name__, exc)
    decal = EAL.load_asset(f"{MAT_DIR}/M_FX_BloodDecal")
    if decal:
        make_mi("MI_FX_BloodDecal_Red", decal, HUMAN_BLOOD, 0.0)
        make_mi("MI_FX_BloodDecal_Blue", decal, ZOMBIE_BLOOD, 2.5)


# ------------------------------------------------------------------ 3. sons

def sounds():
    src = os.path.join(REPO, "assets", "work", "audio", "weapons")
    if not os.path.isdir(src):
        warn(f"falta {src} (rode tools/pipeline/gen_weapon_sfx.py)")
        return
    EAL.make_directory(SFX_DIR)
    done = []
    for f in sorted(os.listdir(src)):
        if not f.lower().endswith(".wav"):
            continue
        name = os.path.splitext(f)[0]
        try:
            import_file(os.path.join(src, f), SFX_DIR, name)
            done.append(name)
        except Exception as exc:  # noqa: BLE001
            err(f"som {name}", exc)
    R["info"]["sons"] = done
    log(f"sons importados: {len(done)}")
    path = f"{SFX_DIR}/ATT_JR_Weapons"
    att = EAL.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        "ATT_JR_Weapons", SFX_DIR, unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
    try:
        s = att.get_editor_property("attenuation")
        s.set_editor_property("attenuation_shape_extents", unreal.Vector(400.0, 0.0, 0.0))  # cheio até 4 m
        s.set_editor_property("falloff_distance", 6000.0)  # some em ~60 m
        att.set_editor_property("attenuation", s)
    except Exception as exc:  # noqa: BLE001
        warn(f"ATT_JR_Weapons: não ajustei a distância ({exc}); fica o padrão")
    save(att)


def sfx(name):
    p = f"{SFX_DIR}/{name}"
    return EAL.load_asset(p) if EAL.does_asset_exist(p) else None


# ------------------------------------------------------------------ 4. armas

def weapons():
    att = EAL.load_asset(f"{SFX_DIR}/ATT_JR_Weapons") if EAL.does_asset_exist(f"{SFX_DIR}/ATT_JR_Weapons") else None
    for path, vals in WEAPONS.items():
        da = EAL.load_asset(path)
        if da is None:
            warn(f"falta {path}")
            continue
        where = path.rsplit("/", 1)[1]
        info = {"antes": {}}
        for k in ("damage", "fire_rate", "pellet_count", "reload_time"):
            try:
                info["antes"][k] = da.get_editor_property(k)
            except Exception:  # noqa: BLE001
                pass
        for k, v in vals.items():
            if k == "sounds":
                continue
            setp(da, k, lc(v) if k == "plasma_color" else float(v), where)
        for k, name in vals["sounds"].items():
            s = sfx(name)
            if s is None:
                warn(f"{where}: som {name} ausente")
                continue
            setp(da, k, s, where)
        if att:
            setp(da, "sound_attenuation", att, where)
        save(da)
        R["info"][where] = info
        log(f"{where}: coice/plasma/sons")


# ------------------------------------------------------------------ 5. heróis

def find_armed_idle(nn):
    for folder in (f"/Game/Characters/Hero{nn}/Anims",):
        for p in EAL.list_assets(folder, recursive=True, include_folder=False):
            base = p.split(".")[0].rsplit("/", 1)[-1]
            if any(base.startswith(n) for n in ARMED_IDLE_NAMES):
                a = EAL.load_asset(p.split(".")[0])
                if isinstance(a, unreal.AnimSequenceBase):
                    return a
    return None


def heroes():
    for nn in HEROES:
        path = f"/Game/Characters/Hero{nn}/BP_Character_Hero{nn}"
        bp = EAL.load_asset(path)
        if bp is None:
            warn(f"falta {path}")
            continue
        cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
        where = f"Hero{nn}"
        info = {}
        try:
            info["antes"] = {"default_arm_length": cdo.get_editor_property("default_arm_length"),
                             "aim_arm_length": cdo.get_editor_property("aim_arm_length")}
        except Exception:  # noqa: BLE001
            pass
        setp(cdo, "default_arm_length", 300.0, where)
        setp(cdo, "base_fov", 90.0, where)
        setp(cdo, "aim_fov", 70.0, where)
        setp(cdo, "sprint_fov_bonus", 5.0, where)
        try:
            arm = cdo.get_editor_property("spring_arm")
            arm.set_editor_property("target_arm_length", 300.0)
            arm.set_editor_property("probe_size", 14.0)
            cam = cdo.get_editor_property("camera")
            cam.set_editor_property("field_of_view", 90.0)
        except Exception as exc:  # noqa: BLE001
            warn(f"{where}: câmera ({exc})")
        idle = find_armed_idle(nn)
        if idle is not None:
            setp(cdo, "armed_idle_anim", idle, where)
            info["armed_idle_anim"] = idle.get_name()
        else:
            info["armed_idle_anim"] = None
            warn(f"{where}: sem animação de arma baixa (ArmedIdleAnim). Baixe no mixamo.com um idle segurando "
                 f"pistola com o cano baixo, retargete para o herói e nomeie {ARMED_IDLE_NAMES[0]}_H{nn}; "
                 "rode este script de novo")
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
        R["info"][where] = info
        log(f"{where}: câmera 300 cm, FOV 90/70/+5")


def main():
    for fn in (textures, materials, sounds, weapons, heroes):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            err(fn.__name__, exc)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_combat_feel.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[setup_combat_feel] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
