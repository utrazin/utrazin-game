"""Vegetação densa da Fase 1 v3 (agente Densidade, A-060): enche o L01_ZombieValley de plantas, árvores e pedras.

RODA NO EDITOR (caixa Cmd, sem Play), DEPOIS de compilar o C++ (AJRInstancedScatter) e do build_l01.py:
  py "E:/game/utrazin-game/tools/unreal/scatter_l01.py"            (refaz tudo; pode rodar de novo)
  py "E:/game/utrazin-game/tools/unreal/scatter_l01.py" limpar     (só apaga a vegetação)
  py "E:/game/utrazin-game/tools/unreal/scatter_l01.py" nanite     (liga Nanite nas malhas do usuário; ver NANITE)
O build_l01.py (v3) também chama este script no fim (bloco marcado [A-060]).

Entradas (geradas fora da Unreal por tools/blender/scatter_l01_v3.py):
  assets/work/levels/L01/l01_scatter_v3.bin    posições/rotações/escalas (float32)
  assets/work/levels/L01/l01_scatter_v3.json   índice: lotes por pedaço de 250 m, malhas, corte, colisão, sombra
Malhas:
  modelos do usuário /Game/Environment/User/<Categoria>/SM_<Nome> (import_user_assets.py; árvores, arbustos,
  cogumelos, flores, tentáculos, pedras, cristais, troncos) = a vegetação principal;
  Quaternius (quaternius_lib.py) só no chão: grama, trevo, samambaia, pétalas, pedrinhas, recoloridas por
  /Game/Environment/Scatter/Materials/MI_Scatter_<Nome> (filhas de M_JR_ScatterTint: azul-petróleo/violeta/magenta).
Faz:
  1. apaga os atores com a tag L01Scatter (pode rodar quantas vezes quiser);
  2. prepara as malhas: LODs extras (4 níveis) nos modelos do usuário, uso com instâncias nos materiais;
  3. um AJRInstancedScatter por pedaço de 250 m (pasta L01/Vegetacao), um HISM por malha/corte;
  4. salva o mapa; relatório em reports/scatter_l01.json.
Depois: Build > Build Paths (as árvores e pedras com colisão mudam a navegação dos zumbis).
"""
import json
import os
import sys
import time
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SRC = os.path.join(REPO, "assets", "work", "levels", "L01")
INDEX = os.path.join(SRC, "l01_scatter_v3.json")
MAP = "/Game/Levels/L01_ZombieValley/L01_ZombieValley"
TAG = "L01Scatter"
FOLDER = "L01/Vegetacao"
MAT_DIR = "/Game/Environment/Scatter/Materials"
MASTER = f"{MAT_DIR}/M_JR_ScatterTint"
WHITE = "/Engine/EngineResources/WhiteSquareTexture"
# ---------------------------------------------------------------- ajustes
# Nanite: o projeto está com r.Nanite.ProjectEnabled=False (RENDERING.md: só com medição). Com o projeto
# desligado a malha Nanite usa a "fallback" e não ganha nada; por isso o padrão são LODs automáticos.
# Para testar: rode com o argumento "nanite" E ligue r.Nanite.ProjectEnabled=True no DefaultEngine.ini.
NANITE = False
LOD_STEPS = [(1.0, 1.0), (0.40, 0.45), (0.15, 0.18), (0.05, 0.06)]   # (% triângulos, tamanho na tela)
ADD_LODS_TO_USER = True

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "counts_by_layer": {},
     "counts_by_mesh": {}, "meshes": {}, "actors": 0}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[scatter_l01] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[scatter_l01] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-900:]})
    unreal.log_error(f"[scatter_l01] {where}: {exc}")


def here_import(name):
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.append(here)
    return __import__(name)


def scatter_class():
    cls = getattr(unreal, "JRInstancedScatter", None)
    if cls is None:
        cls = unreal.load_class(None, "/Script/JogoResgate.JRInstancedScatter")
    if cls is None:
        raise RuntimeError("classe AJRInstancedScatter não existe: compile o C++ (Build.bat) e abra o editor de novo")
    return cls


# ---------------------------------------------------------------- materiais
def setp(obj, k, v):
    try:
        obj.set_editor_property(k, v)
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"{obj.get_name()}.{k}: {exc}")
        return False


def master_tint():
    """M_JR_ScatterTint: cor = brilho da textura x (Tint..Tint2 por instância); dois lados; brilho opcional."""
    if EAL.does_asset_exist(MASTER):
        return EAL.load_asset(MASTER)
    EAL.make_directory(MAT_DIR)
    m = TOOLS.create_asset("M_JR_ScatterTint", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    setp(m, "two_sided", True)
    setp(m, "used_with_instanced_static_meshes", True)
    white = EAL.load_asset(WHITE)

    def node(cls, x, y, **props):
        e = MEL.create_material_expression(m, cls, x, y)
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def link(a, ao, b, bi):
        if not MEL.connect_material_expressions(a, ao, b, bi):
            warn(f"M_JR_ScatterTint: ligação {a.get_name()}.{ao} -> {b.get_name()}.{bi} falhou")

    tex = node(unreal.MaterialExpressionTextureSampleParameter2D, -1400, 0, parameter_name="BaseTex", texture=white)
    lum_w = node(unreal.MaterialExpressionConstant3Vector, -1400, 260, constant=unreal.LinearColor(0.3, 0.59, 0.11, 1))
    dot = node(unreal.MaterialExpressionDotProduct, -1100, 80)
    link(tex, "RGB", dot, "A")
    link(lum_w, "", dot, "B")
    boost = node(unreal.MaterialExpressionScalarParameter, -1100, 260, parameter_name="TexBoost", default_value=1.8)
    lum = node(unreal.MaterialExpressionMultiply, -850, 120)
    link(dot, "", lum, "A")
    link(boost, "", lum, "B")
    t1 = node(unreal.MaterialExpressionVectorParameter, -1100, -300, parameter_name="Tint",
              default_value=unreal.LinearColor(0.1, 0.6, 0.6, 1))
    t2 = node(unreal.MaterialExpressionVectorParameter, -1100, -140, parameter_name="Tint2",
              default_value=unreal.LinearColor(0.4, 0.3, 0.8, 1))
    rnd = node(unreal.MaterialExpressionPerInstanceRandom, -1100, -460)
    lerp = node(unreal.MaterialExpressionLinearInterpolate, -850, -250)
    link(t1, "", lerp, "A")
    link(t2, "", lerp, "B")
    link(rnd, "", lerp, "Alpha")
    col = node(unreal.MaterialExpressionMultiply, -600, -100)
    link(lerp, "", col, "A")
    link(lum, "", col, "B")
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    glow = node(unreal.MaterialExpressionScalarParameter, -600, 120, parameter_name="EmissiveStrength", default_value=0.0)
    emi = node(unreal.MaterialExpressionMultiply, -350, 60)
    link(col, "", emi, "A")
    link(glow, "", emi, "B")
    MEL.connect_material_property(emi, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    rough = node(unreal.MaterialExpressionScalarParameter, -600, 260, parameter_name="Roughness", default_value=0.85)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, only_if_is_dirty=False)
    log("material M_JR_ScatterTint criado")
    return m


def recolor_mi(key, sm, meta, master):
    """MI_Scatter_<Nome>: textura original da Quaternius (só o brilho) x cor alienígena do índice."""
    path = f"{MAT_DIR}/MI_Scatter_{key[2:] if key.startswith('Q_') else key}"
    if EAL.does_asset_exist(path):
        mi = EAL.load_asset(path)
    else:
        mi = TOOLS.create_asset(path.rsplit("/", 1)[1], MAT_DIR, unreal.MaterialInstanceConstant,
                                unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, master)
    tex = None
    try:
        orig = sm.get_material(0)
        if orig is not None and not orig.get_name().startswith("MI_Scatter_"):
            used = MEL.get_used_textures(orig)
            tex = used[0] if used else None
    except Exception as exc:  # noqa: BLE001
        warn(f"{key}: textura original: {exc}")
    if tex is not None:
        MEL.set_material_instance_texture_parameter_value(mi, "BaseTex", tex)
    else:
        MEL.set_material_instance_scalar_parameter_value(mi, "TexBoost", 1.0)
    t = meta["tint"]
    MEL.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(t[0], t[1], t[2], 1))
    # variação por instância: um pouco mais escuro e puxado para o violeta
    t2 = [min(1.0, t[0] * 0.8 + 0.08), min(1.0, t[1] * 0.75), min(1.0, t[2] * 0.95 + 0.05)]
    MEL.set_material_instance_vector_parameter_value(mi, "Tint2", unreal.LinearColor(t2[0], t2[1], t2[2], 1))
    MEL.set_material_instance_scalar_parameter_value(mi, "EmissiveStrength", float(meta.get("glow", 0.0)))
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi, only_if_is_dirty=False)
    for i in range(max(1, len(sm.get_editor_property("static_materials")))):
        sm.set_material(i, mi)
    return mi


def ism_usage(sm):
    """Marca 'Used with Instanced Static Meshes' no material base (sem isso o jogo empacotado mostra cinza)."""
    try:
        for i in range(max(1, len(sm.get_editor_property("static_materials")))):
            mat = sm.get_material(i)
            base = mat.get_base_material() if mat is not None else None
            if base is not None and not base.get_editor_property("used_with_instanced_static_meshes"):
                base.set_editor_property("used_with_instanced_static_meshes", True)
                MEL.recompile_material(base)
                EAL.save_loaded_asset(base, only_if_is_dirty=False)
                log(f"material {base.get_name()}: uso com instâncias ligado")
    except Exception as exc:  # noqa: BLE001
        warn(f"{sm.get_name()}: uso com instâncias: {exc}")


def prep_user_mesh(sm, name, use_nanite):
    info = {}
    if use_nanite:
        try:
            ns = sm.get_editor_property("nanite_settings")
            if not ns.get_editor_property("enabled"):
                ns.set_editor_property("enabled", True)
                sm.set_editor_property("nanite_settings", ns)
                EAL.save_loaded_asset(sm, only_if_is_dirty=False)
            info["nanite"] = True
        except Exception as exc:  # noqa: BLE001
            warn(f"{name}: Nanite: {exc}")
    elif ADD_LODS_TO_USER:
        try:
            if SMES.get_lod_count(sm) < len(LOD_STEPS):
                opts = unreal.EditorScriptingMeshReductionOptions()
                opts.set_editor_property("auto_compute_lod_screen_size", False)
                opts.set_editor_property("reduction_settings", [
                    unreal.EditorScriptingMeshReductionSettings(p, s) for p, s in LOD_STEPS])
                SMES.set_lods(sm, opts)
                EAL.save_loaded_asset(sm, only_if_is_dirty=False)
            info["lods"] = SMES.get_lod_count(sm)
        except Exception as exc:  # noqa: BLE001
            warn(f"{name}: LODs: {exc}")
    return info


def max_extent_cm(sm):
    b = sm.get_bounding_box()
    return max(b.max.x - b.min.x, b.max.y - b.min.y, b.max.z - b.min.z)


def load_meshes(idx, use_nanite):
    U = here_import("l01_user_dressing")
    Q = here_import("quaternius_lib")
    master = None
    out = {}
    for key, meta in idx["meshes"].items():
        try:
            if meta["kind"] == "user":
                sm = U.mesh(meta["name"])
                if sm is None:
                    warn(f"{key}: malha do usuário não importada (rode import_user_assets.py); lotes pulados")
                    continue
                info = prep_user_mesh(sm, key, use_nanite)
            else:
                sm = Q.load_static(meta["ref"], collision="none")
                if sm is None:
                    warn(f"{key}: Quaternius {meta['ref']} não carregou ({Q.LOG[-1:] if Q.LOG else ''}); lotes pulados")
                    continue
                if master is None:
                    master = master_tint()
                recolor_mi(key, sm, meta, master)
                info = {}
            ism_usage(sm)
            ext = max_extent_cm(sm)
            nom = max(meta["nominal_dims_cm"])
            mul = nom / ext if ext > 1e-3 else 1.0
            if not 0.05 <= mul <= 20.0:
                warn(f"{key}: escala estranha ({mul:.3f}); usando 1")
                mul = 1.0
            info.update({"path": sm.get_path_name().split(".")[0], "ue_max_extent_cm": round(ext, 1),
                         "nominal_max_cm": nom, "scale_mul": round(mul, 4)})
            if abs(mul - 1.0) > 0.05 and meta["kind"] == "user":
                warn(f"{key}: tamanho na Unreal difere do tripo_processed.json (x{mul:.2f}); corrigido na escala")
            R["meshes"][key] = info
            out[key] = (sm, mul)
        except Exception as exc:  # noqa: BLE001
            err(f"malha {key}", exc)
    return out


# ---------------------------------------------------------------- mapa
def open_map():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    cur = world.get_path_name().split(".")[0] if world else ""
    if cur != MAP:
        if not EAL.does_asset_exist(MAP):
            raise RuntimeError(f"mapa {MAP} não existe: rode build_l01.py antes")
        LES.load_level(MAP)
        log("mapa L01_ZombieValley aberto")


def clear_old():
    old = [a for a in ACTORS.get_all_level_actors() if TAG in [str(t) for t in a.tags]]
    for a in old:
        ACTORS.destroy_actor(a)
    log(f"{len(old)} atores de vegetação antigos removidos")
    return len(old)


def fill(idx, meshes):
    cls = scatter_class()
    binp = os.path.join(SRC, idx["file"])
    if not os.path.exists(binp):
        raise FileNotFoundError(f"falta {binp} (rode tools/blender/scatter_l01_v3.py)")
    chunks = {}
    for b in idx["batches"]:
        chunks.setdefault(b["chunk"], []).append(b)
    t0 = time.time()
    with unreal.ScopedSlowTask(len(chunks), "Vegetação L01 (scatter)") as task:
        task.make_dialog(True)
        for name, batches in sorted(chunks.items()):
            if task.should_cancel():
                warn("cancelado pelo usuário")
                break
            task.enter_progress_frame(1, f"Vegetação {name}")
            cx, cy = batches[0]["chunk_center_cm"]
            a = ACTORS.spawn_actor_from_class(cls, unreal.Vector(float(cx), float(cy), 0.0))
            if a is None:
                warn(f"{name}: não criou o ator")
                continue
            a.set_editor_property("tags", [unreal.Name(TAG)])
            a.set_folder_path(FOLDER)
            a.set_actor_label(f"Scatter_{name}")
            for b in batches:
                if b["mesh"] not in meshes:
                    continue
                sm, mul = meshes[b["mesh"]]
                n = a.add_batch_from_file(sm, binp, int(b["first"]), int(b["count"]), float(mul),
                                          float(b["cull_start_cm"]), float(b["cull_end_cm"]),
                                          bool(b["collision"]), bool(b["shadows"]))
                if n != b["count"]:
                    warn(f"{name}/{b['mesh']}: {n} de {b['count']} instâncias")
                R["counts_by_layer"][b["layer"]] = R["counts_by_layer"].get(b["layer"], 0) + n
                R["counts_by_mesh"][b["mesh"]] = R["counts_by_mesh"].get(b["mesh"], 0) + n
            R["actors"] += 1
    R["seconds"] = round(time.time() - t0, 1)
    R["total"] = sum(R["counts_by_layer"].values())
    log(f"{R['actors']} atores, {R['total']} instâncias em {R['seconds']} s")


def run(open_level=True, save=True, use_nanite=None, only_clear=False):
    """Usado também pelo build_l01.py (open_level=False: o mapa já está aberto)."""
    use_nanite = NANITE if use_nanite is None else use_nanite
    if not os.path.exists(INDEX):
        raise FileNotFoundError(f"falta {INDEX} (rode tools/blender/scatter_l01_v3.py)")
    idx = json.load(open(INDEX, encoding="utf-8"))
    R["index_total"] = idx["total"]
    # [A-062] dados gerados com a passada anti-sobreposição (árvore x cristal, pedra x árvore...)?
    R["overlap_pass"] = idx.get("overlap_pass")
    if not idx.get("overlap_pass"):
        warn("l01_scatter_v3 sem a passada anti-sobreposição: gere de novo com tools/blender/scatter_l01_v3.py")
    R["nanite"] = bool(use_nanite)
    if open_level:
        open_map()
    clear_old()
    if not only_clear:
        meshes = load_meshes(idx, use_nanite)
        fill(idx, meshes)
    if save:
        LES.save_current_level()
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("mapa salvo")
    return R


def main():
    args = [a.lower() for a in sys.argv[1:]]
    try:
        run(use_nanite=("nanite" in args) or None, only_clear=("limpar" in args))
        log("pronto. Depois: Build > Build Paths; no Play: stat fps / stat unit")
    except Exception as exc:  # noqa: BLE001
        err("main", exc)
    finally:
        write_report()


def write_report():
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "scatter_l01.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[scatter_l01] fim | instâncias: {R.get('total', 0)} | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")


if __name__ != "scatter_l01":
    main()
