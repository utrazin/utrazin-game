"""Diagnóstico (SOMENTE LEITURA) dos zumbis invisíveis. Roda no editor:
  py "E:/game/utrazin-game/tools/unreal/diag_zombie_visibility.py"
Relatório: reports/diag_zombie_visibility.json  (cole o campo "veredito" na conversa)

Não altera nenhum asset. Para cada BP de zumbi confere: malha, tamanho (bounds), esqueleto da malha
x esqueleto do ABP, materiais (vazio ou sem textura), Physics Asset e flags de visibilidade.
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REPORT = os.path.join(REPO, "reports", "diag_zombie_visibility.json")
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
KINDS = ("Melee", "Archer", "Gunner", "Elite")
R = {"bps": {}, "veredito": [], "erros": []}


def safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        R["erros"].append(f"{type(exc).__name__}: {exc}")
        return default


def pkg(o):
    if o is None:
        return None
    p = o if isinstance(o, str) else o.get_path_name()
    p = p.split("'")[1] if "'" in p else p
    return p.split(".")[0]


def bp_cdo(path):
    bp = EAL.load_asset(path)
    if bp is None:
        return None, None
    return bp, unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))


def used_textures(mi):
    base = mi
    while base is not None and isinstance(base, unreal.MaterialInstance):
        base = base.get_editor_property("parent")
    if base is None:
        return []
    return [pkg(t) for t in (safe(lambda: MEL.get_used_textures(base), []) or [])]


def inspect(kind):
    out = {"problemas": []}
    path = f"/Game/Enemies/BP_Enemy_Zombie{kind}"
    bp, cdo = bp_cdo(path)
    if cdo is None:
        out["problemas"].append(f"{path} não existe")
        return out
    m = cdo.get_editor_property("mesh")
    mesh = m.get_editor_property("skeletal_mesh_asset")
    out["malha"] = pkg(mesh)
    out["abp"] = pkg(m.get_editor_property("anim_class"))
    out["flags"] = {
        k: safe(lambda k=k: m.get_editor_property(k))
        for k in ("visible", "hidden_in_game", "render_in_main_pass", "owner_no_see", "cast_shadow",
                  "bounds_scale", "visibility_based_anim_tick_option")
    }
    sc = m.get_editor_property("relative_scale3d")
    loc = m.get_editor_property("relative_location")
    out["escala_malha"] = [sc.x, sc.y, sc.z]
    out["posicao_malha"] = [loc.x, loc.y, loc.z]
    cap = cdo.get_editor_property("capsule_component")
    out["capsula"] = {"raio": cap.get_editor_property("capsule_radius"),
                      "meia_altura": cap.get_editor_property("capsule_half_height")}
    if mesh is None:
        out["problemas"].append("BP sem malha")
        return out
    b = safe(lambda: mesh.get_bounds())
    if b is not None:
        e = b.box_extent
        out["bounds"] = {"extensao_cm": [round(e.x, 1), round(e.y, 1), round(e.z, 1)],
                         "origem": [round(b.origin.x, 1), round(b.origin.y, 1), round(b.origin.z, 1)]}
        biggest = max(e.x, e.y, e.z)
        if biggest < 5:
            out["problemas"].append(f"malha minúscula (maior meia-extensão {biggest:.2f} cm): escala de importação errada")
        if biggest > 600:
            out["problemas"].append(f"malha gigante (maior meia-extensão {biggest:.0f} cm)")
    skel = safe(lambda: mesh.get_editor_property("skeleton"))
    out["esqueleto_malha"] = pkg(skel)
    abp_cls = m.get_editor_property("anim_class")
    abp_asset = EAL.load_asset(pkg(abp_cls)) if abp_cls else None
    if abp_asset is None:
        out["problemas"].append("BP sem AnimBlueprint")
    else:
        tskel = safe(lambda: abp_asset.get_editor_property("target_skeleton"))
        out["esqueleto_abp"] = pkg(tskel)
        if tskel is not None and skel is not None and pkg(tskel) != pkg(skel):
            out["problemas"].append("ABP é de OUTRO esqueleto (a malha não anima certo; pose quebrada pode sumir o modelo)")
    out["physics_asset"] = pkg(safe(lambda: mesh.get_editor_property("physics_asset")))
    if out["physics_asset"] is None:
        out["problemas"].append("sem Physics Asset (ragdoll e bounds de física)")
    mats = []
    for sm in mesh.get_editor_property("materials"):
        mi = sm.get_editor_property("material_interface")
        tex = used_textures(mi) if mi else []
        mats.append({"slot": str(sm.get_editor_property("material_slot_name")), "material": pkg(mi), "texturas": tex})
        if mi is None:
            out["problemas"].append(f"slot {mats[-1]['slot']} SEM material (some ou fica padrão)")
        elif not tex:
            out["problemas"].append(f"slot {mats[-1]['slot']}: material {pkg(mi)} sem textura detectada")
    out["materiais"] = mats
    ov = [pkg(x) for x in m.get_editor_property("override_materials")]
    out["override_materials"] = ov
    return out


def main():
    for kind in KINDS:
        try:
            R["bps"][kind] = inspect(kind)
        except Exception:  # noqa: BLE001
            R["bps"][kind] = {"problemas": ["falha ao inspecionar"], "trace": traceback.format_exc()}
    for kind, d in R["bps"].items():
        for p in d.get("problemas", []):
            R["veredito"].append(f"{kind}: {p}")
    if not R["veredito"]:
        R["veredito"].append("Nenhum problema nos assets. A causa está na execução (veja o Output Log durante o jogo) "
                             "ou no ABP em tempo de execução.")
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log("diag_zombie_visibility: " + " | ".join(R["veredito"]))


main()
