"""Garante que cada zumbi (Blueprint e instâncias no mapa) tenha seu Archetype (DA_Enemy_*).
RODA NO EDITOR com L01_Zombies aberto e o jogo parado:
  py "E:/game/utrazin-game/tools/unreal/fix_archetypes.py"
"""
import unreal

EAL = unreal.EditorAssetLibrary
SUB = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
PAIRS = {
    "BP_Enemy_ZombieMelee": "/Game/Data/DA_Enemy_ZombieMelee",
    "BP_Enemy_ZombieArcher": "/Game/Data/DA_Enemy_ZombieArcher",
    "BP_Enemy_ZombieGunner": "/Game/Data/DA_Enemy_ZombieGunner",
}
fixed_cdo = fixed_inst = 0
for bp_name, da_path in PAIRS.items():
    da = EAL.load_asset(da_path)
    bp = EAL.load_asset(f"/Game/Enemies/{bp_name}")
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    before = cdo.get_editor_property("archetype")
    unreal.log(f"[fix_archetypes] CDO {bp_name}: archetype antes = {before}")
    if before is None:
        cdo.set_editor_property("archetype", da)
        bp.modify()
        EAL.save_loaded_asset(bp, False)
        fixed_cdo += 1
    for a in SUB.get_all_level_actors():
        if a.get_class().get_name().startswith(bp_name):
            if a.get_editor_property("archetype") is None:
                a.modify()
                a.set_editor_property("archetype", da)
                fixed_inst += 1
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.log(f"[fix_archetypes] CDOs corrigidos={fixed_cdo} instâncias corrigidas={fixed_inst}")
