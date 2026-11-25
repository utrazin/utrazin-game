"""[A-098] Colisão justa nos prédios/casas da cidade (fim da "parede invisível").

RODA NO EDITOR (caixa Cmd, sem Play):
  py "E:/game/utrazin-game/tools/unreal/fix_building_collision.py"                 troca para convex decomposition
  py "E:/game/utrazin-game/tools/unreal/fix_building_collision.py" --so-relatorio  só mede (não muda nada)
  py "E:/game/utrazin-game/tools/unreal/fix_building_collision.py" --complexa      usa a própria malha (Complex as Simple)

Causa (prep_tripo.py + import_user_assets.py): colisão "box" = UMA caixa UCX do tamanho da malha inteira (beiral,
varanda, chaminé, toldo entram na caixa: o herói bate no ar em volta da casa); "complex" = a malha mesmo.
Agora, para cada malha da lista: remove as colisões simples, volta o trace flag para o padrão e gera convex
decomposition (V-HACD) com 8 a 16 cascas (mais para malha aberta: barraca, torre de rádio). Mede antes e depois a
caixa da colisão contra a caixa visual e avisa quando sobra mais de 25 cm para algum lado.
Os atores da L_Cidade usam o asset, então pegam a colisão nova sem rodar o dress de novo (salve o mapa depois).
Relatório: reports/fix_building_collision.json
"""
import json
import os
import sys
import traceback

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
EAL = unreal.EditorAssetLibrary
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
U = "/Game/Environment/User"
# malha: cascas (hull count)
MESHES = {
    f"{U}/Vila/SM_BLD_Armeiro": 16, f"{U}/Vila/SM_BLD_Bancada": 16, f"{U}/Vila/SM_BLD_Casa01": 16,
    f"{U}/Vila/SM_BLD_Casa02": 16, f"{U}/Construcoes/SM_CON_CasaVila": 16, f"{U}/Construcoes/SM_CON_Cabana": 12,
    f"{U}/Construcoes/SM_CON_PostoLoja": 12, f"{U}/Construcoes/SM_CON_TorreRadio": 16,
    f"{U}/Construcoes/SM_CON_Barraca": 16, f"{U}/Construcoes/SM_CON_Conteiner": 8,
}
MAX_HULL_VERTS = 24
HULL_PRECISION = 200000
SLACK_CM = 25.0
ARGS = set(sys.argv[1:])
R = {"mode": "relatorio" if "--so-relatorio" in ARGS else ("complexa" if "--complexa" in ARGS else "convexa"),
     "meshes": {}, "warnings": [], "errors": []}


def log(m):
    unreal.log(f"[colisao] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[colisao] {m}")


def box_of(points_min_max):
    mn = [min(p[0][i] for p in points_min_max) for i in range(3)]
    mx = [max(p[1][i] for p in points_min_max) for i in range(3)]
    return mn, mx


def collision_box(sm):
    """Caixa que envolve a colisão simples (caixas + cascas), em cm no espaço da malha. None se não der para ler."""
    bs = sm.get_editor_property("body_setup")
    if bs is None:
        return None, "sem body_setup"
    try:
        agg = bs.get_editor_property("agg_geom")
    except Exception as exc:  # noqa: BLE001
        return None, f"agg_geom não exposto ({exc})"
    parts = []
    try:
        for b in agg.get_editor_property("box_elems"):
            c = b.get_editor_property("center")
            hx, hy, hz = b.get_editor_property("x") / 2, b.get_editor_property("y") / 2, b.get_editor_property("z") / 2
            parts.append(((c.x - hx, c.y - hy, c.z - hz), (c.x + hx, c.y + hy, c.z + hz)))  # (ignora giro da caixa)
    except Exception:  # noqa: BLE001
        pass
    try:
        for cv in agg.get_editor_property("convex_elems"):
            got = False
            for key in ("elem_box", "vertex_data"):
                try:
                    v = cv.get_editor_property(key)
                except Exception:  # noqa: BLE001
                    continue
                if key == "elem_box" and v is not None:
                    parts.append(((v.min.x, v.min.y, v.min.z), (v.max.x, v.max.y, v.max.z)))
                    got = True
                    break
                if key == "vertex_data" and v:
                    xs, ys, zs = [p.x for p in v], [p.y for p in v], [p.z for p in v]
                    parts.append(((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))))
                    got = True
                    break
            if not got:
                return None, "cascas sem dados expostos ao Python"
    except Exception:  # noqa: BLE001
        pass
    if not parts:
        return None, "sem colisão simples"
    return box_of(parts), ""


def measure(sm):
    bb = sm.get_bounding_box()
    vis = ([bb.min.x, bb.min.y, bb.min.z], [bb.max.x, bb.max.y, bb.max.z])
    out = {"visual_cm": [round(vis[1][i] - vis[0][i]) for i in range(3)],
           "simples": SMES.get_simple_collision_count(sm), "cascas": SMES.get_convex_collision_count(sm)}
    try:
        out["trace"] = str(sm.get_editor_property("body_setup").get_editor_property("collision_trace_flag")).split(".")[-1]
    except Exception:  # noqa: BLE001
        pass
    col, why = collision_box(sm)
    if col is None:
        out["colisao_cm"] = why
        return out, 0.0
    out["colisao_cm"] = [round(col[1][i] - col[0][i]) for i in range(3)]
    # quanto a colisão passa da malha visível, por lado (+X, -X, +Y, -Y, topo)
    over = {"+X": col[1][0] - vis[1][0], "-X": vis[0][0] - col[0][0], "+Y": col[1][1] - vis[1][1],
            "-Y": vis[0][1] - col[0][1], "topo": col[1][2] - vis[1][2]}
    out["sobra_cm"] = {k: round(v) for k, v in over.items()}
    return out, max(over.values())


def to_convex(sm, hulls):
    SMES.remove_collisions(sm)
    bs = sm.get_editor_property("body_setup")
    if bs is not None:
        bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
    for fn in ("set_convex_decomposition_collisions_with_notification", "set_convex_decomposition_collisions"):
        f = getattr(SMES, fn, None)
        if f is None:
            continue
        try:
            ok = f(sm, hulls, MAX_HULL_VERTS, HULL_PRECISION, True) if fn.endswith("notification") else f(sm, hulls, MAX_HULL_VERTS, HULL_PRECISION)
            return bool(ok) or SMES.get_convex_collision_count(sm) > 0
        except TypeError:
            ok = f(sm, hulls, MAX_HULL_VERTS, HULL_PRECISION)
            return bool(ok) or SMES.get_convex_collision_count(sm) > 0
    # versão antiga
    f = getattr(unreal.EditorStaticMeshLibrary, "set_convex_decomposition_collisions", None)
    if f is not None:
        return bool(f(sm, hulls, MAX_HULL_VERTS, HULL_PRECISION))
    raise RuntimeError("nem StaticMeshEditorSubsystem nem EditorStaticMeshLibrary têm set_convex_decomposition_collisions")


def to_complex(sm):
    SMES.remove_collisions(sm)
    bs = sm.get_editor_property("body_setup")
    bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    return True


def main():
    for path, hulls in MESHES.items():
        name = path.rsplit("/", 1)[1]
        sm = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
        if sm is None:
            warn(f"não existe {path}")
            continue
        try:
            before, over0 = measure(sm)
            entry = {"antes": before}
            if over0 > SLACK_CM:
                warn(f"{name}: colisão passa {over0:.0f} cm da malha (parede invisível)")
            if R["mode"] != "relatorio":
                ok = to_complex(sm) if R["mode"] == "complexa" else to_convex(sm, hulls)
                if not ok:
                    warn(f"{name}: a troca de colisão não confirmou")
                EAL.save_loaded_asset(sm)
                after, over1 = measure(sm)
                entry["depois"] = after
                if R["mode"] == "convexa" and after.get("cascas", 0) == 0:
                    warn(f"{name}: ficou SEM cascas (o herói atravessa): rode com --complexa")
                elif over1 > SLACK_CM:
                    warn(f"{name}: ainda sobra {over1:.0f} cm (aumente as cascas ou use --complexa)")
            R["meshes"][name] = entry
            log(f"{name}: {entry}")
        except Exception as exc:  # noqa: BLE001
            R["errors"].append(f"{name}: {exc}")
            unreal.log_error(f"[colisao] {name}: {exc}\n{traceback.format_exc()[-800:]}")


try:
    main()
except Exception as exc:  # noqa: BLE001
    R["errors"].append(str(exc))
    unreal.log_error(f"[colisao] {exc}\n{traceback.format_exc()[-1500:]}")
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "fix_building_collision.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[colisao] fim ({R['mode']}) | {len(R['meshes'])} malhas | avisos {len(R['warnings'])} | erros {len(R['errors'])}")
