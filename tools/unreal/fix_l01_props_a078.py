"""Tira enfeites sem sentido e assenta no chão os que flutuam (A-078). Pode rodar de novo. RODA NO EDITOR (Cmd):
  py "E:/game/utrazin-game/tools/unreal/fix_l01_props_a078.py"
Relatório: reports/fix_l01_props_a078.json. O build_l01.py faz o mesmo nas próximas vezes.

1. Remove o sofá (SM_Couch) e os pneus empilhados (SM_Wheels_Stack) do acampamento da queda: não combinam com
   um acampamento de sobreviventes e foram os "itens aleatórios" do print.
2. Enfeites pequenos das pastas L01/POI e L01/Cenario que estão no ar (ou enterrados) vão para o chão
   (l01_ground_snap.py: mede o terreno no centro e nos cantos e põe a base na menor altura - 3 cm).
"""
import json
import os
import sys
import traceback

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
if HERE not in sys.path:
    sys.path.append(HERE)
import l01_ground_snap as G  # noqa: E402

MAP = "/Game/Levels/L01_ZombieValley/L01_ZombieValley"
REMOVE = {"L01/POI/Z0_Acampamento": ("SM_Couch", "SM_Wheels_Stack")}
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
R = {"removidos": [], "assentados": [], "erros": []}
try:
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if w is None or w.get_path_name().split(".")[0] != MAP:
        LES.load_level(MAP)
    for a in list(ACTORS.get_all_level_actors()):
        if not isinstance(a, unreal.StaticMeshActor):
            continue
        folder = str(a.get_folder_path())
        sm = a.static_mesh_component.get_editor_property("static_mesh")
        name = sm.get_name() if sm else ""
        for f, names in REMOVE.items():
            if folder.startswith(f) and name in names:
                R["removidos"].append(f"{a.get_actor_label()} ({name})")
                ACTORS.destroy_actor(a)
                break
    R["assentados"] = G.snap_all(log=unreal.log)
    LES.save_current_level()
except Exception:  # noqa: BLE001
    R["erros"].append(traceback.format_exc()[-1500:])
os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
with open(os.path.join(REPO, "reports", "fix_l01_props_a078.json"), "w", encoding="utf-8") as fh:
    json.dump(R, fh, ensure_ascii=False, indent=1)
unreal.log(f"[fix_l01_props_a078] removidos {len(R['removidos'])} | assentados {len(R['assentados'])} | erros {len(R['erros'])}")
