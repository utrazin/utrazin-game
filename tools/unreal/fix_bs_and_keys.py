"""Corrige os BS_Idle_Walk_Run_HNN (amostras apontando para animações que nunca foram salvas)
e garante a tecla de sacar arma (1 / Q) no IMC_JR_Combat.

RODA NO EDITOR (caixa Cmd):
  py "E:/game/utrazin-game/tools/unreal/fix_bs_and_keys.py"
Relatório: reports/fix_bs_and_keys.json
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
R = {"steps": [], "errors": [], "check": {}}
SRC_BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run"


def log(m):
    R["steps"].append(m)
    unreal.log(f"[fix_bs] {m}")


def sample_names(bs):
    out = []
    for s in bs.get_editor_property("sample_data"):
        a = s.get_editor_property("animation")
        out.append(a.get_path_name() if a else None)
    return out


def fix_bs(nn):
    src = EAL.load_asset(SRC_BS)
    src_samples = src.get_editor_property("sample_data")
    path = f"/Game/Characters/Hero{nn}/Anims/BS_Idle_Walk_Run_H{nn}"
    bs = EAL.load_asset(path)
    skel = EAL.load_asset(f"/Game/Characters/Hero{nn}/Mesh/SK_Hero{nn}").skeleton
    samples = bs.get_editor_property("sample_data")
    if len(samples) != len(src_samples):
        raise RuntimeError(f"Hero{nn}: {len(samples)} amostras vs {len(src_samples)} no BS original")
    new = []
    for s, ss in zip(samples, src_samples):
        src_anim = ss.get_editor_property("animation")
        name = src_anim.get_name()
        target = f"/Game/Characters/Hero{nn}/Anims/{name}_H{nn}"
        anim = EAL.load_asset(target)
        if anim is None or anim.get_editor_property("skeleton") != skel:
            raise RuntimeError(f"Hero{nn}: animação ausente ou de outro esqueleto: {target}")
        s.set_editor_property("animation", anim)
        new.append(s)
    bs.modify()
    bs.set_editor_property("sample_data", new)
    try:
        bs.post_edit_change()
    except Exception:  # noqa: BLE001
        pass
    EAL.save_loaded_asset(bs, only_if_is_dirty=False)
    R["check"][f"H{nn}"] = sample_names(EAL.load_asset(path))
    log(f"Hero{nn}: {len(new)} amostras religadas e salvas")


def mappings(imc):
    return [(m.get_editor_property("action").get_name() if m.get_editor_property("action") else None,
             str(m.get_editor_property("key").get_editor_property("key_name")))
            for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings")]


def fix_keys():
    imc = EAL.load_asset("/Game/Core/Input/IMC_JR_Combat")
    ia = EAL.load_asset("/Game/Core/Input/IA_ToggleWeapon")
    have = {k for a, k in mappings(imc) if a == "IA_ToggleWeapon"}
    imc.modify()
    for key in ("One", "Q", "Gamepad_FaceButton_Right"):
        if key in have:
            continue
        k = unreal.Key()
        k.import_text(key)
        imc.map_key(ia, k)
    EAL.save_loaded_asset(imc, only_if_is_dirty=False)
    R["check"]["imc"] = mappings(EAL.load_asset("/Game/Core/Input/IMC_JR_Combat"))
    log("teclas de sacar arma garantidas")


for fn, args in ((fix_bs, ("01",)), (fix_bs, ("02",)), (fix_keys, ())):
    try:
        fn(*args)
    except Exception as exc:  # noqa: BLE001
        R["errors"].append({"fn": fn.__name__, "args": args, "e": str(exc), "t": traceback.format_exc()[-1200:]})
with open(os.path.join(REPO, "reports", "fix_bs_and_keys.json"), "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=1, default=str)
unreal.log(f"[fix_bs] fim | erros: {len(R['errors'])}")
