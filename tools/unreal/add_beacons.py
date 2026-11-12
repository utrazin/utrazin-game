"""Coloca "faróis" (colunas coloridas altas, sem colisão) para achar os pontos da fase no greybox.
RODA NO EDITOR com L01_Zombies aberto e o jogo parado:
  py "E:/game/utrazin-game/tools/unreal/add_beacons.py"

Amarelo = checkpoint de transição | Vermelho = horda | Verde = resgate.
Idempotente: se os faróis já existem, só os move para cima dos alvos (rode de novo após mover pontos).
"""
import unreal

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
SUB = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
BASE = "/Game/LevelPrototyping/Materials/M_FlatCol"
CYL = EAL.load_asset("/Game/LevelPrototyping/Meshes/SM_Cylinder")
COLORS = {"Yellow": unreal.LinearColor(1.0, 0.8, 0.0, 1), "Red": unreal.LinearColor(1.0, 0.05, 0.05, 1),
          "Green": unreal.LinearColor(0.1, 1.0, 0.2, 1)}


def material(name, color):
    path = f"/Game/Developer/Greybox/MI_Beacon_{name}"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    EAL.make_directory("/Game/Developer/Greybox")
    mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        f"MI_Beacon_{name}", "/Game/Developer/Greybox", unreal.MaterialInstanceConstant,
        unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, EAL.load_asset(BASE))
    for p in MEL.get_vector_parameter_names(EAL.load_asset(BASE)):
        MEL.set_material_instance_vector_parameter_value(mi, p, color)
    EAL.save_loaded_asset(mi)
    return mi


actors = SUB.get_all_level_actors()
existing = {a.get_actor_label() for a in actors}
targets = []
for a in actors:
    label = a.get_actor_label()
    if label == "CP_Transition":
        targets.append((a, "Yellow"))
    elif label == "HordeDirector_Final":
        targets.append((a, "Red"))
    elif label == "Rescue_Victim01":
        targets.append((a, "Green"))
for actor, color in targets:
    beacon_label = f"Beacon_{actor.get_actor_label()}"
    loc = actor.get_actor_location()
    old = [a for a in actors if a.get_actor_label() == beacon_label]
    if old:
        # Já existe: só reposiciona em cima do alvo (os alvos podem ter sido movidos depois).
        for o in old:
            o.detach_from_actor(unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD,
                                unreal.DetachmentRule.KEEP_WORLD)
            o.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z), False, False)
        unreal.log(f"[add_beacons] {beacon_label} reposicionado em {loc}")
        continue
    b = SUB.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(loc.x, loc.y, loc.z), unreal.Rotator(0, 0, 0))
    b.set_actor_label(beacon_label)
    comp = b.static_mesh_component
    comp.set_static_mesh(CYL)
    comp.set_material(0, material(color, COLORS[color]))
    comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    b.set_actor_scale3d(unreal.Vector(0.6, 0.6, 25.0))
    unreal.log(f"[add_beacons] {beacon_label} ({color}) em {loc}")
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)  # mapas World Partition: salva também os pacotes de atores externos
