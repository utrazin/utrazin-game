"""(A-078, teste) Durante o Play: leva o herói para 1,6 m na frente do baú mais perto ainda fechado."""
import math, unreal
w = unreal.EditorLevelLibrary.get_game_world()
hero = unreal.GameplayStatics.get_player_pawn(w, 0)
chests = [c for c in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.JRLootChest)]
c = min(chests, key=lambda a: (a.get_actor_location() - hero.get_actor_location()).length())
loc = c.get_actor_location()
f = c.get_actor_forward_vector()
p = unreal.Vector(loc.x + f.x * 160, loc.y + f.y * 160, loc.z + 120)
hero.set_actor_location(p, False, True)
yaw = math.degrees(math.atan2(loc.y - p.y, loc.x - p.x))
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pc.set_control_rotation(unreal.Rotator(0, -15, yaw))
unreal.log(f"[dev_tp_chest] {c.get_actor_label() if hasattr(c,'get_actor_label') else c.get_name()} em {loc}")
