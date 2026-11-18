"""OBSOLETO: use tools/unreal/setup_ai_director.py (este arquivo só roda aquele, para os atalhos antigos).

RODA NO EDITOR (caixa Cmd), sem Play, DEPOIS de compilar o C++:
  py "E:/game/utrazin-game/tools/unreal/add_ai_director.py"
Relatório: reports/setup_ai_director.json
"""
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "setup_ai_director.py"), run_name="__main__")
