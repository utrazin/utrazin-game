"""(A-078) Lê a pose LOCAL de alguns ossos nas animações dos zumbis (procura escala 0,01 ou posição errada).
py "E:/game/utrazin-game/tools/unreal/diag_zombie_anims.py"  -> reports/diag_zombie_anims.json"""
import json, os, unreal
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
out = {}
AR = unreal.AssetRegistryHelpers.get_asset_registry()
for folder in ("/Game/Characters/Zombies/ZMB_Comum/Anims", "/Game/Characters/Zombies/ZMB_Corredor/Anims",
               "/Game/Characters/Zombies/ZMB_Tanque/Anims", "/Game/Characters/Survivor/Anims", "/Game/Characters/Hero01/Anims"):
    for ad in AR.get_assets_by_path(folder, recursive=True):
        if str(ad.asset_class_path.asset_name) != "AnimSequence":
            continue
        a = ad.get_asset()
        rec = {}
        for bone in ("Hips", "Spine", "LeftUpLeg", "root", "pelvis", "spine_01"):
            try:
                t = unreal.AnimationLibrary.get_bone_pose_for_time(a, bone, 0.0, False)
                p, s = t.translation, t.scale3d
                rec[bone] = [round(p.x, 2), round(p.y, 2), round(p.z, 2), round(s.x, 4), round(s.y, 4), round(s.z, 4)]
            except Exception as e:  # noqa: BLE001
                pass
        try:
            rec["_skel"] = a.get_editor_property("skeleton").get_name()
        except Exception:  # noqa: BLE001
            pass
        out[a.get_path_name()] = rec
json.dump(out, open(os.path.join(REPO, "reports", "diag_zombie_anims.json"), "w", encoding="utf-8"), indent=1)
unreal.log(f"[diag_zombie_anims] {len(out)} animações")
