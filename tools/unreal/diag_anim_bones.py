"""(A-078) Translação LOCAL de todos os ossos (quadro 10) numa animação e na pose de referência."""
import json, os, unreal
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
A = "/Game/Characters/Zombies/ZMB_Comum/Anims/A_Zombie_Idle_Comum"
anim = unreal.load_asset(A)
skel = anim.get_editor_property("skeleton")
ref = unreal.AnimPoseExtensions.get_reference_pose(skel)
out = {}
for b in unreal.AnimPoseExtensions.get_bone_names(ref):
    t = unreal.AnimationLibrary.get_bone_pose_for_frame(anim, b, 10, False)
    r = unreal.AnimPoseExtensions.get_bone_pose(ref, b, unreal.AnimPoseSpaces.LOCAL)
    out[str(b)] = {"anim": [round(t.translation.x, 3), round(t.translation.y, 3), round(t.translation.z, 3), round(t.scale3d.x, 3)],
                   "ref": [round(r.translation.x, 3), round(r.translation.y, 3), round(r.translation.z, 3), round(r.scale3d.x, 3)]}
json.dump(out, open(os.path.join(REPO, "reports", "diag_anim_bones.json"), "w", encoding="utf-8"), indent=1)
unreal.log("[diag_anim_bones] ok")
