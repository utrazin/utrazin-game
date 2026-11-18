"""(A-078, teste) Durante o Play: leva o herói para 3 m do lado do buggy, olhando para ele."""
import math, unreal
w = unreal.EditorLevelLibrary.get_game_world()
hero = unreal.GameplayStatics.get_player_pawn(w, 0)
cars = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.JRVehiclePawn)
c = min(cars, key=lambda a: (a.get_actor_location() - hero.get_actor_location()).length())
loc = c.get_actor_location()
r = c.get_actor_right_vector()
p = unreal.Vector(loc.x - r.x * 300, loc.y - r.y * 300, loc.z + 150)
hero.set_actor_location(p, False, True)
yaw = math.degrees(math.atan2(loc.y - p.y, loc.x - p.x))
unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.Rotator(0, -10, yaw))
unreal.log(f"[dev_tp_car] {c.get_name()} em {loc}")
