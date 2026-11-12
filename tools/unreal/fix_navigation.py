"""Habilita navegação para a IA no mapa aberto (mapas World Partition não criam a navmesh sozinhos).
RODA NO EDITOR com L01_Zombies aberto e o jogo parado:
  py "E:/game/utrazin-game/tools/unreal/fix_navigation.py"

- Cria um RecastNavMesh com geração em tempo de execução (Dynamic) se não existir.
- Levanta os inimigos posicionados (a cápsula estava meio enterrada).
"""
import unreal

SUB = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = SUB.get_all_level_actors()
navs = [a for a in actors if isinstance(a, unreal.RecastNavMesh)]
if not navs:
    nav = SUB.spawn_actor_from_class(unreal.RecastNavMesh, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    if nav is None:
        unreal.log_warning("[fix_navigation] não foi possível criar RecastNavMesh por script; "
                           "a navmesh será criada em tempo de execução (DefaultEngine.ini: RuntimeGeneration=Dynamic)")
    else:
        nav.set_actor_label("RecastNavMesh_L01")
        navs = [nav]
for nav in navs:
    try:
        nav.set_editor_property("runtime_generation", unreal.RuntimeGenerationType.DYNAMIC)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning(f"[fix_navigation] runtime_generation: {exc}")
    try:
        nav.set_editor_property("is_world_partitioned", False)
    except Exception:  # noqa: BLE001
        pass
raised = 0
# (inimigos já são posicionados com altura correta por apply_marks.py)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)  # mapas World Partition: salva também os pacotes de atores externos
unreal.log(f"[fix_navigation] navmesh={len(navs)} inimigos levantados={raised}")
