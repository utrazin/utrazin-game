"""Construções com interior na L01 (A-070): onde cada uma fica no mapa e o que ela substitui.

Duas partes:
- CÁLCULO (fora da Unreal, numpy): decide a posição de cada construção de assets/work/interiors/interiors_l01.json
  e grava assets/work/interiors/interiors_placement_l01.json + uma prévia de cima. Roda uma vez (de novo só se
  mudar o layout ou as construções):
      python tools/unreal/l01_interiors.py           (precisa de numpy e Pillow)
- PLANO (Python puro, usado por l01_user_dressing.plan_v3): lê os dois JSON e ajusta o plano: tira os modelos
  e peças de blockout trocados, registra a área das construções (vegetação e enfeites desviam) e leva os baús
  que moram dentro delas (Bau_Pistola_Posto, Bau_Vila_Municao) para a posição de dentro.
Regras de posição:
- substitui um modelo do usuário ("CON_CasaVila#1" = 2a casa): mesmo lugar e mesma frente (+X do modelo =
  porta); se a construção nova for maior e encostar em algo, recua pela parte de trás (até 8 m);
- substitui peça de blockout (sala trancada): mesmo lugar, frente para o centro do POI;
- lugar novo ("near_route"): perto da estrada principal na zona pedida, a side_m do eixo, frente para a estrada,
  chão plano (desnível < 1,2 m no terreno), longe de POIs (60 m) e sem bater em nada do registro;
- "poi": no POI com um deslocamento.
Coordenadas: o JSON das construções está em metros do Blender (y para a esquerda); aqui viram cm da Unreal
(y para a direita): (x, y) -> (x, -y) e yaw -> -yaw.
"""
from __future__ import annotations

import json
import math
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
INT_DIR = os.path.join(REPO, "assets", "work", "interiors")
INTERIORS = os.path.join(INT_DIR, "interiors_l01.json")
PLACEMENT = os.path.join(INT_DIR, "interiors_placement_l01.json")
LEVEL_DIR = os.path.join(REPO, "assets", "work", "levels", "L01")
POI_CLEAR_CM = 6000.0
MAX_STEP_M = 1.2
PUSH_MAX_CM = 800.0
# o que cada construção pode ter por perto (enfeites que caírem dentro saem)
CHEST_LABELS_INSIDE = ("Bau_Pistola_Posto", "Bau_Vila_Municao")
# Ligado só depois do OK do usuário (OD-P07): o build_interiors_l01.py cria este arquivo ao rodar. Antes disso o
# plano NÃO troca nada (build_l01.py e a vegetação continuam com os modelos antigos). JR_INTERIORS=1 força (testes).
APPROVED = os.path.join(INT_DIR, "APROVADO.txt")


def enabled():
    return os.path.exists(APPROVED) or os.environ.get("JR_INTERIORS") == "1"


def load_json(path):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None


def radius_cm(b):
    sx, sy = b["size_m"]
    return 50.0 * math.hypot(sx, sy) + 60.0


def to_world(px, py, pyaw, lx_m, ly_m):
    """Local do Blender (m, y esquerda) -> mundo Unreal (cm) para uma construção em (px, py, yaw graus)."""
    ux, uy = lx_m * 100.0, -ly_m * 100.0
    t = math.radians(pyaw)
    return px + ux * math.cos(t) - uy * math.sin(t), py + ux * math.sin(t) + uy * math.cos(t)


# ====================================================================== plano (puro)
def apply_to_plan(P, L, reg=None, have=None):
    """Ajusta o plano de l01_user_dressing.plan_v3 com as construções. Não faz nada sem os dois JSON."""
    B = load_json(INTERIORS)
    PL = load_json(PLACEMENT)
    P["interiors"] = []
    P["replaced_user"] = []      # modelos do usuário trocados (o build_interiors apaga o ator antigo nesse lugar)
    P["culled"] = []             # enfeites que caíram dentro de uma construção
    if not B or not PL or not enabled():
        return P
    have = have or (lambda n: True)
    poi = {p["key"]: p for p in L["pois"]}
    used = {}
    for key, b in B["buildings"].items():
        pl = PL["placements"].get(key)
        if not pl:
            P["notes"].append(f"interior {key}: sem posição (rode l01_interiors.py)")
            continue
        rep = b.get("replaces", {})
        # tira os modelos do usuário trocados (pela ordem: "#1" = segundo do mesmo nome)
        for ref in rep.get("user", []):
            name, _, idx = ref.partition("#")
            idx = int(idx or 0)
            hits = [i for i, p in enumerate(P["place"]) if p["name"] == name]
            if idx < len(hits):
                gone = P["place"][hits[idx]]
                gone["replaced_by"] = key
                P["replaced_user"].append({"name": name, "x": gone["x"], "y": gone["y"], "key": key})
                used.setdefault("drop", []).append(hits[idx])
                if reg is not None:
                    _drop_footprint(reg, gone["x"], gone["y"])
        for (pk, ref) in rep.get("blockout", []):
            for i, e in enumerate(poi[pk]["pieces"]):
                if (e.get("q") or e.get("mesh") or e.get("engine")) == ref:
                    P["skip"].add((pk, i))
        x, y, yaw = pl["x"], pl["y"], pl["yaw"]
        r = radius_cm(b)
        if reg is not None:
            reg.add(x, y, r, "estrutura", f"interior {key}", f"INT_{key}", force=True)
        # itens do layout que passam a morar dentro (ex.: kit e munição que eram da loja fechada)
        for label, (lx, ly) in b.get("absorb_pickups", {}).items():
            px_, py_ = to_world(x, y, yaw, lx, ly)
            P["pickups"][label] = {"x": px_, "y": py_, "interior": key}
        # baús que moram dentro: frente (+Y local do AJRLootChest) virada para o centro da construção
        for ch in b.get("chests", []):
            cx, cy = to_world(x, y, yaw, ch["x"], ch["y"])
            face = math.degrees(math.atan2(y - cy, x - cx))
            P["chests"][ch["label"]] = {"x": cx, "y": cy, "yaw": face - 90.0, "kind": "bau", "interior": key}
        P["interiors"].append({"key": key, "x": x, "y": y, "yaw": yaw, "radius_cm": r})
    for i in sorted(set(used.get("drop", [])), reverse=True):
        P["place"].pop(i)
    # enfeites conferidos (grupos, dressing) que caíram dentro de uma construção saem
    keep = []
    for p in P["place"]:
        inside = any(math.hypot(p["x"] - it["x"], p["y"] - it["y"]) < it["radius_cm"] * 0.8 for it in P["interiors"])
        if inside and p.get("folder", "").startswith(("L01/Cenario", "L01/POI")) and p["name"].startswith(("PRP_", "NAT_", "ITM_")):
            P["notes"].append(f"{p['name']} saiu (dentro da construção)")
            P["culled"].append({"name": p["name"], "x": p["x"], "y": p["y"]})
            if reg is not None:
                _drop_footprint(reg, p["x"], p["y"])
            continue
        keep.append(p)
    P["place"] = keep
    return P


def rect_points(x, y, yaw, b, front_m=4.2, step_m=1.0):
    """Pontos (cm) do contorno da construção + a área das rampas na frente das portas."""
    sx, sy = b["size_m"]
    pts = []
    nx, ny = max(2, int(sx / step_m)), max(2, int(sy / step_m))
    for i in range(nx + 1):
        for lyy in (-sy / 2 - 0.3, sy / 2 + 0.3):
            pts.append(to_world(x, y, yaw, -sx / 2 + sx * i / nx, lyy))
    for j in range(ny + 1):
        for lxx in (-sx / 2 - 0.3, sx / 2 + 0.3):
            pts.append(to_world(x, y, yaw, lxx, -sy / 2 + sy * j / ny))
    for d in b.get("doors", []):
        side, off = d["side"], d["offset_m"]
        for k in (1.5, 3.0, front_m):
            if side == "+X":
                pts.append(to_world(x, y, yaw, sx / 2 + k, off))
            elif side == "-X":
                pts.append(to_world(x, y, yaw, -sx / 2 - k, -off))
            elif side == "+Y":
                pts.append(to_world(x, y, yaw, -off, sy / 2 + k))
            else:
                pts.append(to_world(x, y, yaw, off, -sy / 2 - k))
    return pts


def _route_dist(C, x, y, skip_trails):
    """Distância (cm) até a borda da rota mais próxima; skip_trails ignora as trilhas a pé ("Trilha_*")."""
    import l01_user_dressing as U
    best = 1e12
    for key, half, pts in C.routes:
        if skip_trails and key.startswith("Trilha"):
            continue
        for a, b in zip(pts, pts[1:]):
            best = min(best, U.seg_dist(x, y, a[0], a[1], b[0], b[1]) - half)
    return best


def rect_clear(C, x, y, yaw, b, margin_cm=40.0):
    """Contorno fora de estrada/trilha, rio e lago. As rampas das portas podem encostar numa trilha a pé
    (a trilha leva até a porta), mas não em estrada."""
    pts = rect_points(x, y, yaw, b)
    n_door = 3 * len(b.get("doors", []))
    body, ramps = pts[:len(pts) - n_door], pts[len(pts) - n_door:]
    ok = all(C.road_dist(px, py) > margin_cm and not C.in_hazard(px, py, 100.0) for px, py in body)
    return ok and all(_route_dist(C, px, py, True) > margin_cm and not C.in_hazard(px, py, 100.0) for px, py in ramps)


def _drop_footprint(reg, x, y):
    keep = [f for f in reg.items if not (abs(f.x - x) < 1.0 and abs(f.y - y) < 1.0)]
    if len(keep) != len(reg.items):
        reg._rebuild(keep)


# ====================================================================== cálculo das posições (numpy)
def compute(write=True, preview=True):
    import sys
    sys.path.insert(0, os.path.join(REPO, "tools", "pipeline"))
    sys.path.insert(0, os.path.join(REPO, "tools", "unreal"))
    import numpy as np
    import l01_user_dressing as U

    L = json.load(open(os.path.join(LEVEL_DIR, "l01_layout_v3.json"), encoding="utf-8"))
    B = load_json(INTERIORS)
    if not B:
        raise FileNotFoundError(f"{INTERIORS}: rode tools/blender/gen_interiors_l01.py antes")
    P = U.plan_v3(L, interiors=False)
    reg = P["registry"]
    reg.allow("piso", "estrutura_nova")          # pode ficar em cima de piso de POI; o resto bloqueia
    reg.allow("gameplay", "estrutura_nova")      # itens/baús do layout: os que caem dentro são levados para dentro
    C = U.Clearance(L)
    npz = np.load(os.path.join(LEVEL_DIR, "l01_preview_v3.npz"))
    H = npz["H"]
    half_m = L["map_half_cm"] / 100.0
    n = H.shape[0]
    step = 2 * half_m / (n - 1)

    def height_range(x, y, r_cm):
        """Desnível (m) do terreno dentro do círculo (x, y em cm da Unreal)."""
        X, Y = x / 100.0, -y / 100.0
        rm = r_cm / 100.0
        i0, i1 = int((X - rm + half_m) / step), int((X + rm + half_m) / step) + 1
        j0, j1 = int((Y - rm + half_m) / step), int((Y + rm + half_m) / step) + 1
        i0, j0 = max(0, i0), max(0, j0)
        sub = H[i0:min(n, i1), j0:min(n, j1)]
        return float(sub.max() - sub.min()) if sub.size else 99.0

    zones = {z["id"]: z for z in L["zones"]}

    def settle(b, x0, y0, yaw, r):
        """Menor deslocamento (para trás e para os lados, passos de 1 m, até PUSH_MAX_CM) livre de tudo."""
        fx, fy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        moves = sorted(((bk, sd) for bk in range(0, int(PUSH_MAX_CM) + 1, 100)
                        for sd in range(-int(PUSH_MAX_CM), int(PUSH_MAX_CM) + 1, 100)),
                       key=lambda m: math.hypot(m[0], m[1]) + 0.01 * abs(m[1]))
        for back, side in moves:
            x, y = x0 - fx * back - fy * side, y0 - fy * back + fx * side
            if reg.can_place(x, y, r * 0.75, tag="estrutura_nova") and rect_clear(C, x, y, yaw, b):
                return (x, y, yaw, round(math.hypot(back, side)))
        return None
    out = {"version": 1, "unit": "cm", "placements": {}, "notes": []}
    # 1) os que trocam algo primeiro (ocupam o lugar antigo), depois os novos
    order = sorted(B["buildings"].items(), key=lambda kv: 0 if kv[1].get("replaces") else 1)
    for key, b in order:
        rep, place = b.get("replaces", {}), b.get("place")
        r = radius_cm(b)
        pos = None
        if rep.get("user"):
            name, _, idx = rep["user"][0].partition("#")
            hits = [p for p in P["place"] if p["name"] == name]
            src = hits[int(idx or 0)]
            x0, y0, yaw = src["x"], src["y"], float(src["yaw"])
            _drop_footprint(reg, x0, y0)
            pos = settle(b, x0, y0, yaw, r)
            if pos is None:
                pos = (x0, y0, yaw, 0)
                out["notes"].append(f"{key}: não achou lugar livre recuando; ficou no lugar do modelo antigo")
        elif rep.get("blockout"):
            pk, ref = rep["blockout"][0]
            pz = next(p for p in L["pois"] if p["key"] == pk)
            idx, e = next((i, e) for i, e in enumerate(pz["pieces"]) if (e.get("q") or e.get("mesh") or e.get("engine")) == ref)
            x, y = e["loc"][0], e["loc"][1]
            reg.remove_ids([f"{pk}[{idx}]"])           # a peça trocada sai antes de procurar lugar
            parent = next((p for p in L["pois"] if p["key"] == "Posto"), pz) if pk == "SalaTrancada" else pz
            yaw = math.degrees(math.atan2(parent["loc"][1] - y, parent["loc"][0] - x))
            pos = settle(b, x, y, yaw, r) or (x, y, yaw, 0)
        elif place and place.get("poi"):
            pz = next(p for p in L["pois"] if p["key"] == place["poi"])
            ox, oy = place.get("offset_m", (0, 0))
            x, y = pz["loc"][0] + ox * 100.0, pz["loc"][1] + oy * 100.0
            yaw = math.degrees(math.atan2(pz["loc"][1] - y, pz["loc"][0] - x)) + 180.0   # porta para fora da torre
            pos = settle(b, x, y, yaw, r)
            if pos is None:
                out["notes"].append(f"{key}: sem lugar livre perto do POI {place['poi']}")
        elif place and place.get("near_route"):
            pts = next(p for k, _, p in C.routes if k == place["near_route"])
            zid = place["zone"]
            z = zones[zid]
            cand = []
            for j in range(2, len(pts) - 2):
                x0, y0 = pts[j]
                zn = min(zones, key=lambda q: math.hypot(zones[q]["center"][0] - x0, zones[q]["center"][1] - y0) / max(1.0, zones[q]["radius_cm"]))
                if zn != zid:
                    continue
                tx, ty = pts[j + 1][0] - pts[j - 1][0], pts[j + 1][1] - pts[j - 1][1]
                tl = math.hypot(tx, ty) or 1.0
                nx, ny = -ty / tl, tx / tl
                for side in (1, -1):
                    for extra in (0.0, 600.0, 1200.0):
                        d = place["side_m"] * 100.0 + extra
                        x, y = x0 + nx * side * d, y0 + ny * side * d
                        if any(math.hypot(x - p["loc"][0], y - p["loc"][1]) < POI_CLEAR_CM for p in L["pois"]):
                            continue
                        if not C.ok(x, y, r, road_margin=300.0) or not reg.can_place(x, y, r, tag="estrutura_nova"):
                            continue
                        dz = height_range(x, y, r * 0.8)
                        if dz > MAX_STEP_M:
                            continue
                        mid = math.hypot(x0 - z["center"][0], y0 - z["center"][1]) / max(1.0, z["radius_cm"])
                        yaw = math.degrees(math.atan2(y0 - y, x0 - x))       # porta (+X) para a estrada
                        cand.append((dz + mid * 0.6 + extra / 3000.0, x, y, yaw, dz))
            if cand:
                cand.sort()
                _, x, y, yaw, dz = cand[0]
                pos = (x, y, yaw, 0)
                out["notes"].append(f"{key}: {len(cand)} lugares possíveis; escolhido com desnível {dz:.2f} m")
            else:
                out["notes"].append(f"{key}: nenhum lugar livre e plano perto da estrada na zona {zid}")
        if pos is None:
            continue
        x, y, yaw, back = pos
        reg.add(x, y, r, "estrutura", f"interior {key}", f"INT_{key}", force=True)
        out["placements"][key] = {"x": round(x, 1), "y": round(y, 1), "yaw": round(yaw, 1), "radius_cm": round(r, 1),
                                  "recuo_cm": back, "desnivel_m": round(height_range(x, y, r * 0.8), 2)}
    if write:
        json.dump(out, open(PLACEMENT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if preview:
        draw_preview(L, B, out, os.path.join(INT_DIR, "previews", "mapa_construcoes.png"))
    return out


def draw_preview(L, B, out, path):
    """Mapa (minimapa v4, sem nomes) com o contorno de cada construção (amarelo) e a porta (ciano);
    e uma folha com o recorte de 160 m em volta de cada uma."""
    from PIL import Image, ImageDraw, ImageFont
    base_p = os.path.join(LEVEL_DIR, "T_L01_Minimap_v4.png")
    im = Image.open(base_p).convert("RGB") if os.path.exists(base_p) else Image.new("RGB", (2048, 2048), (24, 30, 62))
    S = im.size[0]
    half = L["map_half_cm"]
    dr = ImageDraw.Draw(im)

    def font(sz):
        try:
            return ImageFont.truetype("DejaVuSans-Bold.ttf", sz)
        except OSError:
            return ImageFont.load_default()

    def px(x, y):
        return ((x + half) / (2 * half) * S, (y + half) / (2 * half) * S)

    crops = []
    for key, pl in out["placements"].items():
        b = B["buildings"][key]
        sx, sy = b["size_m"]
        pts = [to_world(pl["x"], pl["y"], pl["yaw"], cx, cy) for cx, cy in ((sx / 2, sy / 2), (-sx / 2, sy / 2), (-sx / 2, -sy / 2), (sx / 2, -sy / 2))]
        dr.polygon([px(*p) for p in pts], fill=(255, 196, 40), outline=(12, 13, 32), width=2)
        for d in b.get("doors", []):
            side, off = d["side"], d["offset_m"]
            lx, ly = {"+X": (sx / 2 + 2.5, off), "-X": (-sx / 2 - 2.5, -off), "+Y": (-off, sy / 2 + 2.5), "-Y": (off, -sy / 2 - 2.5)}[side]
            a = to_world(pl["x"], pl["y"], pl["yaw"], lx, ly)
            dr.ellipse([px(*a)[0] - 4, px(*a)[1] - 4, px(*a)[0] + 4, px(*a)[1] + 4], fill=(64, 232, 240), outline=(12, 13, 32))
        crops.append((key, b["nome"].split(" (")[0], px(pl["x"], pl["y"])))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    full = im.copy()
    fd = ImageDraw.Draw(full)
    for key, nome, c in crops:
        fd.text((c[0] + 16, c[1] - 14), nome, font=font(30), fill=(255, 255, 255), stroke_width=4, stroke_fill=(12, 13, 32))
    full.save(path)
    tile, head, cols = 440, 40, 3
    rows = (len(crops) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile, rows * (tile + head)), (24, 30, 62))
    sd = ImageDraw.Draw(sheet)
    span = 160.0 * 100 / (2 * half) * S
    for k, (key, nome, c) in enumerate(crops):
        cr = im.crop((int(c[0] - span / 2), int(c[1] - span / 2), int(c[0] + span / 2), int(c[1] + span / 2))).resize((tile, tile), Image.LANCZOS)
        x0, y0 = (k % cols) * tile, (k // cols) * (tile + head)
        sheet.paste(cr, (x0, y0 + head))
        sd.text((x0 + 10, y0 + 8), nome[:30], font=font(22), fill=(255, 214, 92))
    sd.text((10, rows * (tile + head) - 30), "160 m em volta; amarelo = construção, ciano = porta", font=font(18), fill=(196, 206, 236))
    sheet.save(path.replace(".png", "_detalhe.png"))


if __name__ == "__main__":
    res = compute()
    print(json.dumps(res, ensure_ascii=False, indent=1))
