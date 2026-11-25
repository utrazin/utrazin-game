"""Roda, em ordem, os scripts de editor do pacote "fechar F1 + F2" (A-081 a A-084). Sem Play, depois de compilar:
  py "E:/game/utrazin-game/tools/unreal/run_remap_setup.py"
Cada script escreve o próprio relatório em reports/. Um erro num script não impede os outros."""
import os
import runpy
import sys
import traceback

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = ["setup_zombie_feel.py", "setup_pickups_3d.py", "setup_remap_hud.py", "build_remap_f2.py"]
resultado = []
for nome in SCRIPTS:
    sys.argv = [os.path.join(HERE, nome)]
    try:
        runpy.run_path(os.path.join(HERE, nome), run_name="__main__")
        resultado.append(f"{nome}: ok")
    except SystemExit:
        resultado.append(f"{nome}: ok (saiu)")
    except Exception:  # noqa: BLE001
        resultado.append(f"{nome}: ERRO")
        unreal.log_error(traceback.format_exc()[-1500:])
for linha in resultado:
    unreal.log(f"[run_remap_setup] {linha}")
