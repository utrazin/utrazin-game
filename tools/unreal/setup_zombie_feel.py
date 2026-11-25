"""Sensação do zumbi (A-081): passo sem escorregar e contorno brilhante. Pode rodar de novo.

RODA NO EDITOR (caixa Cmd), sem Play, DEPOIS de compilar o C++ novo (campos LocomotionRunSpeed/MaxLocomotionRate):
  py "E:/game/utrazin-game/tools/unreal/setup_zombie_feel.py"

1. MATERIAL: cria/refaz /Game/Materials/Remap/M_ZombieRim (Unlit, Additive, usado em malha esquelética):
   Fresnel -> x Cor -> x Intensidade -> Emissive. Parâmetros: "Intensidade" (o C++ anima por MID),
   "Cor" (verde-tóxico) e "Expoente" (espessura do contorno). O AJREnemyCharacter aplica como
   OverlayMaterial no BeginPlay; sem este asset nada muda.
2. PASSO: para cada personagem de zumbi usado pelos BP_Enemy_Zombie* mede, na própria animação
   retargetada (A_Zombie_Walk_<sufixo> e A_Zombie_Run_<sufixo>), a velocidade do pé apoiado no chão
   (= velocidade em que o corpo deveria andar). Na BS_Idle_Walk_Run_<sufixo> põe as amostras "andar
   para frente" e "correr para frente" nessa velocidade (x rate_scale da amostra). Antes, a corrida
   ficava em 600 cm/s e o andar em 120: em 400 cm/s a blend space misturava andar+correr e o corpo
   deslizava. Cópia de segurança BS_..._PreA081 (uma vez). Desfazer: UNDO = True.
3. DAs: grava em DA_Enemy_Zombie* LocomotionRunSpeed (= amostra de correr) e MaxLocomotionRate.
   O C++ acelera a animação acima disso e limita a perseguição a LocomotionRunSpeed x MaxLocomotionRate.
   ADJUST_WANDER: se o vagar (WanderSpeedMin/Max) ficou muito acima do andar medido, baixa
   (nunca sobe) para o zumbi calmo cambalear no passo da animação.
Relatório: reports/setup_zombie_feel.json
"""
import json
import math
import os
import traceback
from datetime import datetime

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
REPORT = os.path.join(REPO, "reports", "setup_zombie_feel.json")

# ------------------------------------------------------------------ ajustes (mude e rode de novo)
BUILD_MATERIAL = True
FIX_BLENDSPACES = True
WRITE_DAS = True
ADJUST_WANDER = True
UNDO = False                  # True: devolve as amostras das blend spaces do backup e zera LocomotionRunSpeed
MAX_LOCOMOTION_RATE = 1.5     # maior aceleração da corrida (C++: MaxLocomotionRate)
WANDER_MAX_OVER_WALK = 1.35   # vagar no máximo 35% acima do andar medido (a blend space mistura um pouco de corrida)
WANDER_MIN_OVER_WALK = 0.85
WANDER_FLOOR = 45.0           # cm/s: nunca vagar mais devagar que isto
SPEED_SANITY = (15.0, 1200.0)  # cm/s: medida fora disto é descartada

RIM_PATH = "/Game/Materials/Remap/M_ZombieRim"
RIM_COLOR = (0.25, 1.0, 0.12)   # verde-tóxico (mesmo tom do tiro dos zumbis)
RIM_EXPONENT = 3.5               # maior = contorno mais fino
RIM_INTENSITY_DEFAULT = 1.0      # o C++ sobrescreve (RimIntensity)

KINDS = ("Melee", "Archer", "Gunner", "Elite")
CHARS = {  # pasta do personagem -> sufixo das animações (setup_zombie_models.py)
    "ZMB_Comum": "_Comum",
    "ZMB_Corredor": "_Corredor",
    "ZMB_Tanque": "_Tanque",
}
FOOT_NAMES = {"l": ("LeftFoot", "foot_l"), "r": ("RightFoot", "foot_r")}
HIP_NAMES = ("Hips", "pelvis")

R = {"time": datetime.now().isoformat(), "undo": UNDO, "material": {}, "chars": {}, "das": {},
     "steps": [], "warnings": [], "errors": []}


# ------------------------------------------------------------------ funções puras (testadas em tests/python)

def _median(values):
    v = sorted(values)
    n = len(v)
    if n == 0:
        return None
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def estimate_ground_speed(frames, plant_margin=4.0, root_motion_threshold=20.0):
    """Velocidade (cm/s) em que o corpo deve andar para o pé apoiado não escorregar.

    frames: lista de (t, quadril, pé_esq, pé_dir), cada ponto (x, y, z) em cm no espaço do componente.
    Animação no lugar ("in place"): mediana da velocidade horizontal do pé que está no chão.
    Animação com deslocamento no quadril: deslocamento do quadril / duração.
    Retorna (velocidade, detalhe) ou (None, motivo).
    """
    if len(frames) < 8:
        return None, "poucos quadros"
    n = len(frames)
    # eixo "para cima": onde o quadril fica mais longe dos pés
    up_gap = []
    for k in range(3):
        up_gap.append(sum(f[1][k] - 0.5 * (f[2][k] + f[3][k]) for f in frames) / n)
    up = max(range(3), key=lambda k: abs(up_gap[k]))
    sign = 1.0 if up_gap[up] > 0 else -1.0
    hz = [k for k in range(3) if k != up]
    duration = frames[-1][0] - frames[0][0]
    if duration <= 0:
        return None, "duração zero"

    hip0, hip1 = frames[0][1], frames[-1][1]
    hip_travel = math.hypot(hip1[hz[0]] - hip0[hz[0]], hip1[hz[1]] - hip0[hz[1]])
    if hip_travel / duration > root_motion_threshold:
        return hip_travel / duration, {"modo": "quadril anda", "up": up}

    height = {j: [sign * f[j][up] for f in frames] for j in (2, 3)}
    floor = {j: min(height[j]) for j in (2, 3)}
    speeds = []
    for i in range(n - 1):
        dt = frames[i + 1][0] - frames[i][0]
        if dt <= 0:
            continue
        for j, other in ((2, 3), (3, 2)):
            if height[j][i] > floor[j] + plant_margin or height[j][i + 1] > floor[j] + plant_margin:
                continue
            if height[j][i] > height[other][i] + 1.0:
                continue  # o outro pé está mais baixo: este não é o de apoio
            a, b = frames[i][j], frames[i + 1][j]
            speeds.append(math.hypot(b[hz[0]] - a[hz[0]], b[hz[1]] - a[hz[1]]) / dt)
    if len(speeds) < 4:
        return None, "pé de apoio não encontrado"
    return _median(speeds), {"modo": "pé de apoio", "up": up, "amostras": len(speeds)}


def sane_speed(value):
    return value is not None and SPEED_SANITY[0] <= value <= SPEED_SANITY[1]


def wander_targets(walk_speed, current_min, current_max):
    """Novos (min, max) do vagar: só baixa, nunca sobe. None = não mexe."""
    if not sane_speed(walk_speed):
        return None
    hi = max(WANDER_FLOOR, walk_speed * WANDER_MAX_OVER_WALK)
    lo = max(WANDER_FLOOR, walk_speed * WANDER_MIN_OVER_WALK)
    new_max = min(current_max, hi)
    new_min = min(current_min, lo, new_max)
    if abs(new_max - current_max) < 1.0 and abs(new_min - current_min) < 1.0:
        return None
    return round(new_min, 1), round(new_max, 1)


def char_of_mesh_path(path):
    """Pasta do personagem (ZMB_Comum etc.) a partir do caminho da malha do BP."""
    for name in CHARS:
        if f"/{name}/" in (path or ""):
            return name
    return None


# ------------------------------------------------------------------ editor

def log(m):
    import unreal
    R["steps"].append(m)
    unreal.log(f"[zombie_feel] {m}")


def warn(m):
    import unreal
    R["warnings"].append(m)
    unreal.log_warning(f"[zombie_feel] {m}")


def err(where, exc):
    import unreal
    R["errors"].append({"onde": where, "erro": str(exc), "trace": traceback.format_exc()[-1500:]})
    unreal.log_error(f"[zombie_feel] {where}: {exc}")


def eal():
    import unreal
    return unreal.EditorAssetLibrary


def save(asset):
    eal().save_loaded_asset(asset, only_if_is_dirty=False)


# 1. material ---------------------------------------------------------------------------------

def build_rim_material():
    import unreal
    mel = unreal.MaterialEditingLibrary
    folder, name = RIM_PATH.rsplit("/", 1)
    if eal().does_asset_exist(RIM_PATH):
        mat = eal().load_asset(RIM_PATH)
        mel.delete_all_material_expressions(mat)
        R["material"]["acao"] = "refeito"
    else:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mat = tools.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
        R["material"]["acao"] = "criado"
    if mat is None:
        raise RuntimeError(f"não consegui criar {RIM_PATH}")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    for prop in ("used_with_skeletal_mesh",):
        try:
            mat.set_editor_property(prop, True)
        except Exception as exc:  # noqa: BLE001
            warn(f"material: {prop}: {exc}")

    fres = mel.create_material_expression(mat, unreal.MaterialExpressionFresnel, -700, 0)
    fres.set_editor_property("exponent", RIM_EXPONENT)
    fres.set_editor_property("base_reflect_fraction", 0.0)
    expo = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -1000, -40)
    expo.set_editor_property("parameter_name", "Expoente")
    expo.set_editor_property("default_value", RIM_EXPONENT)
    if not mel.connect_material_expressions(expo, "", fres, "ExponentIn"):
        warn("material: não liguei Expoente no Fresnel (fica fixo em RIM_EXPONENT)")
    color = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -700, 200)
    color.set_editor_property("parameter_name", "Cor")
    color.set_editor_property("default_value", unreal.LinearColor(RIM_COLOR[0], RIM_COLOR[1], RIM_COLOR[2], 1.0))
    inten = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -450, 300)
    inten.set_editor_property("parameter_name", "Intensidade")
    inten.set_editor_property("default_value", RIM_INTENSITY_DEFAULT)
    mul1 = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -400, 60)
    mel.connect_material_expressions(fres, "", mul1, "A")
    mel.connect_material_expressions(color, "", mul1, "B")
    mul2 = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -200, 120)
    mel.connect_material_expressions(mul1, "", mul2, "A")
    mel.connect_material_expressions(inten, "", mul2, "B")
    if not mel.connect_material_property(mul2, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError("não liguei o Emissive")
    mel.recompile_material(mat)
    save(mat)
    R["material"].update({"path": RIM_PATH, "blend": "Additive", "shading": "Unlit", "cor": RIM_COLOR,
                          "expoente": RIM_EXPONENT})
    log(f"{RIM_PATH}: {R['material']['acao']} (Additive/Unlit, Fresnel x Cor x Intensidade)")


# 2. passo ------------------------------------------------------------------------------------

def find_bone(names, candidates):
    for c in candidates:
        for n in names:
            s = str(n)
            if s == c or s.endswith(":" + c) or s.endswith("_" + c):
                return s
    return None


def sample_frames(anim, per_second=60, max_frames=480):
    import unreal
    length = float(anim.get_play_length())
    count = int(min(max_frames, max(48, length * per_second)))
    opts = unreal.AnimPoseEvaluationOptions()
    pose0 = unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, 0.0, opts)
    names = list(unreal.AnimPoseExtensions.get_bone_names(pose0))
    hips = find_bone(names, HIP_NAMES)
    foot_l = find_bone(names, FOOT_NAMES["l"])
    foot_r = find_bone(names, FOOT_NAMES["r"])
    if not (hips and foot_l and foot_r):
        raise RuntimeError(f"{anim.get_name()}: ossos não achados (quadril={hips}, pés={foot_l}/{foot_r})")
    frames = []
    for i in range(count):
        t = length * i / count
        pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, t, opts)
        row = [t]
        for b in (hips, foot_l, foot_r):
            v = unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD).translation
            row.append((float(v.x), float(v.y), float(v.z)))
        frames.append(tuple(row))
    return frames, {"bones": [hips, foot_l, foot_r], "len": round(length, 3), "quadros": count}


def speed_axis(bs):
    params = list(bs.get_editor_property("blend_parameters"))
    for i, p in enumerate(params[:2]):
        n = str(p.get_editor_property("display_name")).lower()
        if "speed" in n or "velocidade" in n:
            return i
    return None


def describe(bs):
    out = []
    for s in bs.get_editor_property("sample_data"):
        a = s.get_editor_property("animation")
        v = s.get_editor_property("sample_value")
        out.append(f"{a.get_name() if a else 'NENHUMA'} @ ({v.x:.0f}, {v.y:.0f}) x{s.get_editor_property('rate_scale'):.2f}")
    return out


def bs_path_of(char):
    return f"/Game/Characters/Zombies/{char}/Anims/BS_Idle_Walk_Run{CHARS[char]}"


def fix_blendspace(char):
    """Mede andar/correr do personagem e põe as amostras para frente na velocidade certa."""
    path = bs_path_of(char)
    info = R["chars"].setdefault(char, {"bs": path})
    if not eal().does_asset_exist(path):
        warn(f"{char}: não achei {path} (rode setup_zombie_models.py)")
        return None
    backup = path + "_PreA081"
    if not eal().does_asset_exist(backup):
        eal().duplicate_asset(path, backup)
        eal().save_asset(backup, only_if_is_dirty=False)
        info["backup"] = backup
    bs = eal().load_asset(path)
    axis = speed_axis(bs)
    if axis is None:
        warn(f"{char}: blend space sem eixo de velocidade (nome 'Speed'): não mexi")
        return None
    info["antes"] = describe(bs)
    samples = list(bs.get_editor_property("sample_data"))
    result = {}
    for s in samples:
        a = s.get_editor_property("animation")
        if a is None:
            continue
        nm = a.get_name()
        role = "walk" if nm.startswith("A_Zombie_Walk") else "run" if nm.startswith("A_Zombie_Run") else None
        if role is None or role in result:
            continue
        frames, meta = sample_frames(a)
        native, detail = estimate_ground_speed(frames)
        rate = float(s.get_editor_property("rate_scale")) or 1.0
        meta.update({"anim": nm, "nativa_cm_s": None if native is None else round(native, 1), "detalhe": detail,
                     "rate_scale": rate})
        info[role] = meta
        if not sane_speed(native):
            warn(f"{char}: medida de {nm} fora do esperado ({native}, {detail}): não mexi nesta amostra")
            continue
        result[role] = (s, round(native * rate, 1))
    if "walk" in result and "run" in result and result["run"][1] < result["walk"][1] * 1.2:
        warn(f"{char}: correr ({result['run'][1]}) quase igual a andar ({result['walk'][1]}): não mexi")
        return None
    changed = {}
    for role, (s, value) in result.items():
        v = s.get_editor_property("sample_value")
        if axis == 0:
            v.x = value
        else:
            v.y = value
        s.set_editor_property("sample_value", v)
        changed[role] = value
    if changed:
        bs.set_editor_property("sample_data", samples)
        save(bs)
    info["depois"] = describe(bs)
    info["amostras_cm_s"] = changed
    log(f"{char}: blend space andar={changed.get('walk')} correr={changed.get('run')} cm/s")
    return changed


def undo_blendspace(char):
    path = bs_path_of(char)
    backup = path + "_PreA081"
    if not (eal().does_asset_exist(path) and eal().does_asset_exist(backup)):
        warn(f"{char}: sem backup {backup}: nada a desfazer")
        return
    bs = eal().load_asset(path)
    bs.set_editor_property("sample_data", list(eal().load_asset(backup).get_editor_property("sample_data")))
    save(bs)
    log(f"{char}: blend space devolvida ao backup")


# 3. DAs --------------------------------------------------------------------------------------

def char_of_kind(kind):
    import unreal
    bp = eal().load_asset(f"/Game/Enemies/BP_Enemy_Zombie{kind}")
    if bp is None:
        return None
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    mesh = cdo.get_editor_property("mesh")
    sk = mesh.get_editor_property("skeletal_mesh_asset") if mesh else None
    return char_of_mesh_path(sk.get_path_name() if sk else "")


def write_da(kind, speeds):
    path = f"/Game/Data/DA_Enemy_Zombie{kind}"
    if not eal().does_asset_exist(path):
        warn(f"{path} não existe")
        return
    da = eal().load_asset(path)
    changes = {}
    run = 0.0 if UNDO or not speeds else float(speeds.get("run") or 0.0)
    try:
        if not UNDO and run <= 0.0:
            warn(f"{path}: sem medida de corrida: LocomotionRunSpeed fica como está")
        else:
            changes["locomotion_run_speed"] = (float(da.get_editor_property("locomotion_run_speed")), run)
            da.set_editor_property("locomotion_run_speed", run)
        changes["max_locomotion_rate"] = (float(da.get_editor_property("max_locomotion_rate")), MAX_LOCOMOTION_RATE)
        da.set_editor_property("max_locomotion_rate", MAX_LOCOMOTION_RATE)
    except Exception as exc:  # noqa: BLE001
        err(f"{path} (compilou o C++ novo do A-081?)", exc)
        return
    if ADJUST_WANDER and not UNDO and speeds and speeds.get("walk"):
        cur_min = float(da.get_editor_property("wander_speed_min"))
        cur_max = float(da.get_editor_property("wander_speed_max"))
        target = wander_targets(float(speeds["walk"]), cur_min, cur_max)
        if target:
            da.set_editor_property("wander_speed_min", target[0])
            da.set_editor_property("wander_speed_max", target[1])
            changes["wander_speed"] = ([cur_min, cur_max], list(target))
    save(da)
    R["das"][kind] = changes
    log(f"DA_Enemy_Zombie{kind}: {changes}")


def main():
    import unreal  # noqa: F401
    if BUILD_MATERIAL and not UNDO:
        try:
            build_rim_material()
        except Exception as exc:  # noqa: BLE001
            err("material", exc)
    owners = {}
    for kind in KINDS:
        try:
            char = char_of_kind(kind)
        except Exception as exc:  # noqa: BLE001
            err(f"BP_Enemy_Zombie{kind}", exc)
            char = None
        R.setdefault("kinds", {})[kind] = char
        if char is None:
            warn(f"BP_Enemy_Zombie{kind}: malha não é ZMB_* (setup_zombie_models.py rodou?): pulei")
            continue
        owners.setdefault(char, []).append(kind)
    speeds = {}
    for char in owners:
        try:
            if UNDO:
                undo_blendspace(char)
            elif FIX_BLENDSPACES:
                speeds[char] = fix_blendspace(char)
        except Exception as exc:  # noqa: BLE001
            err(f"{char} blend space", exc)
    if WRITE_DAS:
        for char, kinds in owners.items():
            for kind in kinds:
                try:
                    write_da(kind, speeds.get(char))
                except Exception as exc:  # noqa: BLE001
                    err(f"DA {kind}", exc)


def run():
    import unreal
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        err("main", exc)
    finally:
        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
        with open(REPORT, "w", encoding="utf-8") as fh:
            json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
        unreal.log(f"[zombie_feel] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])} | {REPORT}")


# No editor roda direto; fora dele (pytest) só as funções puras são importadas.
try:
    import unreal as _unreal_check  # noqa: F401
except ImportError:
    _unreal_check = None
if _unreal_check is not None and hasattr(_unreal_check, "EditorAssetLibrary"):
    run()
