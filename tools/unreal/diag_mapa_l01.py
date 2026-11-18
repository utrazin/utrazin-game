"""Diagnóstico da L01 (A-063), SOMENTE LEITURA: não muda nem salva nada. Pode rodar quantas vezes quiser.

RODA NO EDITOR (caixa Cmd, sem Play):
  py "E:/game/utrazin-game/tools/unreal/diag_mapa_l01.py"
Relatório: reports/diag_mapa_l01.json (o "resumo" no topo; listas limitadas a LIMIT exemplos).

Confere, em todos os atores do mapa aberto (a vegetação instanciada fica de fora, ela tem relatório próprio):
 - sem_textura: malha com material sem nenhuma textura (padrão da engine, Quaternius branco...) = item 2 e 5;
 - restos_antigos: atores fora das pastas e tags da v3 (L01/..., Ceu, AlienSkyGen, L01Gen, L01Scatter) = item 2;
 - no_ar: malha cuja base está a mais de AIR_CM do chão embaixo dela, e itens (JRPickup) acima do chão = 5 e 9;
 - solido_sem_colisao: malha que bloqueia (perfil com colisão) mas não tem NENHUMA forma de colisão = item 1;
 - brilho: materiais com emissivo forte, quem usa M_L01_Glow e luzes fortes ou dentro de malhas = item 8;
 - ceu: materiais com "Is Sky" = item 15.
"""
import json
import os
import traceback
from collections import Counter, defaultdict
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
MAP = "/Game/Levels/L01_ZombieValley/L01_ZombieValley"
LIMIT = 80
AIR_CM = 30.0
BRIGHT_CD = 400.0                  # luz acima disso (candelas) é suspeita com a exposição fixa
BRIGHT_UNITLESS = 5000.0
EMISSIVE_PARAMS = ("EmissiveStrength", "GlowStrength", "Intensity", "Brightness", "StarBrightness")
V3_FOLDERS = ("L01/", "Ceu")
V3_TAGS = {"L01Gen", "L01Scatter", "AlienSkyGen"}
ENGINE_FLAT = ("/Engine/BasicShapes/BasicShapeMaterial", "/Engine/EngineMaterials/WorldGridMaterial",
               "/Engine/EngineMaterials/DefaultMaterial")
VERTEX_COLOR_OK = ("M_L01_VertexColor", "M_L01_Glow")   # cor por vértice de propósito (blockout L01)

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
R = {"time": datetime.now().isoformat(), "somente_leitura": True, "resumo": {}, "sem_textura": [],
     "restos_antigos": [], "no_ar": [], "itens_altura": [], "solido_sem_colisao": [], "brilho": {},
     "ceu": [], "warnings": [], "errors": []}
_tex_cache = {}


def warn(m):
    R["warnings"].append(m)


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-600:]})
    unreal.log_error(f"[diag_mapa_l01] {where}: {exc}")


def path_of(o):
    return o.get_path_name().split(".")[0] if o else ""


def base_material(mat):
    try:
        b = mat.get_base_material()
        return b or mat
    except Exception:  # noqa: BLE001
        return mat


def textures_of(mat):
    """Quantas texturas o material usa (MaterialInstance: as do pai + parâmetros de textura preenchidos)."""
    key = path_of(mat)
    if key in _tex_cache:
        return _tex_cache[key]
    n = 0
    base = base_material(mat)
    try:
        n += len(MEL.get_used_textures(base))
    except Exception:  # noqa: BLE001
        pass
    if isinstance(mat, unreal.MaterialInstance):
        try:
            for name in MEL.get_texture_parameter_names(base):
                if MEL.get_material_instance_texture_parameter_value(mat, name):
                    n += 1
        except Exception:  # noqa: BLE001
            pass
    _tex_cache[key] = n
    return n


def ground_below(world, x, y, z_top, ignore):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, z_top), unreal.Vector(x, y, z_top - 5000.0),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                                 unreal.DrawDebugTrace.NONE, True)
    if isinstance(hit, tuple):
        hit = hit[-1]
    t = hit.to_tuple() if hit else None
    return t[5].z if t and t[0] else None


def main():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    cur = path_of(world)
    R["mapa"] = cur
    if cur != MAP:
        warn(f"mapa aberto é {cur}, não {MAP}: o diagnóstico vale para o mapa aberto")
    actors = ACTORS.get_all_level_actors()
    folders, notex_by_mesh, glow_users, emissive = Counter(), Counter(), Counter(), {}
    nocol_by_mesh = Counter()
    old_by_folder = Counter()
    n_mesh_actors = 0
    for a in actors:
        try:
            label = a.get_actor_label()
            folder = str(a.get_folder_path())
            tags = {str(t) for t in a.tags}
            folders[folder.split("/")[0] + ("/" + folder.split("/")[1] if folder.count("/") else "")] += 1
            if "L01Scatter" in tags:
                continue
            # ---- restos antigos
            is_v3 = folder.startswith(V3_FOLDERS) or bool(tags & V3_TAGS)
            comps = a.get_components_by_class(unreal.StaticMeshComponent)
            if not is_v3 and comps and not isinstance(a, (unreal.WorldSettings,)):
                old_by_folder[folder or "(sem pasta)"] += 1
                if len(R["restos_antigos"]) < LIMIT:
                    sm0 = comps[0].get_editor_property("static_mesh")
                    R["restos_antigos"].append({"ator": label, "pasta": folder, "tags": sorted(tags),
                                                "malha": path_of(sm0)})
            # ---- itens: altura do chão
            if hasattr(unreal, "JRPickup") and isinstance(a, unreal.JRPickup):
                loc = a.get_actor_location()
                g = ground_below(world, loc.x, loc.y, loc.z + 60.0, [a])
                if g is not None and len(R["itens_altura"]) < LIMIT:
                    R["itens_altura"].append({"ator": label, "acima_do_chao_cm": round(loc.z - g, 1)})
            for c in comps:
                sm = c.get_editor_property("static_mesh")
                if sm is None:
                    continue
                mname = path_of(sm)
                if isinstance(a, unreal.StaticMeshActor):
                    n_mesh_actors += 1
                # ---- materiais: sem textura, brilho
                for mat in c.get_materials():
                    if mat is None:
                        notex_by_mesh[mname + " | (sem material)"] += 1
                        continue
                    mp = path_of(mat)
                    bname = path_of(base_material(mat))
                    if bname.endswith("M_L01_Glow"):
                        glow_users[mname] += 1
                    if any(bname.endswith(v) for v in VERTEX_COLOR_OK):
                        continue
                    if bname in ENGINE_FLAT or textures_of(mat) == 0:
                        notex_by_mesh[f"{mname} | {mp}"] += 1
                    if isinstance(mat, unreal.MaterialInstance) and mp not in emissive:
                        vals = {}
                        for p in EMISSIVE_PARAMS:
                            try:
                                v = MEL.get_material_instance_scalar_parameter_value(mat, p)
                                if v:
                                    vals[p] = round(v, 3)
                            except Exception:  # noqa: BLE001
                                pass
                        emissive[mp] = vals
                # ---- colisão: bloqueia mas sem forma nenhuma
                if isinstance(a, unreal.StaticMeshActor):
                    prof = str(c.get_collision_profile_name())
                    if prof != "NoCollision" and c.get_collision_enabled() != unreal.CollisionEnabled.NO_COLLISION:
                        try:
                            cnt = SMES.get_simple_collision_count(sm)
                            flag = sm.get_editor_property("body_setup").get_editor_property("collision_trace_flag")
                        except Exception:  # noqa: BLE001
                            cnt, flag = -1, None
                        if cnt == 0 and flag != unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
                            nocol_by_mesh[mname] += 1
                # ---- no ar (só atores de malha soltos)
                if isinstance(a, unreal.StaticMeshActor) and len(R["no_ar"]) < LIMIT:
                    o, e = a.get_actor_bounds(False)
                    if e.z < 2000:   # pula terreno e peças gigantes
                        bottom = o.z - e.z
                        g = ground_below(world, o.x, o.y, bottom + 5.0, [a])
                        if g is not None and bottom - g > AIR_CM:
                            R["no_ar"].append({"ator": label, "pasta": folder, "malha": mname,
                                               "altura_cm": round(bottom - g, 1),
                                               "loc": [round(o.x), round(o.y), round(bottom)]})
        except Exception as exc:  # noqa: BLE001
            err(f"ator {a}", exc)
    R["sem_textura"] = [{"malha_material": k, "atores": v} for k, v in notex_by_mesh.most_common(LIMIT)]
    R["solido_sem_colisao"] = [{"malha": k, "atores": v} for k, v in nocol_by_mesh.most_common(LIMIT)]
    R["brilho"]["usam_M_L01_Glow"] = [{"malha": k, "componentes": v} for k, v in glow_users.most_common(LIMIT)]
    R["brilho"]["materiais_emissivos"] = {k: v for k, v in emissive.items() if v}
    # ---- luzes
    lights = []
    for a in actors:
        if not isinstance(a, unreal.Light):
            continue
        try:
            lc = a.get_component_by_class(unreal.LocalLightComponent)
            if lc is None:
                continue
            inten = lc.get_editor_property("intensity")
            units = str(lc.get_editor_property("intensity_units"))
            strong = inten > (BRIGHT_CD if "CANDELA" in units.upper() else BRIGHT_UNITLESS)
            loc = a.get_actor_location()
            inside = []
            for b in actors:
                if b is a or not isinstance(b, unreal.StaticMeshActor):
                    continue
                o, e = b.get_actor_bounds(False)
                if e.z > 2000:
                    continue
                if abs(loc.x - o.x) < e.x and abs(loc.y - o.y) < e.y and abs(loc.z - o.z) < e.z:
                    inside.append(b.get_actor_label())
            lights.append({"luz": a.get_actor_label(), "intensidade": round(inten, 1), "unidade": units,
                           "forte": strong, "dentro_de": inside[:5]})
        except Exception as exc:  # noqa: BLE001
            err(f"luz {a.get_actor_label()}", exc)
    R["brilho"]["luzes"] = lights
    # ---- céu: materiais "Is Sky"
    for p in EAL.list_assets("/Game", recursive=True, include_folder=False):
        if "/Sky" not in p and "Sky" not in p.split("/")[-1]:
            continue
        try:
            asset = EAL.load_asset(p.split(".")[0])
            if isinstance(asset, unreal.Material) and asset.get_editor_property("is_sky"):
                R["ceu"].append(path_of(asset))
        except Exception:  # noqa: BLE001
            pass
    R["resumo"] = {
        "atores": len(actors), "atores_de_malha": n_mesh_actors,
        "malhas_sem_textura": len(notex_by_mesh), "restos_antigos": sum(old_by_folder.values()),
        "restos_por_pasta": dict(old_by_folder.most_common(20)),
        "no_ar": len(R["no_ar"]), "itens_acima_de_30cm": sum(1 for i in R["itens_altura"] if i["acima_do_chao_cm"] > 30),
        "malhas_solidas_sem_colisao": len(nocol_by_mesh), "malhas_com_M_L01_Glow": len(glow_users),
        "luzes_fortes": sum(1 for x in lights if x["forte"]), "luzes_dentro_de_malha": sum(1 for x in lights if x["dentro_de"]),
        "materiais_is_sky": len(R["ceu"]), "pastas": dict(folders.most_common(30)),
    }


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "diag_mapa_l01.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[diag_mapa_l01] fim | {json.dumps(R['resumo'], ensure_ascii=False, default=str)[:400]}")
