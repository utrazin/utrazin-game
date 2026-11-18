"""Roda TUDO do retrabalho "Vale Alienígena" em ordem, dentro do editor (caixa Cmd), sem Play:
  py "E:/game/utrazin-game/tools/unreal/run_all_wave1.py"

Ordem: setup_wave1 -> setup_zombie_skin -> build_l01 -> setup_minimap
Cada um grava o próprio relatório em reports/. Este grava o resumo em reports/run_all_wave1.json.
Demora (vários minutos: importa ~4000 objetos). O editor pode parecer travado: espere.
"""
import json
import os
import traceback
from datetime import datetime

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPTS = ("setup_wave1", "setup_zombie_skin", "build_l01", "setup_minimap")
S = {"time": datetime.now().isoformat(), "scripts": {}}

for name in SCRIPTS:
    path = os.path.join(HERE, f"{name}.py")
    unreal.log(f"[run_all] >>> {name}")
    try:
        code = compile(open(path, encoding="utf-8").read(), path, "exec")
        exec(code, {"__file__": path, "__name__": "__main__"})  # noqa: S102 (scripts do próprio repositório)
        rep = os.path.join(REPO, "reports", f"{name}.json")
        info = {}
        if os.path.exists(rep):
            r = json.load(open(rep, encoding="utf-8"))
            info = {"avisos": len(r.get("warnings", [])), "erros": len(r.get("errors", []))}
        S["scripts"][name] = info or {"ok": True}
    except Exception as exc:  # noqa: BLE001
        S["scripts"][name] = {"falhou": str(exc), "t": traceback.format_exc()[-800:]}

with open(os.path.join(REPO, "reports", "run_all_wave1.json"), "w", encoding="utf-8") as fh:
    json.dump(S, fh, ensure_ascii=False, indent=1)
unreal.log(f"[run_all] fim: {S['scripts']}")
