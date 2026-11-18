"""Conserta o zumbi (e a sobrevivente) invisível (A-078). Pode rodar de novo.

Causa medida (reports/diag_zombie_refpose.json e diag_zombie_anims.json): os esqueletos dos personagens rigados
(ZMB_Comum, ZMB_Corredor, ZMB_Tanque, NPC_Sobrevivente) vieram do Blender com o osso raiz Hips em ESCALA 100 e os
filhos em metros. As animações retargetadas gravam o Hips com escala 1: o corpo inteiro encolhe 100 vezes
(1,8 cm de altura) e some. O personagem está lá (bate, anda), mas não aparece.
Além disso o retarget gravou os filhos diretos do Hips (Spine, LeftUpLeg, RightUpLeg) em centímetros enquanto o
resto está em metros (como na pose de referência).
Conserto: em cada AnimSequence desses esqueletos, a escala do Hips em todos os quadros vira a escala da pose de
referência (100); e a translação de qualquer osso que esteja mais de 20 vezes maior que a da referência é dividida
por 100 (chave por chave). Rotações ficam como estão.

RODA NO EDITOR (caixa Cmd, sem Play):
  py "E:/game/utrazin-game/tools/unreal/fix_zombie_anim_scale.py"
Relatório: reports/fix_zombie_anim_scale.json. Rode de novo se refizer o setup_zombie_models.py/setup_passenger.py.
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
MESHES = ["/Game/Characters/Zombies/ZMB_Comum/SK_ZMB_Comum", "/Game/Characters/Zombies/ZMB_Corredor/SK_ZMB_Corredor",
          "/Game/Characters/Zombies/ZMB_Tanque/SK_ZMB_Tanque", "/Game/Characters/Survivor/SK_NPC_Sobrevivente"]
ROOT = "Hips"
R = {"esqueletos": {}, "animacoes": {}, "avisos": [], "erros": []}
AR = unreal.AssetRegistryHelpers.get_asset_registry()
EAL = unreal.EditorAssetLibrary


def num_keys(anim):
    for fn in ("get_number_of_keys",):
        try:
            return int(getattr(anim.get_data_model(), fn)())
        except Exception:  # noqa: BLE001
            pass
    return int(unreal.AnimationLibrary.get_num_frames(anim)) + 1


def bone_keys(anim, bone, n):
    pos, rot, scl = [], [], []
    for f in range(n):
        t = unreal.AnimationLibrary.get_bone_pose_for_frame(anim, bone, f, False)
        pos.append(t.translation)
        rot.append(t.rotation)
        scl.append(t.scale3d)
    return pos, rot, scl


def fix_anim(anim, ref, bones):
    """ref: {osso: Transform local da pose de referência}. Devolve o que mudou."""
    n = num_keys(anim)
    changes = {}
    edits = []
    for bone in bones:
        r = ref[bone]
        rlen = r.translation.length()
        # amostra rápida (começo, meio, fim) antes de ler todas as chaves
        probe = [unreal.AnimationLibrary.get_bone_pose_for_frame(anim, bone, f, False) for f in sorted({0, n // 2, n - 1})]
        if bone == ROOT:
            need = any(abs(t.scale3d.x - r.scale3d.x) > 0.01 for t in probe)
        else:
            need = rlen > 1e-5 and any(t.translation.length() > 20.0 * rlen for t in probe)
        if not need:
            continue
        pos, rot, scl = bone_keys(anim, bone, n)
        if bone == ROOT:
            scl = [r.scale3d for _ in scl]
            changes[bone] = "escala da referência"
        else:
            k = 0
            for i, t in enumerate(pos):
                if t.length() > 20.0 * rlen:
                    pos[i] = unreal.Vector(t.x / 100.0, t.y / 100.0, t.z / 100.0)
                    k += 1
            changes[bone] = f"{k} chaves / 100"
        edits.append((bone, pos, rot, scl))
    if not edits:
        return "já estava certa"
    ctrl = anim.controller
    ctrl.open_bracket(unreal.Text("Escala do Hips e translações (A-078)"), True)
    for bone, pos, rot, scl in edits:
        if not ctrl.set_bone_track_keys(bone, pos, rot, scl, True):
            ctrl.close_bracket(True)
            raise RuntimeError(f"set_bone_track_keys recusou {bone}")
    ctrl.close_bracket(True)
    EAL.save_loaded_asset(anim, False)
    return changes


for mp in MESHES:
    sk_mesh = unreal.load_asset(mp)
    if not sk_mesh:
        R["avisos"].append(f"{mp} não existe")
        continue
    skel = sk_mesh.get_editor_property("skeleton")
    pose = unreal.AnimPoseExtensions.get_reference_pose(skel)
    bones = [str(b) for b in unreal.AnimPoseExtensions.get_bone_names(pose)]
    ref = {b: unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.LOCAL) for b in bones}
    ref_scale = ref[ROOT].scale3d
    R["esqueletos"][skel.get_path_name()] = [ref_scale.x, ref_scale.y, ref_scale.z]
    if abs(ref_scale.x - 1.0) < 0.01:
        R["avisos"].append(f"{skel.get_name()}: Hips com escala 1 (nada a fazer)")
        continue
    folder = mp.rsplit("/", 1)[0]
    for ad in AR.get_assets_by_path(folder, recursive=True):
        if str(ad.asset_class_path.asset_name) != "AnimSequence":
            continue
        anim = ad.get_asset()
        try:
            if anim.get_editor_property("skeleton") != skel:
                continue
            R["animacoes"][anim.get_path_name()] = fix_anim(anim, ref, bones)
        except Exception as exc:  # noqa: BLE001
            R["erros"].append({"anim": anim.get_path_name(), "erro": str(exc), "trace": traceback.format_exc()[-600:]})

os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
with open(os.path.join(REPO, "reports", "fix_zombie_anim_scale.json"), "w", encoding="utf-8") as fh:
    json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
unreal.log(f"[fix_zombie_anim_scale] {len(R['animacoes'])} animações | erros: {len(R['erros'])}")
