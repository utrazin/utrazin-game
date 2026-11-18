"""(A-078) Durante o Play: posição de TODOS os ossos do zumbi mais perto (procura NaN, ossos longe, escala zero)."""
import json, os, math, unreal
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
w = unreal.EditorLevelLibrary.get_game_world()
hero = unreal.GameplayStatics.get_player_pawn(w, 0)
zs = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.JREnemyCharacter)
z = min(zs, key=lambda a: (a.get_actor_location() - hero.get_actor_location()).length())
m = z.get_editor_property("mesh")
base = m.get_world_location()
out = {"zumbi": z.get_name(), "base": [base.x, base.y, base.z], "ossos": {}}
for i in range(m.get_num_bones()):
    n = m.get_bone_name(i)
    t = m.get_socket_transform(n, unreal.RelativeTransformSpace.RTS_COMPONENT)
    p, s = t.translation, t.scale3d
    out["ossos"][str(n)] = [round(p.x, 1), round(p.y, 1), round(p.z, 1), round(s.x, 3), round(s.y, 3), round(s.z, 3)]
ai = m.get_anim_instance()
out["anim_instance"] = ai.get_class().get_path_name() if ai else None
try:
    out["skin_cache"] = str(m.get_editor_property("skin_cache_usage"))
except Exception as e:  # noqa: BLE001
    out["skin_cache"] = str(e)
for k in ("cast_shadow", "visible", "hidden_in_game", "render_in_main_pass", "render_in_depth_pass", "bounds_scale", "use_bounds_from_leader_pose_component", "component_use_fixed_skel_bounds"):
    try:
        out[k] = str(m.get_editor_property(k))
    except Exception as e:  # noqa: BLE001
        out[k] = "?"
json.dump(out, open(os.path.join(REPO, "reports", "diag_zombie_bones_pie.json"), "w", encoding="utf-8"), indent=1)
unreal.log("[diag_zombie_bones_pie] ok")
