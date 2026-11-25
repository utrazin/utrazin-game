"""[A-098] Roda tudo da rodada de 23/11 noite na ordem certa (depois de compilar_remap.bat e gerar_grama.bat).

RODA NO EDITOR (caixa Cmd, sem Play):
    py "E:/game/utrazin-game/tools/unreal/a098_tudo.py"

1. setup_bike_anim.py      malhas novas da bicicleta (pedivela, pedais, selim, guidão) + pedalada dos 2 heróis
2. setup_grass.py          tufos de grama novos (precisa do gerar_grama.bat antes)
3. fix_building_collision.py  colisão justa nos prédios (acaba a parede invisível)
4. fix_city_landscape.py   confere o Landscape; se o relevo for da planta velha (v5), APAGA e para com os números do
                           import da v6. Importe e rode este script de novo. Com o relevo certo ele segue sozinho:
                           setup_city_landscape.py, dress_city_v6.py, build_interiors_vila.py.
Pode rodar quantas vezes quiser. Cada etapa escreve o próprio relatório em reports/.
"""
import os
import runpy
import sys
import traceback

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [("setup_bike_anim.py", []), ("setup_grass.py", []), ("fix_building_collision.py", []), ("fix_city_landscape.py", [])]
ok, fail = [], []
for name, args in STEPS:
    unreal.log(f"[a098] ===== {name} =====")
    old = sys.argv
    sys.argv = [name] + args
    try:
        runpy.run_path(os.path.join(HERE, name), run_name="__main__")
        ok.append(name)
    except SystemExit:
        ok.append(name)
    except Exception as exc:  # noqa: BLE001
        fail.append(name)
        unreal.log_error(f"[a098] {name} parou: {exc}\n{traceback.format_exc()[-1200:]}")
        if name == "fix_city_landscape.py":
            unreal.log_warning("[a098] se a mensagem acima pede para importar o city_height.png da v6, importe e rode o a098_tudo.py de novo")
    finally:
        sys.argv = old
unreal.log(f"[a098] fim | ok: {', '.join(ok) or '-'} | com erro: {', '.join(fail) or '-'}")
if not fail:
    unreal.log("[a098] agora: Build > Build Paths, Ctrl+S e Play. Console: JRRecorde 6 (abre o Mercado), JRCristais 50 (Árvore-Mãe)")
