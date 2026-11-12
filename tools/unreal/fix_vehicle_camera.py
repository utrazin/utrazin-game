"""Ajusta a câmera do BP_Vehicle_SUV (o Offroad é grande; a câmera ficava baixa, colando no chão).
RODA NO EDITOR:  py "E:/game/utrazin-game/tools/unreal/fix_vehicle_camera.py"
"""
import unreal

EAL = unreal.EditorAssetLibrary
bp = EAL.load_asset("/Game/Vehicles/SUV/BP_Vehicle_SUV")
cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
arm = cdo.get_editor_property("spring_arm")
arm.set_editor_property("relative_location", unreal.Vector(0, 0, 200))  # origem do braço acima do chão
arm.set_editor_property("target_arm_length", 900.0)
arm.set_editor_property("socket_offset", unreal.Vector(0, 0, 120))
arm.set_editor_property("target_offset", unreal.Vector(0, 0, 0))
bp.modify()
EAL.save_loaded_asset(bp, False)
unreal.log("[fix_vehicle_camera] câmera ajustada: origem +2 m, braço 9 m, offset +1,2 m")
