"""[Remap F1] Diagnóstico da arena DURANTE o Play: zumbi sem levar tiro, duro/deslizando, tiro torto.
Rode com o jogo rodando na arena (zumbis à vista), na caixa Cmd (Python):
  py "E:/game/utrazin-game/tools/unreal/diag_arena_pie.py"
Só lê. Relatório: reports/diag_arena_pie.json"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
R = {"zumbis": [], "tracos": [], "erros": []}
VIS = unreal.CollisionChannel.ECC_VISIBILITY


def v(x):
    return [round(x.x, 1), round(x.y, 1), round(x.z, 1)]


def hit_info(w, start, end, ignore):
    hit = unreal.SystemLibrary.line_trace_single(w, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                                 unreal.DrawDebugTrace.FOR_DURATION, True)
    if hit is None:
        return None
    t = hit.to_tuple()
    # (blocking, initial_overlap, time, distance, location, impact_point, normal, impact_normal, phys_mat, hit_actor, hit_component, hit_bone_name, ...)
    actor = t[9]
    comp = t[10]
    return {"acertou": bool(t[0]), "ator": actor.get_name() if actor else None,
            "componente": comp.get_name() if comp else None, "osso": str(t[11]), "ponto": v(t[5])}


def comp_info(c):
    out = {"nome": c.get_name()}
    for k, f in (("perfil", lambda: str(c.get_collision_profile_name())),
                 ("colisao", lambda: str(c.get_collision_enabled())),
                 ("resposta_visibility", lambda: str(c.get_collision_response_to_channel(VIS))),
                 ("tick", lambda: c.is_component_tick_enabled())):
        try:
            out[k] = f()
        except Exception as exc:  # noqa: BLE001
            out[k] = f"? {exc}"
    return out


try:
    w = unreal.EditorLevelLibrary.get_game_world()
    R["mundo"] = w.get_path_name() if w else None
    hero = unreal.GameplayStatics.get_player_pawn(w, 0)
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    cam = unreal.GameplayStatics.get_player_camera_manager(w, 0)
    cam_loc = cam.get_camera_location()
    cam_rot = cam.get_camera_rotation()
    R["camera"] = {"pos": v(cam_loc), "rot": [round(cam_rot.pitch, 1), round(cam_rot.yaw, 1)]}
    R["pc"] = pc.get_class().get_name() if pc else None
    R["hud"] = pc.get_hud().get_class().get_name() if pc and pc.get_hud() else None
    R["dilatacao"] = unreal.GameplayStatics.get_global_time_dilation(w)
    fwd = cam_rot.get_forward_vector()
    R["tracos"].append({"tipo": "centro da tela", **(hit_info(w, cam_loc, cam_loc + fwd * 10000.0, [hero]) or {})})
    actors = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.JREnemyCharacter) if w else []
    R["total"] = len(actors)
    hp = hero.get_actor_location() if hero else cam_loc
    actors = sorted(actors, key=lambda a: (a.get_actor_location() - hp).length())
    for a in actors[:4]:
        z = {"nome": a.get_name(), "pos": v(a.get_actor_location()), "vel": v(a.get_velocity()),
             "dist_m": round((a.get_actor_location() - hp).length() / 100, 1)}
        cap = a.get_editor_property("capsule_component")
        m = a.get_editor_property("mesh")
        z["capsula"] = comp_info(cap)
        z["malha"] = comp_info(m)
        try:
            sk = m.get_editor_property("skeletal_mesh_asset")
            z["malha"]["asset"] = sk.get_path_name() if sk else None
            pa = sk.get_editor_property("physics_asset") if sk else None
            z["malha"]["physics_asset"] = pa.get_path_name() if pa else None
            ai = m.get_anim_instance()
            z["malha"]["anim_instance"] = ai.get_class().get_name() if ai else None
            z["malha"]["modo_anim"] = str(m.get_editor_property("animation_mode"))
            z["malha"]["pausado"] = m.get_editor_property("pause_anims")
            z["malha"]["no_skeleton_update"] = m.get_editor_property("no_skeleton_update")
            o, e, r = unreal.SystemLibrary.get_component_bounds(m)
            z["malha"]["bounds_origem"] = v(o)
            z["malha"]["bounds_ext"] = v(e)
            z["malha"]["renderizado"] = m.was_recently_rendered(0.2)
        except Exception as exc:  # noqa: BLE001
            z["malha"]["erro"] = str(exc)
        try:
            cm = a.get_editor_property("character_movement")
            z["movimento"] = {"modo": str(cm.get_editor_property("movement_mode")),
                              "max_walk": cm.get_editor_property("max_walk_speed"),
                              "accel": v(cm.get_current_acceleration())}
        except Exception as exc:  # noqa: BLE001
            z["movimento"] = str(exc)
        target = a.get_actor_location() + unreal.Vector(0, 0, 40)
        z["traco_camera_ate_peito"] = hit_info(w, cam_loc, target + (target - cam_loc) * 0.2, [hero])
        R["zumbis"].append(z)
except Exception:  # noqa: BLE001
    R["erros"].append(traceback.format_exc()[-1500:])
os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
with open(os.path.join(REPO, "reports", "diag_arena_pie.json"), "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=1, default=str)
unreal.log(f"[diag_arena_pie] {R.get('total')} zumbis; relatório em reports/diag_arena_pie.json")
