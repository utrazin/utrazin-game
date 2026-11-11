"""Valida um mapa de fase: atores obrigatórios do fluxo (checkpoints, diretor de horda, resgate).

EXECUTA SOMENTE NO PYTHON DO EDITOR UNREAL:
  UnrealEditor-Cmd.exe unreal/JogoResgate/JogoResgate.uproject -run=pythonscript \
      -script="tools/unreal/validate_level.py --map /Game/Levels/L01_Zombies/L01_Zombies" -unattended -nullrhi
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ue_common import MAP_RE, level_problems  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_ACTORS = {
    "JRCheckpoint": 2,          # Start + Transition
    "JRHordeDirector": 1,
    "JRRescueTarget": 1,
    "PlayerStart": 1,
}


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - requer Unreal
    ap = argparse.ArgumentParser(prog="validate_level.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", required=True)
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])
    try:
        import unreal  # type: ignore
    except ImportError:
        print("ERRO: este script roda apenas no Python do Editor Unreal.", file=sys.stderr)
        return 2
    problems = []
    map_name = args.map.rsplit("/", 1)[-1]
    if not MAP_RE.match(map_name):
        problems.append(f"nome do mapa fora do padrão: {map_name}")
    if not unreal.EditorLoadingAndSavingUtils.load_map(args.map):
        problems.append("não foi possível carregar o mapa")
    else:
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        counts = {}
        for cls_name in REQUIRED_ACTORS:
            ue_cls = getattr(unreal, cls_name, None)  # classes C++ expostas: unreal.JRCheckpoint etc.
            if ue_cls is None:
                problems.append(f"classe {cls_name} não exposta ao Python (módulo compilado?)")
                continue
            counts[cls_name] = sum(1 for a in actors if isinstance(a, ue_cls))
        problems += level_problems(counts, REQUIRED_ACTORS)
    out = REPO_ROOT / "reports" / f"validate_level_{map_name}_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"map": args.map, "problems": problems}, ensure_ascii=False, indent=2), encoding="utf-8")
    for p in problems:
        unreal.log_error(f"[validate_level] {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
