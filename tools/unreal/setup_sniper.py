"""Rifle de precisão alien (A-058): definição da arma, malha nos heróis, luneta e o baú da vila. Pode rodar de novo.

RODA NO EDITOR (caixa Cmd, sem Play), DEPOIS de compilar o C++ novo e de:
  py "E:/game/utrazin-game/tools/unreal/import_user_assets.py"   (importa SM_ARM_Sniper do assets/work/tripo)
  py "E:/game/utrazin-game/tools/unreal/setup_combat_feel.py"    (sons e materiais de plasma)
Depois:
  py "E:/game/utrazin-game/tools/unreal/setup_sniper.py"
Com o mapa L01 ABERTO, também põe o rifle no baú da vila (Bau_Vila_Municao, zona 6) e salva o mapa.

O que faz (ver reports/setup_sniper.json):
 1. Sons novos (SFX_Plasma_Sniper_Fire, SFX_Plasma_Sniper_Bolt, SFX_Scope_Zoom) se ainda não importados.
 2. /Game/Data/DA_Weapon_AlienSniper (cópia da pistola com os valores do rifle: dano 120, 1 tiro a cada 1,2 s,
    pente 5, reserva 15, alcance 200 m, atravessa 1 corpo, coice grande, plasma ciano da textura do modelo).
 3. BP_Character_Hero01/02: SniperDefinition, SniperStaticMesh e o olho da luneta medido no modelo
    (assets/work/tripo/tripo_processed.json, campo scope_m).
 4. Mapa aberto: baú Bau_Vila_Municao com WeaponInside = Sniper (o build_l01.py já faz isso ao reconstruir).
"""
import json
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
SFX_DIR = "/Game/Audio/SFX/Weapons"
DA_PISTOL = "/Game/Data/DA_Weapon_AlienPistol"
DA_SNIPER = "/Game/Data/DA_Weapon_AlienSniper"
SNIPER_MESH = "/Game/Environment/User/Armas/SM_ARM_Sniper"
HEROES = ("01", "02")
CHEST_LABEL = "Bau_Vila_Municao"
# Ciano dos detalhes brilhantes do modelo (T_ARM_Sniper_D: corpo azul, tubos e visor ciano).
SNIPER_COLOR = (0.1, 0.85, 1.0)
VALUES = {
    "damage": 120.0, "fire_rate": 1.0 / 1.2, "magazine_size": 5, "starting_reserve": 15, "reload_time": 2.6,
    "range": 20000.0, "spread_half_angle_degrees": 0.6, "pellet_count": 1, "pellet_spread_degrees": 0.0,
    "max_pierce": 1,
    "recoil_pitch": 6.0, "recoil_yaw": 0.8, "recoil_recovery": 5.0, "recoil_keep_fraction": 0.25,
    "kick_back": 10.0, "kick_pitch": 12.0, "kick_recovery": 8.0, "shake_scale": 0.5, "crosshair_bloom": 1.0,
    "follow_up_delay": 0.45,
    "plasma_intensity": 35.0, "bolt_speed": 20000.0, "bolt_length": 160.0, "bolt_width": 7.0, "trail_length": 1200.0,
    "muzzle_flash_scale": 1.6, "impact_scale": 1.4, "fire_volume": 1.0, "pitch_variance": 0.03,
}
SOUNDS = {"fire_sound": "SFX_Plasma_Sniper_Fire", "reload_sound": "SFX_Plasma_Reload_Shotgun",
          "impact_sound": "SFX_Plasma_Impact", "dry_fire_sound": "SFX_Plasma_DryFire",
          "follow_up_sound": "SFX_Plasma_Sniper_Bolt"}
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "info": {}, "cpp_needed": []}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[setup_sniper] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[setup_sniper] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-900:]})
    unreal.log_error(f"[setup_sniper] {where}: {exc}")


def setp(obj, prop, value, where):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception:  # noqa: BLE001
        R["cpp_needed"].append(f"{where}.{prop}")
        warn(f"{where}: propriedade {prop} não existe (compilou o C++ novo?)")
        return False


def sounds():
    src = os.path.join(REPO, "assets", "work", "audio", "weapons")
    for name in ("SFX_Plasma_Sniper_Fire", "SFX_Plasma_Sniper_Bolt", "SFX_Scope_Zoom"):
        if EAL.does_asset_exist(f"{SFX_DIR}/{name}"):
            continue
        f = os.path.join(src, name + ".wav")
        if not os.path.exists(f):
            warn(f"falta {f} (rode tools/pipeline/gen_weapon_sfx.py)")
            continue
        task = unreal.AssetImportTask()
        task.filename = f
        task.destination_path = SFX_DIR
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = True
        TOOLS.import_asset_tasks([task])
        log(f"som {name}")


def weapon_def():
    if not EAL.does_asset_exist(DA_SNIPER):
        if not EAL.does_asset_exist(DA_PISTOL):
            raise RuntimeError(f"falta {DA_PISTOL} para copiar")
        EAL.duplicate_asset(DA_PISTOL, DA_SNIPER)
        log("DA_Weapon_AlienSniper criado (cópia da pistola)")
    da = EAL.load_asset(DA_SNIPER)
    setp(da, "weapon_id", unreal.Name("WPN-004"), "DA_Sniper")
    setp(da, "display_name", unreal.Text("Rifle de precisão alien"), "DA_Sniper")
    for k, v in VALUES.items():
        setp(da, k, int(v) if isinstance(v, int) else float(v), "DA_Sniper")
    setp(da, "plasma_color", unreal.LinearColor(*SNIPER_COLOR, 1.0), "DA_Sniper")
    for k, name in SOUNDS.items():
        p = f"{SFX_DIR}/{name}"
        if EAL.does_asset_exist(p):
            setp(da, k, EAL.load_asset(p), "DA_Sniper")
        else:
            warn(f"som {name} ausente (rode setup_combat_feel.py)")
    if EAL.does_asset_exist(f"{SFX_DIR}/ATT_JR_Weapons"):
        setp(da, "sound_attenuation", EAL.load_asset(f"{SFX_DIR}/ATT_JR_Weapons"), "DA_Sniper")
    EAL.save_loaded_asset(da, only_if_is_dirty=False)
    return da


def scope_offset_cm():
    """Olho da luneta (cm, espaço da malha): um pouco atrás e acima do centro da luneta medido no Blender."""
    try:
        proc = json.load(open(os.path.join(REPO, "assets", "work", "tripo", "tripo_processed.json"), encoding="utf-8"))
        sx, sy, sz = proc["ARM_Sniper"]["scope_m"]
        return unreal.Vector(sx * 100.0 - 22.0, sy * 100.0, sz * 100.0 + 3.0)
    except Exception as exc:  # noqa: BLE001
        warn(f"scope_m não achado ({exc}); uso o padrão do C++")
        return None


def heroes(da):
    mesh = EAL.load_asset(SNIPER_MESH) if EAL.does_asset_exist(SNIPER_MESH) else None
    if mesh is None:
        warn(f"falta {SNIPER_MESH}: rode import_user_assets.py (o rifle aparece com a malha da pistola até lá)")
    eye = scope_offset_cm()
    for nn in HEROES:
        path = f"/Game/Characters/Hero{nn}/BP_Character_Hero{nn}"
        bp = EAL.load_asset(path)
        if bp is None:
            warn(f"falta {path}")
            continue
        cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
        where = f"Hero{nn}"
        setp(cdo, "sniper_definition", da, where)
        if mesh:
            setp(cdo, "sniper_static_mesh", mesh, where)
        setp(cdo, "sniper_mesh_scale", 1.0, where)
        if eye:
            setp(cdo, "sniper_scope_offset", eye, where)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        EAL.save_loaded_asset(bp, only_if_is_dirty=False)
        log(f"{where}: rifle ligado")


def chest_in_open_level():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    found = [a for a in actors if a.get_actor_label() == CHEST_LABEL]
    if not found:
        warn(f"mapa aberto sem {CHEST_LABEL}: abra o L01 e rode de novo (ou reconstrua com build_l01.py)")
        return
    for a in found:
        setp(a, "weapon_inside", unreal.JRWeaponSlot.SNIPER, CHEST_LABEL)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log(f"{CHEST_LABEL}: rifle dentro; mapa salvo")


def main():
    for fn in (sounds,):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            err(fn.__name__, exc)
    da = None
    try:
        da = weapon_def()
    except Exception as exc:  # noqa: BLE001
        err("weapon_def", exc)
    if da:
        try:
            heroes(da)
        except Exception as exc:  # noqa: BLE001
            err("heroes", exc)
    try:
        chest_in_open_level()
    except Exception as exc:  # noqa: BLE001
        err("chest", exc)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_sniper.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[setup_sniper] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
