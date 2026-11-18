"""Etapa 2 (zumbis x carro): liga efeitos do carro e confere os zumbis. Pode rodar de novo.

RODA NO EDITOR (caixa Cmd), sem Play, DEPOIS de compilar o C++:
  py "E:/game/utrazin-game/tools/unreal/setup_car_zombies.py"

1. Procura sistemas Niagara de fumaça, fogo e explosão (em /Game, depois na engine e plugins)
   e coloca no BP_Vehicle_SUV (smoke_system, fire_system, explosion_system). Se não achar,
   o carro usa só a luz laranja do fogo e o clarão (o jogo funciona igual).
2. Procura um som de explosão (nome com "explo") para explosion_sound.
3. Garante nos BP_Enemy_* o raio de perseguição do carro (vehicle_chase_radius >= 4000 cm).
4. Grava no BP_Vehicle_SUV os valores da A-041/A-042 (agarrar até 40 km/h, freada que derruba,
   puxão no volante, bomba de 5 s, fogo que queima o motor). Mude VEHICLE_TUNING abaixo e rode de novo.
5. Confere os destroços da barricada (SM_CarWreck, SM_Roadblock, SM_Barricade, SM_Crate).
Relatório: reports/setup_car_zombies.json (lista também partículas Cascade achadas, não usadas).
"""
import json
import os
import re
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
VEHICLE_BP = "/Game/Vehicles/SUV/BP_Vehicle_SUV"
ENEMY_BPS = ["/Game/Enemies/BP_Enemy_ZombieMelee", "/Game/Enemies/BP_Enemy_ZombieArcher",
             "/Game/Enemies/BP_Enemy_ZombieGunner", "/Game/Enemies/BP_Enemy_ZombieElite"]
MIN_CHASE_CM = 4000.0
# Etapa 2: valores do zumbi x carro no BP do carro (nome Python = nome C++ em snake_case).
VEHICLE_TUNING = {
    "grab_max_speed_kmh": 40.0,           # acima disto ninguém agarra
    "shake_off_speed_kmh": 60.0,          # acima disto os agarrados caem
    "shake_off_lateral_accel": 1000.0,    # curva forte (cm/s²)
    "shake_off_brake_decel": 1100.0,      # freada forte (cm/s²)
    "grabber_steer_pull": 0.08,           # puxão no volante por zumbi na lateral
    "grabber_deceleration": 120.0,        # freio por zumbi agarrado (cm/s²)
    "car_bomb_on_exit_while_burning": True,
    "car_bomb_fuse_time": 5.0,
    "burn_engine_damage_per_second": 1.5,
}
BARRICADE_PROPS = ["/Game/Environment/L01/Props/SM_CarWreck", "/Game/Environment/L01/Props/SM_Roadblock",
                   "/Game/Environment/L01/Props/SM_Barricade", "/Game/Environment/L01/Props/SM_Crate"]
PATTERNS = {
    "smoke_system": re.compile(r"smoke|fumaca", re.I),
    "fire_system": re.compile(r"(?<!wild)fire(?!work)|flame|fogo", re.I),
    "explosion_system": re.compile(r"explo|blast", re.I),
}
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "found": {}, "assigned": {}}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[car_zombies] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[car_zombies] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-900:]})
    unreal.log_error(f"[car_zombies] {where}: {exc}")


def assets_of_class(package, name):
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    flt = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath(package, name)], recursive_classes=True)
    out = []
    for a in ar.get_assets(flt):
        out.append(f"{a.package_name}.{a.asset_name}")
    return out


def rank(path):
    """Prefere conteúdo do projeto; depois engine; por último exemplos/templates de plugin."""
    if path.startswith("/Game/"):
        return 0
    if path.startswith("/Engine/"):
        return 1
    return 2


def pick(paths, pattern):
    hits = [p for p in paths if pattern.search(p.rsplit("/", 1)[-1]) and "template" not in p.lower()]
    hits.sort(key=lambda p: (rank(p), len(p)))
    return hits


def cdo_of(bp_path):
    bp = EAL.load_asset(bp_path)
    if bp is None:
        raise RuntimeError(f"não existe: {bp_path}")
    return bp, unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))


def compile_save(bp):
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    EAL.save_loaded_asset(bp, only_if_is_dirty=False)


def vehicle_fx():
    niagara = assets_of_class("/Script/Niagara", "NiagaraSystem")
    cascade = assets_of_class("/Script/Engine", "ParticleSystem")
    R["found"]["niagara_total"] = len(niagara)
    R["found"]["cascade_matches_not_used"] = [p for p in cascade if re.search(r"smoke|fire|explo", p, re.I)][:20]
    bp, cdo = cdo_of(VEHICLE_BP)
    changed = False
    for prop, pattern in PATTERNS.items():
        hits = pick(niagara, pattern)
        R["found"][prop] = hits[:10]
        current = cdo.get_editor_property(prop)
        if current is not None:
            log(f"{prop} já definido: {current.get_path_name()} (mantido)")
            continue
        if not hits:
            warn(f"{prop}: nenhum Niagara com nome parecido; o carro usa só luz/clarão. "
                 f"Importe um NS_ grátis (ex.: Fab) e rode de novo.")
            continue
        asset = EAL.load_asset(hits[0])
        if asset is None:
            warn(f"{prop}: falha ao carregar {hits[0]}")
            continue
        cdo.set_editor_property(prop, asset)
        R["assigned"][prop] = hits[0]
        changed = True
        log(f"{prop} = {hits[0]}")
    sounds = [p for p in assets_of_class("/Script/Engine", "SoundWave") + assets_of_class("/Script/Engine", "SoundCue")
              if re.search(r"explo", p.rsplit("/", 1)[-1], re.I)]
    sounds.sort(key=lambda p: (rank(p), len(p)))
    R["found"]["explosion_sound"] = sounds[:10]
    if sounds and cdo.get_editor_property("explosion_sound") is None:
        snd = EAL.load_asset(sounds[0])
        if snd:
            cdo.set_editor_property("explosion_sound", snd)
            R["assigned"]["explosion_sound"] = sounds[0]
            changed = True
            log(f"explosion_sound = {sounds[0]}")
    if changed:
        compile_save(bp)
        log("BP_Vehicle_SUV salvo")


def enemies():
    for path in ENEMY_BPS:
        if not EAL.does_asset_exist(path):
            continue
        try:
            bp, cdo = cdo_of(path)
            value = float(cdo.get_editor_property("vehicle_chase_radius"))
            if value < MIN_CHASE_CM:
                cdo.set_editor_property("vehicle_chase_radius", MIN_CHASE_CM)
                compile_save(bp)
                log(f"{path}: vehicle_chase_radius {value:.0f} -> {MIN_CHASE_CM:.0f}")
            else:
                log(f"{path}: vehicle_chase_radius {value:.0f} (ok)")
        except Exception as exc:  # noqa: BLE001
            err(path, exc)


def vehicle_tuning():
    bp, cdo = cdo_of(VEHICLE_BP)
    changed = False
    for prop, value in VEHICLE_TUNING.items():
        try:
            current = cdo.get_editor_property(prop)
        except Exception as exc:  # noqa: BLE001
            err(f"vehicle.{prop} (compilou o C++ novo?)", exc)
            continue
        same = (abs(float(current) - float(value)) < 1e-4) if not isinstance(value, bool) else (bool(current) == value)
        if same:
            log(f"carro {prop} = {current} (ok)")
            continue
        cdo.set_editor_property(prop, value)
        changed = True
        log(f"carro {prop}: {current} -> {value}")
    if changed:
        compile_save(bp)
        log("BP_Vehicle_SUV salvo (tuning zumbi x carro)")


def barricade_props():
    found = [p for p in BARRICADE_PROPS if EAL.does_asset_exist(p)]
    R["found"]["barricade_props"] = found
    if not found:
        warn("nenhum destroço de barricada achado; build_vehicle_test.py usa o cubo da engine")
    else:
        log(f"destroços de barricada: {len(found)} ({', '.join(p.rsplit('/', 1)[-1] for p in found)})")


def main():
    for f in (vehicle_fx, enemies, vehicle_tuning, barricade_props):
        try:
            f()
        except Exception as exc:  # noqa: BLE001
            err(f.__name__, exc)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_car_zombies.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[car_zombies] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
