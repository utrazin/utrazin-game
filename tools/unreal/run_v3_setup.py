"""[A-085/A-086] Roda, em ordem, tudo do pacote v3 (sem Play, depois de compilar):
  py "E:/game/utrazin-game/tools/unreal/run_v3_setup.py"
1. import_user_assets.py   importa os 7 modelos novos da vila (/Game/Environment/User/Vila) e confere colisões
3. dress_remap_v3.py       veste a cidade e a arena + céu alienígena e exposição fixa
Depois: abrir L_Arena_F1, Build > Build Paths, Ctrl+S. Relatórios em reports/."""
import os
import runpy
import sys
import traceback

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))

# [A-087] .uasset somente leitura (vindos do Git) não deixam salvar: tira o atributo antes (= attrib -R /S).
import stat  # noqa: E402
CONTENT = os.path.abspath(os.path.join(HERE, "..", "..", "unreal", "JogoResgate", "Content"))
_fixed = 0
for _root, _dirs, _files in os.walk(CONTENT):
    for _f in _files:
        _p = os.path.join(_root, _f)
        try:
            if not os.access(_p, os.W_OK):
                os.chmod(_p, stat.S_IWRITE | stat.S_IREAD)
                _fixed += 1
        except OSError:
            pass
unreal.log(f"[run_v3_setup] {_fixed} arquivos somente leitura liberados")
for nome in ("import_user_assets.py", "setup_v3_materials.py", "setup_hud_v3.py", "dress_remap_v3.py"):  # run_remap_setup já rodou em 22/11
    sys.argv = [os.path.join(HERE, nome)]
    try:
        runpy.run_path(os.path.join(HERE, nome), run_name="__main__")
        unreal.log(f"[run_v3_setup] {nome}: ok")
    except SystemExit:
        unreal.log(f"[run_v3_setup] {nome}: ok (saiu)")
    except Exception:  # noqa: BLE001
        unreal.log_error(f"[run_v3_setup] {nome}: ERRO\n{traceback.format_exc()[-1500:]}")
