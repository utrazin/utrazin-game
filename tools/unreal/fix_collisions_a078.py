"""Colisão que faltava (A-078). Pode rodar de novo. RODA NO EDITOR (caixa Cmd, sem Play):
  py "E:/game/utrazin-game/tools/unreal/fix_collisions_a078.py"
Relatório: reports/fix_collisions_a078.json.

Causa medida (reports/build_interiors_l01.json): as caixas UCX dos FBX não viram colisão na importação deste
projeto (as 46 malhas dos interiores ficaram com 0 formas simples; o mesmo já tinha acontecido com os modelos do
usuário, A-063). Sem colisão simples:
  - paredes, pisos e móveis das construções não seguram o herói nem os zumbis;
  - a base do baú do usuário (SM_PRP_Bau_Base) não é achada pelo traço de interação: o "E Abrir o baú" não aparece.
Conserto:
  1. malhas dos interiores (/Game/Environment/Interiors) sem forma simples: usam a própria malha como colisão
     (Complex as Simple; serve para parede com vão de porta e para o piso), menos os enfeites sem colisão;
  2. props do usuário (PRP_, ITM_ e a base do baú) sem forma simples: ganham uma caixa do tamanho da malha;
     a tampa do baú (PRP_Bau_Tampa) continua sem colisão de propósito. Marcos (MRC_: arco, nave, disco,
     árvore-mãe, colmeia, cristal) ficam como estão: usam a própria malha (A-051); se a primeira versão deste
     script pôs caixa neles, ela é tirada aqui.
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
EAL = unreal.EditorAssetLibrary
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
DECOR = {"SM_INT_Lixo", "SM_INT_Tapete", "SM_INT_Quadro", "SM_INT_Luminaria"}
BOXED_BY_V1 = {"SM_MRC_Arco", "SM_MRC_ArvoreMae", "SM_MRC_Colmeia", "SM_MRC_Cristal", "SM_MRC_DiscoVoador",
               "SM_MRC_NaveResgate"}
R = {"complexa": [], "caixa": [], "ja_tinham": 0, "avisos": [], "erros": []}


def simple_count(sm):
    try:
        return SMES.get_simple_collision_count(sm)
    except Exception:  # noqa: BLE001
        return -1


def use_complex(sm):
    bs = sm.get_editor_property("body_setup")
    if bs is None:
        raise RuntimeError("sem body_setup")
    sm.modify()
    bs.modify()
    bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    EAL.save_loaded_asset(sm, False)


def meshes_under(path):
    for p in EAL.list_assets(path, recursive=True, include_folder=False):
        a = EAL.load_asset(p)
        if isinstance(a, unreal.StaticMesh):
            yield a


try:
    for sm in meshes_under("/Game/Environment/Interiors"):
        name = sm.get_name()
        if name in DECOR:
            continue
        if simple_count(sm) > 0:
            R["ja_tinham"] += 1
            continue
        try:
            use_complex(sm)
            R["complexa"].append(name)
        except Exception as exc:  # noqa: BLE001
            R["erros"].append({"malha": name, "erro": str(exc)})
    for sm in meshes_under("/Game/Environment/User"):
        name = sm.get_name()
        if name.startswith("SM_MRC_"):
            # primeira versão pôs caixa nos marcos: tira (eles usam a própria malha como colisão)
            if simple_count(sm) == 1 and name in BOXED_BY_V1:
                SMES.remove_collisions(sm)
                use_complex(sm)
                R.setdefault("caixa_tirada", []).append(name)
            continue
        if not name.startswith(("SM_PRP_", "SM_ITM_")) or name.endswith("_Tampa"):
            continue
        if simple_count(sm) > 0:
            R["ja_tinham"] += 1
            continue
        try:
            SMES.add_simple_collisions(sm, unreal.ScriptCollisionShapeType.BOX)
            EAL.save_loaded_asset(sm, False)
            R["caixa"].append(name)
        except Exception as exc:  # noqa: BLE001
            R["erros"].append({"malha": name, "erro": str(exc)})
except Exception:  # noqa: BLE001
    R["erros"].append(traceback.format_exc()[-1500:])
os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
with open(os.path.join(REPO, "reports", "fix_collisions_a078.json"), "w", encoding="utf-8") as fh:
    json.dump(R, fh, ensure_ascii=False, indent=1)
unreal.log(f"[fix_collisions_a078] complexa: {len(R['complexa'])} | caixa: {len(R['caixa'])} | erros: {len(R['erros'])}")
