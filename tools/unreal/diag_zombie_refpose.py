"""(A-078) Pose de referência LOCAL dos esqueletos dos zumbis e do herói (procura escala 100 no Hips)."""
import json, os, unreal
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
out = {}
for p in ("/Game/Characters/Zombies/ZMB_Comum/SK_ZMB_Comum", "/Game/Characters/Zombies/ZMB_Corredor/SK_ZMB_Corredor",
          "/Game/Characters/Zombies/ZMB_Tanque/SK_ZMB_Tanque", "/Game/Characters/Survivor/SK_NPC_Sobrevivente"):
    sk = unreal.load_asset(p)
    if not sk:
        out[p] = "não existe"
        continue
    pose = unreal.AnimPoseExtensions.get_reference_pose(sk.get_editor_property("skeleton"))
    rec = {}
    for b in ("Hips", "Spine", "Spine1", "LeftUpLeg", "LeftLeg", "Head"):
        try:
            t = unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.LOCAL)
            rec[b] = [round(t.translation.x, 3), round(t.translation.y, 3), round(t.translation.z, 3),
                      round(t.scale3d.x, 4), round(t.scale3d.y, 4), round(t.scale3d.z, 4),
                      round(t.rotation.rotator().roll, 1), round(t.rotation.rotator().pitch, 1), round(t.rotation.rotator().yaw, 1)]
        except Exception as e:  # noqa: BLE001
            rec[b] = str(e)
    out[p] = rec
json.dump(out, open(os.path.join(REPO, "reports", "diag_zombie_refpose.json"), "w", encoding="utf-8"), indent=1)
unreal.log("[diag_zombie_refpose] ok")
