"""Zumbi vivo (A-048): valores de vagar/visão/audição nos DAs e animação de zumbi no andar. Pode rodar de novo.

RODA NO EDITOR (caixa Cmd), sem Play, DEPOIS de compilar o C++ novo:
  py "E:/game/utrazin-game/tools/unreal/setup_zombie_life.py"

1. Grava nos DA_Enemy_Zombie* os valores de LIFE (raio e velocidade de vagar, manada, comer/bater,
   cone de visão, audição, chance de "corredor"). Mude LIFE/COMMON abaixo e rode de novo.
2. Confere nos BP_Enemy_Zombie* que o vagar está ligado (wander_enabled).
3. Retarget das animações de zumbi (A_Zombie_Idle/Walk/Run_Manny) para o Copzombie (sufixo _CZ).
4. SWAP_LOCOMOTION: no BS_Idle_Walk_Run_CZ troca parado/andar/correr PARA FRENTE pelas animações
   de zumbi (os lados/trás continuam os do Manny) e põe o "andar" na velocidade de vagar
   (WALK_SAMPLE_SPEED) para o pé não escorregar. Faz cópia BS_Idle_Walk_Run_CZ_Backup antes (uma vez).
   Só mexe se os zumbis ainda usam o ABP_Unarmed_CZ (se outro script trocou o ABP, pula).
   Desfazer: SWAP_LOCOMOTION = False e UNDO_SWAP = True (copia as amostras do backup de volta).
5. Procura animações de "comer" e variações de parado (nomes eat/feed/bite/scream/roar...) no esqueleto
   do Copzombie e liga como FeedMontage / IdleVariationMontages. Se não houver, o C++ usa o soco lento
   (comer) e um espasmo raro (HitReact lento).
Ordem com os personagens novos (A-052): pode rodar antes ou depois do setup_zombie_chars.py.
   Os passos 1 e 2 valem para qualquer malha; 4 e 5 só agem no Copzombie (o setup_zombie_chars.py
   faz o andar de zumbi nas malhas novas).
Relatório: reports/setup_zombie_life.json
"""
import json
import os
import re
import traceback
from datetime import datetime

import unreal

SWAP_LOCOMOTION = True
UNDO_SWAP = False
WALK_SAMPLE_SPEED = 120.0   # cm/s em que a amostra "andar para frente" fica (média do vagar 90 a 140). None = não mexe
WALK_RATE_SCALE = 1.0       # velocidade da animação de andar de zumbi na blend space (1 = original)
RUN_RATE_SCALE = 1.0

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
KINDS = ("Melee", "Archer", "Gunner", "Elite")
CZ = "/Game/Enemies/Copzombie"
CZ_ANIMS = f"{CZ}/Anims"
CZ_MESH = f"{CZ}/SK_Copzombie"
RTG = "/Game/Characters/Rigs/RTG_Manny_Copzombie"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
BS_CZ = f"{CZ_ANIMS}/BS_Idle_Walk_Run_CZ"
BS_BACKUP = f"{CZ_ANIMS}/BS_Idle_Walk_Run_CZ_Backup"
ZOMBIE_SRC = {
    "idle": "/Game/Enemies/Anims/A_Zombie_Idle_Manny",
    "walk": "/Game/Enemies/Anims/A_Zombie_Walk_Manny",
    "run": "/Game/Enemies/Anims/A_Zombie_Run_Manny",
}
# Amostras da blend space do template que viram zumbi (nome original -> papel).
HUMAN_SAMPLES = {"MM_Idle_CZ": "idle", "MF_Unarmed_Walk_Fwd_CZ": "walk", "MF_Unarmed_Jog_Fwd_CZ": "run"}

# Valores comuns a todos os arquétipos (nome Python = nome C++ em snake_case).
COMMON = {
    "wander_pause_min": 2.0, "wander_pause_max": 6.0, "turn_chance": 0.45,
    "investigate_speed": 230.0, "investigate_time": 15.0,
    "sight_half_angle_degrees": 55.0,      # cone de 110 graus
    "close_sense_radius": 400.0, "hearing_scale": 1.0,
    "walker_chase_speed_scale": 0.72, "anim_rate_jitter": 0.1, "idle_twitch_chance": 0.12,
}
LIFE = {
    "Melee": {"wander_radius_min": 600.0, "wander_radius_max": 2000.0, "wander_speed_min": 90.0,
              "wander_speed_max": 140.0, "runner_chance": 0.7, "herd_chance": 0.35, "feed_chance": 0.6,
              "bang_chance": 0.4},
    "Archer": {"wander_radius_min": 500.0, "wander_radius_max": 1400.0, "wander_speed_min": 90.0,
               "wander_speed_max": 125.0, "runner_chance": 1.0, "herd_chance": 0.2, "feed_chance": 0.4,
               "bang_chance": 0.15},
    "Gunner": {"wander_radius_min": 500.0, "wander_radius_max": 1400.0, "wander_speed_min": 90.0,
               "wander_speed_max": 125.0, "runner_chance": 1.0, "herd_chance": 0.2, "feed_chance": 0.4,
               "bang_chance": 0.15},
    "Elite": {"wander_radius_min": 800.0, "wander_radius_max": 2000.0, "wander_speed_min": 100.0,
              "wander_speed_max": 130.0, "runner_chance": 1.0, "herd_chance": 0.0, "feed_chance": 0.3,
              "bang_chance": 0.5, "hearing_scale": 1.3},
}
FEED_RE = re.compile(r"eat|feed|bite|devour|gnaw|crouch_?idle", re.I)
IDLE_VAR_RE = re.compile(r"scream|roar|agoni|idle_?var|look_?around|scratch|sway|groan", re.I)
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "das": {}, "blendspace": {},
     "anims": {}}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[zombie_life] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[zombie_life] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-900:]})
    unreal.log_error(f"[zombie_life] {where}: {exc}")


def save(a):
    EAL.save_loaded_asset(a, only_if_is_dirty=False)


def cdo_of(path):
    bp = EAL.load_asset(path)
    if bp is None:
        raise RuntimeError(f"não existe: {path}")
    return bp, unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))


def short(a):
    return a.get_path_name().split(".")[0] if a else None


# ------------------------------------------------------------------ 1. DAs

def data_assets():
    for kind in KINDS:
        path = f"/Game/Data/DA_Enemy_Zombie{kind}"
        if not EAL.does_asset_exist(path):
            continue
        da = EAL.load_asset(path)
        values = dict(COMMON)
        values.update(LIFE.get(kind, LIFE["Melee"]))
        changed = []
        for prop, value in values.items():
            try:
                current = float(da.get_editor_property(prop))
            except Exception as exc:  # noqa: BLE001
                err(f"{path}.{prop} (compilou o C++ novo?)", exc)
                return
            if abs(current - value) > 1e-4:
                da.set_editor_property(prop, value)
                changed.append(f"{prop} {current:g}->{value:g}")
        R["das"][kind] = changed or "ok (nada mudou)"
        if changed:
            save(da)
            log(f"DA_Enemy_Zombie{kind}: {len(changed)} valor(es)")
        else:
            log(f"DA_Enemy_Zombie{kind}: ok")


# ------------------------------------------------------------------ 2. BPs

def blueprints():
    for kind in KINDS:
        path = f"/Game/Enemies/BP_Enemy_Zombie{kind}"
        if not EAL.does_asset_exist(path):
            continue
        bp, cdo = cdo_of(path)
        if not bool(cdo.get_editor_property("wander_enabled")):
            cdo.set_editor_property("wander_enabled", True)
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            save(bp)
            log(f"BP_Enemy_Zombie{kind}: vagar ligado")
        else:
            log(f"BP_Enemy_Zombie{kind}: vagar ok")


# ------------------------------------------------------------------ 3. retarget

def zombie_anims_cz():
    """Retarget (uma vez) Idle/Walk/Run de zumbi para o esqueleto do Copzombie."""
    out = {k: f"{CZ_ANIMS}/{src.split('/')[-1]}_CZ" for k, src in ZOMBIE_SRC.items()}
    missing = [k for k, p in out.items() if not EAL.does_asset_exist(p) and EAL.does_asset_exist(ZOMBIE_SRC[k])]
    if missing:
        for p in (CZ_MESH, RTG, MANNY):
            if not EAL.does_asset_exist(p):
                raise RuntimeError(f"falta {p} (rode setup_zombie_skin.py antes)")
        unreal.IKRetargetBatchOperation.duplicate_and_retarget(
            [EAL.find_asset_data(ZOMBIE_SRC[k]) for k in missing], EAL.load_asset(MANNY), EAL.load_asset(CZ_MESH),
            EAL.load_asset(RTG), search="", replace="", prefix="", suffix="_CZ", target_path=CZ_ANIMS,
            use_source_path=False, include_referenced_assets=False, overwrite_existing_files=False)
        for k in missing:
            if EAL.does_asset_exist(out[k]):
                save(EAL.load_asset(out[k]))
                log(f"retarget {k}: {out[k]}")
    found = {k: p for k, p in out.items() if EAL.does_asset_exist(p)}
    R["anims"]["zombie_cz"] = found
    for k in ZOMBIE_SRC:
        if k not in found:
            warn(f"animação de zumbi '{k}' não disponível no Copzombie ({ZOMBIE_SRC[k]} não existe?)")
    return found


# ------------------------------------------------------------------ 4. blend space

def describe(bs):
    out = []
    for s in bs.get_editor_property("sample_data"):
        a = s.get_editor_property("animation")
        v = s.get_editor_property("sample_value")
        out.append(f"{a.get_name() if a else 'NENHUMA'} @ ({v.x:.0f}, {v.y:.0f}) x{s.get_editor_property('rate_scale'):.2f}")
    return out


def speed_axis(bs):
    try:
        params = list(bs.get_editor_property("blend_parameters"))
    except Exception:  # noqa: BLE001
        return None
    names = []
    for i, p in enumerate(params[:2]):
        n = str(p.get_editor_property("display_name"))
        names.append(n)
        if "speed" in n.lower() or "velocidade" in n.lower():
            R["blendspace"]["eixos"] = names
            return i
    R["blendspace"]["eixos"] = names
    return None


def swap_locomotion(zanims):
    if UNDO_SWAP:
        if not EAL.does_asset_exist(BS_BACKUP):
            warn("UNDO_SWAP: não há BS_Idle_Walk_Run_CZ_Backup")
            return
        bs = EAL.load_asset(BS_CZ)
        bs.set_editor_property("sample_data", list(EAL.load_asset(BS_BACKUP).get_editor_property("sample_data")))
        save(bs)
        R["blendspace"]["depois"] = describe(bs)
        log("BS_Idle_Walk_Run_CZ voltou ao backup (andar do Manny)")
        return
    if not SWAP_LOCOMOTION:
        log("SWAP_LOCOMOTION desligado: blend space não mexida")
        return
    _, melee = cdo_of("/Game/Enemies/BP_Enemy_ZombieMelee")
    anim_cls = melee.get_editor_property("mesh").get_editor_property("anim_class")
    abp = anim_cls.get_path_name() if anim_cls else ""
    R["blendspace"]["abp_zumbi"] = abp
    if "ABP_Unarmed_CZ" not in abp:
        if "/Characters/Zombies/" in abp:
            log("zumbis usam os personagens novos: o andar de zumbi é feito pelo setup_zombie_chars.py")
        else:
            warn(f"zumbis usam outro ABP ({abp or 'nenhum'}): blend space não mexida")
        return
    if not EAL.does_asset_exist(BS_CZ):
        warn(f"não achei {BS_CZ}")
        return
    if not all(k in zanims for k in ("idle", "walk", "run")):
        warn("faltam animações de zumbi no Copzombie: blend space não mexida")
        return
    if not EAL.does_asset_exist(BS_BACKUP):
        EAL.duplicate_asset(BS_CZ, BS_BACKUP)
        save(EAL.load_asset(BS_BACKUP))
        log("backup: BS_Idle_Walk_Run_CZ_Backup")
    bs = EAL.load_asset(BS_CZ)
    R["blendspace"]["antes"] = describe(bs)
    axis = speed_axis(bs)
    seqs = {k: EAL.load_asset(p) for k, p in zanims.items()}
    zombie_names = {seqs[k].get_name(): k for k in seqs}
    samples = list(bs.get_editor_property("sample_data"))
    changed = 0
    for s in samples:
        a = s.get_editor_property("animation")
        name = a.get_name() if a else ""
        role = HUMAN_SAMPLES.get(name) or zombie_names.get(name)
        if not role:
            continue
        if a != seqs[role]:
            s.set_editor_property("animation", seqs[role])
            changed += 1
        if role == "walk":
            s.set_editor_property("rate_scale", WALK_RATE_SCALE)
            if WALK_SAMPLE_SPEED is not None and axis is not None:
                v = s.get_editor_property("sample_value")
                if axis == 0:
                    v.x = WALK_SAMPLE_SPEED
                else:
                    v.y = WALK_SAMPLE_SPEED
                s.set_editor_property("sample_value", v)
        elif role == "run":
            s.set_editor_property("rate_scale", RUN_RATE_SCALE)
    if axis is None and WALK_SAMPLE_SPEED is not None:
        warn("não achei o eixo Speed da blend space: velocidade da amostra de andar mantida")
    bs.set_editor_property("sample_data", samples)
    save(bs)
    R["blendspace"]["depois"] = describe(bs)
    log(f"BS_Idle_Walk_Run_CZ: {changed} amostra(s) trocadas por zumbi (andar em {WALK_SAMPLE_SPEED} cm/s)")


# ------------------------------------------------------------------ 5. comer / variações

def anims_on_cz():
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    flt = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "AnimSequence")],
                          package_paths=["/Game"], recursive_paths=True)
    out = []
    for d in ar.get_assets(flt):
        path = str(d.package_name)
        if "/Copzombie/" in path:
            out.append(path)
    return out


def montage_for(seq_path):
    name = "AM_" + seq_path.split("/")[-1].removeprefix("A_")
    dst = f"{CZ_ANIMS}/{name}"
    if EAL.does_asset_exist(dst):
        return EAL.load_asset(dst)
    f = unreal.AnimMontageFactory()
    f.set_editor_property("source_animation", EAL.load_asset(seq_path))
    m = TOOLS.create_asset(name, CZ_ANIMS, unreal.AnimMontage, f)
    if m:
        save(m)
        log(f"montage criada: {dst}")
    return m


def life_montages():
    # Montages achadas aqui são do esqueleto do Copzombie: só liga se os zumbis ainda usam o Copzombie
    # (com os personagens novos, rode setup_zombie_chars.py de novo: ele retargeta o que estiver nos DAs).
    _, melee = cdo_of("/Game/Enemies/BP_Enemy_ZombieMelee")
    cur = short(melee.get_editor_property("mesh").get_editor_property("skeletal_mesh_asset")) or ""
    if "/Copzombie/" not in cur:
        log(f"zumbis usam {cur or 'outra malha'}: comer/variações do Copzombie não são ligados")
        return
    seqs = anims_on_cz()
    feed = [p for p in seqs if FEED_RE.search(p.split("/")[-1])]
    idle_var = [p for p in seqs if IDLE_VAR_RE.search(p.split("/")[-1])]
    R["anims"]["feed_candidatos"] = feed
    R["anims"]["idle_var_candidatos"] = idle_var
    if not feed:
        warn("sem animação de comer no Copzombie: o C++ usa o soco lento (importe uma 'zombie eating' do Mixamo)")
    if not idle_var:
        log("sem variações de parado: o C++ usa um espasmo raro (HitReact lento)")
    feed_m = montage_for(feed[0]) if feed else None
    var_m = [m for m in (montage_for(p) for p in idle_var[:4]) if m]
    for kind in KINDS:
        path = f"/Game/Data/DA_Enemy_Zombie{kind}"
        if not EAL.does_asset_exist(path):
            continue
        da = EAL.load_asset(path)
        dirty = False
        if feed_m and da.get_editor_property("feed_montage") is None:
            da.set_editor_property("feed_montage", feed_m)
            dirty = True
        if var_m and not list(da.get_editor_property("idle_variation_montages")):
            da.set_editor_property("idle_variation_montages", var_m)
            dirty = True
        if dirty:
            save(da)
            log(f"DA_Enemy_Zombie{kind}: montages de vida ligadas")


def main():
    for f in (data_assets, blueprints):
        try:
            f()
        except Exception as exc:  # noqa: BLE001
            err(f.__name__, exc)
    zanims = {}
    try:
        zanims = zombie_anims_cz()
    except Exception as exc:  # noqa: BLE001
        err("zombie_anims_cz", exc)
    try:
        swap_locomotion(zanims)
    except Exception as exc:  # noqa: BLE001
        err("swap_locomotion", exc)
    try:
        life_montages()
    except Exception as exc:  # noqa: BLE001
        err("life_montages", exc)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_zombie_life.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[zombie_life] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
