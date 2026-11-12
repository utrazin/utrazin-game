"""Marca a posição ATUAL do jogador (durante o Play) para um ponto da fase.
Use DURANTE o jogo (Shift+F1 libera o mouse; digite na caixa Cmd do Editor):
  py "E:/game/utrazin-game/tools/unreal/mark_here.py" transicao
  py "E:/game/utrazin-game/tools/unreal/mark_here.py" horda
  py "E:/game/utrazin-game/tools/unreal/mark_here.py" resgate
Depois PARE o jogo e rode apply_marks.py para mover os atores no mapa.
Grava em reports/marks.json.
"""
import json
import os
import sys

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PATH = os.path.join(REPO, "reports", "marks.json")
VALID = {"transicao", "horda", "resgate"}

what = sys.argv[1].lower() if len(sys.argv) > 1 else ""
if what not in VALID:
    unreal.log_error(f"[mark_here] use um de: {', '.join(sorted(VALID))}")
else:
    game = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    pawn = unreal.GameplayStatics.get_player_pawn(game, 0) if game else None
    if not pawn:
        unreal.log_error("[mark_here] o jogo não está rodando (aperte Play e chegue no lugar desejado)")
    else:
        loc = pawn.get_actor_location()
        marks = {}
        if os.path.exists(PATH):
            with open(PATH, encoding="utf-8") as f:
                marks = json.load(f)
        marks[what] = [loc.x, loc.y, loc.z]
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(marks, f, indent=2)
        unreal.log(f"[mark_here] {what} marcado em {loc}. Marcados: {sorted(marks)}")
