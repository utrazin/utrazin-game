"""Diagnóstico do zumbi DURANTE o Play (A-078): rode com o jogo rodando (Play no editor), na caixa Cmd:
  py "E:/game/utrazin-game/tools/unreal/diag_zombie_pie.py"
Só lê. Relatório: reports/diag_zombie_pie.json (posição, bounds reais, ossos, animação, material, visível)."""
import json
import os
import traceback

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
R = {"zumbis": [], "erros": []}


def v(x):
    return [round(x.x, 1), round(x.y, 1), round(x.z, 1)]


try:
    w = unreal.EditorLevelLibrary.get_game_world()
    R["mundo"] = w.get_path_name() if w else None
    actors = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.JREnemyCharacter) if w else []
    R["total"] = len(actors)
    hero = unreal.GameplayStatics.get_player_pawn(w, 0)
    hp = hero.get_actor_location() if hero else None
    actors = sorted(actors, key=lambda a: (a.get_actor_location() - hp).length() if hp else 0)
    for a in actors[:6]:
        m = a.get_editor_property("mesh")
        z = {"nome": a.get_actor_label() if hasattr(a, "get_actor_label") else a.get_name(),
             "classe": a.get_class().get_name(), "pos": v(a.get_actor_location()),
             "dist_heroi_m": round((a.get_actor_location() - hp).length() / 100, 1) if hp else None,
             "ator_escondido": a.is_hidden_ed() if hasattr(a, "is_hidden_ed") else None}
        try:
            z["hidden_in_game_ator"] = a.get_editor_property("hidden")
        except Exception as exc:  # noqa: BLE001
            z["hidden_in_game_ator"] = str(exc)
        if m:
            z["malha"] = m.get_editor_property("skeletal_mesh_asset").get_path_name() if m.get_editor_property("skeletal_mesh_asset") else None
            z["visivel"] = m.is_visible()
            z["hidden_in_game"] = m.get_editor_property("hidden_in_game")
            z["escala_mundo"] = v(m.get_world_scale())
            z["pos_mundo"] = v(m.get_world_location())
            o, e, r = unreal.SystemLibrary.get_component_bounds(m)
            z["bounds_origem"] = v(o)
            z["bounds_ext"] = v(e)
            ai = m.get_anim_instance()
            z["anim"] = ai.get_class().get_name() if ai else None
            z["modo_anim"] = str(m.get_editor_property("animation_mode"))
            ossos = {}
            for b in ("root", "mixamorig:Hips", "mixamorig_Hips", "Hips", "pelvis", "mixamorig:Head", "Head"):
                try:
                    if m.get_bone_index(b) >= 0:
                        t = m.get_socket_transform(b, unreal.RelativeTransformSpace.RTS_WORLD)
                        ossos[b] = {"pos": v(t.translation), "escala": v(t.scale3d)}
                except Exception:  # noqa: BLE001
                    pass
            z["ossos"] = ossos
            z["num_ossos"] = m.get_num_bones()
            z["lod"] = m.get_editor_property("forced_lod_model") if hasattr(m, "get_editor_property") else None
            z["recentemente_renderizado"] = m.was_recently_rendered(0.2)
            mats = []
            for i in range(m.get_num_materials()):
                mi = m.get_material(i)
                mats.append(mi.get_path_name() if mi else None)
            z["materiais"] = mats
        R["zumbis"].append(z)
except Exception as exc:  # noqa: BLE001
    R["erros"].append(traceback.format_exc()[-1500:])
os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
with open(os.path.join(REPO, "reports", "diag_zombie_pie.json"), "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=1, default=str)
unreal.log(f"[diag_zombie_pie] {R.get('total')} zumbis; relatório em reports/diag_zombie_pie.json")
