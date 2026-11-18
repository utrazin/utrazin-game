"""Modelos do usuário (Tripo) na Fase 1 v3: trocas nos POIs, baús, itens, portões, ponte e grupos de cenário.

Usado por tools/unreal/build_l01.py (v3). A parte de PLANO (plan_v3) é Python puro (testável sem a Unreal):
recebe o layout v3 e devolve o que trocar, onde pôr cada modelo e o que mover. A parte que fala com a
Unreal (mesh, ground_z) só roda no editor.

Regras (A-051 em docs/decisions/ASSUMPTIONS.md):
- Tamanho real vem da malha (import_user_assets.py importa em escala 1); aqui a escala é 1, salvo exceções
  marcadas (arco 1,12x para o vão caber a estrada, colmeia 0,8x para caber na ilha, ponte esticada).
- Frente dos modelos = +X do ator. Barracas, casas, loja, bombas e cela olham para o centro do POI.
- Baú da chave DENTRO da barraca (1,1 m atrás do centro, 0,8 m de folga da lona de trás).
- Nada a menos de (meia largura + 4 m) das estradas/trilhas, 30 m dos saltos, fora do rio e do lago.
- Se a malha do usuário não existir (import não rodou), o build usa a peça Quaternius/blockout original.
"""
import json
import math
import os
import random
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
_PIPE = os.path.join(REPO, "tools", "pipeline")
if _PIPE not in sys.path:
    sys.path.append(_PIPE)
import placement_registry as PR  # noqa: E402

# ---------------------------------------------------------------- regras de sobreposição da L01 (A-062)
# Tags: piso (chão de POI), estrutura (blockout e modelos postos à mão), cenario (enfeite conferido),
# item (ITM_*, pequeno e sem colisão), gameplay (baú, item, checkpoint), e da vegetação (scatter_l01_v3.py):
# copa, tronco_arvore, cristal, rocha_grande, rocha, tronco, arbusto, detalhe.
TAGS = ("piso", "estrutura", "cenario", "item", "gameplay", "copa", "tronco_arvore", "cristal",
        "rocha_grande", "rocha", "tronco", "arbusto", "detalhe")
OK_PAIRS = [
    *[("piso", t) for t in TAGS],                       # tudo pode ficar em cima de piso
    *[("item", t) for t in TAGS],                       # galão do lado da bomba, explosivo na boca da colmeia
    ("estrutura", "estrutura"),                         # peças do mesmo POI encostadas de propósito
    ("gameplay", "estrutura"), ("gameplay", "gameplay"), ("gameplay", "copa"),   # baú dentro da barraca
    ("copa", "copa"), ("copa", "tronco_arvore"), ("copa", "rocha"), ("copa", "tronco"),
    ("copa", "arbusto"), ("copa", "detalhe"),           # o que é baixo pode ficar debaixo da copa
    ("arbusto", "arbusto"), ("arbusto", "detalhe"), ("detalhe", "detalhe"),
]


def new_registry():
    """Registro vazio com as regras da L01 (cm, coordenadas da Unreal)."""
    reg = PR.Registry()
    for a, b in OK_PAIRS:
        reg.allow(a, b)
    return reg


FLOORS = ("Ruins/Floor_SquareLarge", "SM_StonePlatform", "SM_StonePlatformTall", "SM_BridgePlanks")


def piece_radius_cm(e):
    """Raio aproximado (cm) de uma peça do layout (o mesmo critério do scatter_l01_v3.py)."""
    s = e.get("scale", 1.0)
    s = max(s[0], s[1]) if isinstance(s, list) else float(s)
    r = e.get("q") or e.get("mesh") or e.get("engine") or ""
    base = 0.5 if r in ("Cube", "Cone", "Cylinder", "Sphere") else (1.6 if "/" in r else 2.5)
    return 100.0 * base * s
CATALOG = os.path.join(REPO, "assets", "raw", "tripo", "tripo_catalog.json")
PROCESSED = os.path.join(REPO, "assets", "work", "tripo", "tripo_processed.json")
ROOT = "/Game/Environment/User"

_CAT = None
_PROC = None


def catalog():
    global _CAT
    if _CAT is None:
        _CAT = {i["name"]: i for i in json.load(open(CATALOG, encoding="utf-8"))["items"]}
    return _CAT


def dims_m(name):
    """Medidas finais (m) do modelo processado; None se não houver."""
    global _PROC
    if _PROC is None:
        _PROC = json.load(open(PROCESSED, encoding="utf-8")) if os.path.exists(PROCESSED) else {}
    return (_PROC.get(name) or {}).get("dims_m")


def asset_path(name):
    base = name.replace("_Base", "").replace("_Tampa", "")
    return f"{ROOT}/{catalog()[base]['category']}/SM_{name}"


# ====================================================================== geometria (cm, graus; Unreal: x leste, y sul)
def fwd(yaw):
    r = math.radians(yaw)
    return math.cos(r), math.sin(r)


def offset(x, y, yaw, f=0.0, side=0.0):
    """Ponto a f cm para a frente (+X local) e side cm para o lado (+Y local) de um ator com esse yaw."""
    c, s = fwd(yaw)
    return x + c * f - s * side, y + s * f + c * side


def yaw_to(x, y, tx, ty):
    return math.degrees(math.atan2(ty - y, tx - x))


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class Clearance:
    """Distâncias para estradas, trilhas, rio, lago e saltos (o que não pode ser bloqueado)."""

    def __init__(self, L):
        self.routes = []
        for key, r in L["routes"].items():
            pts = [(s[0], s[1]) for s in r["samples"]]
            self.routes.append((key, r["half_width_m"] * 100.0, pts))
        self.boxes = []
        for h in L["hazards"]:
            self.boxes.append((h["loc"][0], h["loc"][1], h["yaw"], h["box_extent_cm"][0], h["box_extent_cm"][1]))
        self.jumps = []
        for j in L.get("jumps", []):
            for k in ("ramp", "landing"):
                self.jumps.append((j[k]["loc"][0], j[k]["loc"][1]))
        river = L.get("river") or {}
        self.river = [(s[0], s[1]) for s in river.get("samples", [])]
        self.river_half = river.get("half_width_m", 20) * 100.0

    def road_dist(self, x, y):
        """Distância (cm) até a BORDA da rota mais próxima (negativa = em cima da rota)."""
        best = 1e12
        for _, half, pts in self.routes:
            for a, b in zip(pts, pts[1:]):
                d = seg_dist(x, y, a[0], a[1], b[0], b[1]) - half
                if d < best:
                    best = d
        return best

    def nearest_on(self, key, x, y):
        """(ponto mais próximo, yaw da tangente) numa rota."""
        pts = next(p for k, _, p in self.routes if k == key)
        best = (1e12, None, 0.0)
        for a, b in zip(pts, pts[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy or 1.0
            t = max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / L2))
            px, py = a[0] + t * dx, a[1] + t * dy
            d = math.hypot(x - px, y - py)
            if d < best[0]:
                best = (d, (px, py), math.degrees(math.atan2(dy, dx)))
        return best[1], best[2]

    def in_hazard(self, x, y, margin):
        for hx, hy, yaw, ex, ey in self.boxes:
            c, s = fwd(-yaw)
            lx, ly = (x - hx) * c - (y - hy) * s, (x - hx) * s + (y - hy) * c
            if abs(lx) < ex + margin and abs(ly) < ey + margin:
                return True
        for a, b in zip(self.river, self.river[1:]):
            if seg_dist(x, y, a[0], a[1], b[0], b[1]) < self.river_half + margin:
                return True
        return False

    def ok(self, x, y, radius_cm, road_margin=400.0):
        if self.road_dist(x, y) < radius_cm + road_margin:
            return False
        if self.in_hazard(x, y, radius_cm + 300.0):
            return False
        return all(math.hypot(x - jx, y - jy) > 3000 + radius_cm for jx, jy in self.jumps)


def radius_cm(name, scale=1.0):
    d = dims_m(name) or [1, 1, 1]
    return 50.0 * max(d[0], d[1]) * scale


# ====================================================================== o plano
def plan_v3(L, have=None, interiors=True):
    """have(name) -> bool diz se a malha do usuário existe (no editor). Sem have: assume que todas existem.
    Retorna dict com: skip {(poi, idx)}, hide {(poi, idx)}, place [..], chests {label: ..}, pickups {label: ..},
    pickup_display {tipo: nome}, gates {label: ..}, bridge {..}, barricade_meshes [..], cage, notes [..]."""
    have = have or (lambda n: True)
    C = Clearance(L)
    P = {"skip": set(), "hide": set(), "place": [], "chests": {}, "pickups": {}, "gates": {}, "bridge": None,
         "barricade_meshes": [n for n in ("PRP_CarroBatido1", "PRP_CarroBatido2", "PRP_Barricada") if have(n)],
         "cage": "CON_Cela" if have("CON_Cela") else None, "notes": [],
         "pickup_display": {k: v for k, v in (("HEALTH", "ITM_KitMedico"), ("AMMO", "ITM_Municao"),
                                                 ("WEAPON_MELEE", "ARM_Graveto"), ("WEAPON_SHOTGUN", "ARM_Escopeta"))
                            if have(v)}}
    poi = {p["key"]: p for p in L["pois"]}
    # [A-062] registro de footprints: o que já existe (blockout dos POIs, baús, itens, checkpoints) entra antes;
    # cada modelo posto entra depois. Enfeites (check=True) não podem cair em cima de nada disso.
    reg = new_registry()
    P["registry"] = reg
    for pz in L["pois"]:
        for i, e in enumerate(pz["pieces"]):
            ref0 = e.get("q") or e.get("mesh") or e.get("engine") or ""
            reg.add(e["loc"][0], e["loc"][1], piece_radius_cm(e), "piso" if ref0 in FLOORS else "estrutura",
                    f"blockout {pz['key']}: {ref0}", f"{pz['key']}[{i}]", force=True)
    for key, r in (("chests", 120.0), ("pickups", 80.0), ("checkpoints", 300.0)):
        for e in L.get(key, []):
            reg.add(e["loc"][0], e["loc"][1], r, "gameplay", key, e.get("label", ""), force=True)
    rejected = []

    def put(name, x, y, yaw, folder, scale=1.0, nocol=False, cull_m=0, pitch=0.0, roll=0.0, z=None, dz=0.0,
            check=False, hidden=False, label=None):
        if not have(name):
            return False
        r = radius_cm(name, scale if not isinstance(scale, list) else max(scale[:2]))
        tag = "item" if name.startswith("ITM_") else ("cenario" if check else "estrutura")
        if check:
            if not C.ok(x, y, r):
                return False
            hit = reg.conflict(x, y, r, tag=tag)
            if hit is not None:
                rejected.append(f"{name} em {folder} bate em {hit.id or hit.tag}")
                return False
        P["place"].append({"name": name, "x": x, "y": y, "yaw": yaw, "scale": scale, "pitch": pitch, "roll": roll,
                           "z": z, "dz": dz, "folder": folder, "nocol": nocol, "cull_m": cull_m, "hidden": hidden,
                           "label": label})
        reg.add(x, y, r, tag, folder, label or name, force=True)
        return True

    def swap(key, idx, name, yaw=None, scale=1.0, road=False, at=None, **kw):
        """Troca a peça idx do POI pelo modelo do usuário no mesmo lugar (at = outro ponto (x, y)).
        road=True: se o modelo do usuário (maior que o original) encostar numa estrada/trilha, fica o original."""
        e = poi[key]["pieces"][idx]
        x, y = at or (e["loc"][0], e["loc"][1])
        if road and C.road_dist(x, y) < radius_cm(name, scale) + 100.0:
            P["notes"].append(f"{key}[{idx}] {name}: perto da rota, ficou a peça original")
            return False
        if put(name, x, y, e["rot"][1] if yaw is None else yaw, f"L01/POI/Z{poi[key]['zone']}_{key}",
               scale, **kw):
            P["skip"].add((key, idx))
            return True
        return False

    def ref(e):
        return e.get("q") or e.get("mesh") or e.get("engine")

    # ---------------- Z0 Acampamento: barracas de verdade (abertura para o centro), baú da chave dentro
    k = "Acampamento"
    cx, cy = poi[k]["loc"][0], poi[k]["loc"][1]
    chest = next(c for c in L["chests"] if c["label"] == "Bau_ChaveBuggy")
    tents = [i for i, e in enumerate(poi[k]["pieces"]) if ref(e) == "Cone"]
    key_tent = min(tents, key=lambda i: math.hypot(poi[k]["pieces"][i]["loc"][0] - chest["loc"][0],
                                                   poi[k]["pieces"][i]["loc"][1] - chest["loc"][1]))
    for i in tents:
        e = poi[k]["pieces"][i]
        ty = yaw_to(e["loc"][0], e["loc"][1], cx, cy)
        if swap(k, i, "CON_Barraca", yaw=ty, cull_m=900) and i == key_tent:
            bx, by = offset(e["loc"][0], e["loc"][1], ty, f=-110.0)
            # baú: frente (+Y local do AJRLootChest) para a abertura da barraca
            P["chests"]["Bau_ChaveBuggy"] = {"x": bx, "y": by, "yaw": ty - 90.0, "kind": "bau", "ground_from": (e["loc"][0], e["loc"][1])}
            P["notes"].append(f"Bau_ChaveBuggy dentro da barraca {i} ({bx:.0f}, {by:.0f})")
    for i, e in enumerate(poi[k]["pieces"]):
        if ref(e) == "ZombieKit/Barrel":
            swap(k, i, "PRP_Barril", cull_m=300)
    camp = [("PRP_Gerador", -1200, -900, 0), ("PRP_Poste", 900, -1400, 0), ("PRP_Poste", -1500, 1100, 0),
            ("PRP_Placa", 300, -2700, 0), ("CON_Conteiner", -2600, -1500, 30), ("PRP_Barril", -1000, -1050, 0),
            ("PRP_Barril", -1080, -950, 40), ("NAT_Arbusto2", 1800, 1900, 0), ("NAT_Pedra2", -2300, 2400, 20)]
    for n, dx, dy, yw in camp:
        x, y = cx + dx, cy + dy
        put(n, x, y, yaw_to(x, y, cx, cy) + yw, "L01/POI/Z0_Acampamento", cull_m=500, check=True)

    # ---------------- Z0 Nave de resgate caída
    k = "NaveQueda"
    for i, e in enumerate(poi[k]["pieces"]):
        if ref(e) == "SpaceKit/Spaceship_FinnTheFrog":
            swap(k, i, "MRC_NaveResgate", yaw=e["rot"][1], roll=0.0)

    # ---------------- Z1 Arco: centralizado na estrada, vão ao longo da estrada
    k = "ArcoPedra"
    e = poi[k]["pieces"][0]
    (ax, ay), tang = C.nearest_on("main", e["loc"][0], e["loc"][1])
    if put("MRC_Arco", ax, ay, tang, "L01/POI/Z1_ArcoPedra", scale=1.12):
        P["skip"].add((k, 0))

    # ---------------- Z1 destroços (carros batidos no lugar dos Quaternius)
    for k, n in (("Destroco_Z1_1", "PRP_CarroBatido1"), ("Destroco_Z1_2", "PRP_CarroBatido2"),
                 ("Destroco_Z1_3", "PRP_CarroBatido1")):
        swap(k, 0, n, yaw=poi[k]["pieces"][0]["rot"][1] + (160 if k.endswith("3") else 0), cull_m=800)

    # ---------------- Z2 Posto: cobertura + 2 bombas (uma é o "baú" do galão) + loja + torre
    k = "Posto"
    pcs = poi[k]["pieces"]
    cols = [e for e in pcs if ref(e) == "Ruins/Column_Square"]
    gx = sum(e["loc"][0] for e in cols) / max(1, len(cols))
    gy = sum(e["loc"][1] for e in cols) / max(1, len(cols))
    base_yaw = cols[0]["rot"][1] if cols else 0.0
    if put("CON_PostoCobertura", gx, gy, base_yaw + 90.0, "L01/POI/Z2_Posto"):
        for i, e in enumerate(pcs):
            if ref(e) in ("Ruins/Column_Square", "Ruins/Floor_SquareLarge", "Cube"):
                P["skip"].add((k, i))
        cubes = [e for e in pcs if ref(e) == "Cube"]
        pump_yaw = base_yaw - 90.0
        galao = next((c for c in L["chests"] if c["label"] == "Bomba_Galao"), None)
        if cubes:
            # bomba mais perto do baú do galão = o próprio baú (AJRLootChest com a malha da bomba)
            cubes.sort(key=lambda e: math.hypot(e["loc"][0] - galao["loc"][0], e["loc"][1] - galao["loc"][1]) if galao else 0)
            if galao and have("CON_PostoBomba"):
                P["chests"]["Bomba_Galao"] = {"x": cubes[0]["loc"][0], "y": cubes[0]["loc"][1], "yaw": pump_yaw, "kind": "bomba"}
                gx2, gy2 = offset(cubes[0]["loc"][0], cubes[0]["loc"][1], pump_yaw, f=40.0, side=70.0)
                put("ITM_Galao", gx2, gy2, pump_yaw + 25, "L01/POI/Z2_Posto", nocol=True, cull_m=200)
            for e in cubes[1:]:
                put("CON_PostoBomba", e["loc"][0], e["loc"][1], pump_yaw, "L01/POI/Z2_Posto", cull_m=500)
    for i, e in enumerate(pcs):
        r = ref(e)
        if r == "SpaceKit/Building_L":
            # loja 6 m a leste do prédio antigo: a trilha para a sala trancada passa a oeste dele
            lx, ly = e["loc"][0] + 600.0, e["loc"][1]
            sy = yaw_to(lx, ly, gx, gy)
            if swap(k, i, "CON_PostoLoja", yaw=sy, at=(lx, ly)):
                # itens que estavam dentro do prédio antigo vão para a calçada da loja (a loja nova é fechada)
                fx, fy = offset(lx, ly, sy, f=50.0 * (dims_m("CON_PostoLoja") or [8.5])[0] + 250.0)
                for label, side in (("Pickup_Medkit_Posto", 250.0), ("Pickup_Municao_Posto", -250.0)):
                    px, py = offset(fx, fy, sy, side=side)
                    P["pickups"][label] = {"x": px, "y": py}
                gx3, gy3 = offset(lx, ly, sy, f=0.0, side=(50.0 * (dims_m("CON_PostoLoja") or [0, 10])[1] + 150.0))
                put("PRP_Gerador", gx3, gy3, sy + 90.0, "L01/POI/Z2_Posto", cull_m=400, check=True)
        elif r == "SpaceKit/Roof_Radar":
            P["skip"].add((k, i))
        elif r == "ZombieKit/StreetLights":
            swap(k, i, "PRP_Poste", cull_m=600)
        elif r == "ZombieKit/Barrel":
            swap(k, i, "PRP_Barril", cull_m=300)
        elif r == "ZombieKit/Container_Red":
            swap(k, i, "CON_Conteiner", cull_m=700, road=True)
        elif r == "ZombieKit/Vehicle_Truck":
            swap(k, i, "PRP_CarroBatido2", cull_m=700, road=True)
        elif r == "ZombieKit/TownSign":
            sx, sy2 = offset(e["loc"][0], e["loc"][1], e["rot"][1], side=500.0)
            put("PRP_Placa", sx, sy2, e["rot"][1], "L01/POI/Z2_Posto", cull_m=300, check=True)
    k = "TorreRadio"
    swap(k, 0, "CON_TorreRadio")

    # ---------------- Z3 Árvore-mãe
    k = "ArvoreMae"
    for i, e in enumerate(poi[k]["pieces"]):
        if ref(e) == "Nature/TwistedTree_2":
            swap(k, i, "MRC_ArvoreMae")
    mx, my = poi[k]["loc"][0], poi[k]["loc"][1]
    rnd = random.Random(31)
    for j in range(10):
        a = j * 36 + rnd.uniform(-10, 10)
        d = rnd.uniform(2100, 2800)
        x, y = mx + math.cos(math.radians(a)) * d, my + math.sin(math.radians(a)) * d
        put(("NAT_Cogumelo", "NAT_Flor", "NAT_Cogumelos", "NAT_Flor2", "NAT_Tentaculo")[j % 5], x, y, rnd.uniform(0, 360),
            "L01/POI/Z3_ArvoreMae", nocol=(j % 5 != 0), cull_m=400, check=True)

    # ---------------- Z4 Ponte: ponte de corda do usuário por cima do tabuleiro (visual), corrimãos escondidos
    k = "Ponte"
    rails = [(i, e) for i, e in enumerate(poi[k]["pieces"]) if ref(e) == "SM_GuardRail"]
    if rails and have("CON_Ponte"):
        ys = sorted(rails, key=lambda t: t[1]["loc"][1])
        n_end = [e for _, e in ys if abs(e["loc"][1] - ys[-1][1]["loc"][1]) < 200]
        s_end = [e for _, e in ys if abs(e["loc"][1] - ys[0][1]["loc"][1]) < 200]
        a = [sum(e["loc"][j] for e in n_end) / len(n_end) for j in range(3)]
        b = [sum(e["loc"][j] for e in s_end) / len(s_end) for j in range(3)]
        xs = sorted(e["loc"][0] for _, e in rails)
        width = (xs[-1] - xs[0])                          # distância entre os corrimãos (cm)
        length = math.dist(a[:2], b[:2]) + 800.0
        d = dims_m("CON_Ponte") or [14.0, 5.18, 4.52]
        sz = 1.6
        P["bridge"] = {"a": a, "b": b, "scale": [length / (d[0] * 100.0), width / 280.0, sz],
                       "deck_end_m": 2.2 * sz, "note": "tábuas da ponte de corda 15 cm abaixo do tabuleiro nas pontas"}
        for i, _ in rails:
            P["hide"].add((k, i))

    # ---------------- Z4 Colmeia: na ilha, boca virada para os pilares (oeste); baú na boca
    k = "Colmeia"
    hx, hy = poi[k]["loc"][0] + 700.0, poi[k]["loc"][1]
    hs = 0.8
    hd = dims_m("MRC_Colmeia") or [13.4, 15, 13.2]
    if put("MRC_Colmeia", hx, hy, 180.0, "L01/POI/Z4_Colmeia", scale=hs):
        half_x, half_y = 50.0 * hd[0] * hs + 80.0, 50.0 * hd[1] * hs + 80.0
        for i, e in enumerate(poi[k]["pieces"]):
            if abs(e["loc"][0] - hx) < half_x and abs(e["loc"][1] - hy) < half_y:
                P["skip"].add((k, i))
        mouth_x = hx - 50.0 * hd[0] * hs
        P["chests"]["Bau_Colmeia"] = {"x": mouth_x - 130.0, "y": hy, "yaw": 180.0 - 90.0, "kind": "bau"}
        put("ITM_Explosivo", mouth_x - 130.0, hy + 120.0, 30.0, "L01/POI/Z4_Colmeia", nocol=True, cull_m=200)

    # ---------------- Z6 Vila: casas decorativas fechadas, cercas, barricadas, portão com vão a pé
    k = "Vila"
    vx, vy = poi[k]["loc"][0], poi[k]["loc"][1]
    for i, e in enumerate(poi[k]["pieces"]):
        r = ref(e)
        ex, ey = e["loc"][0], e["loc"][1]
        face = yaw_to(ex, ey, vx, vy)
        ring = yaw_to(vx, vy, ex, ey)            # ângulo da peça em volta do centro = yaw da cerca (Y local tangente)
        if r in ("SpaceKit/House_Long", "SM_FarmhouseRuin"):
            swap(k, i, "CON_CasaVila", yaw=face)
        elif r == "SpaceKit/House_Cylinder":
            swap(k, i, "CON_Cabana", yaw=face)
        elif r == "SM_Fence" and have("CON_Cerca"):
            P["skip"].add((k, i))
            for off_cm in (-400.0, 0.0, 400.0):
                fx, fy = offset(ex, ey, ring, side=off_cm)
                put("CON_Cerca", fx, fy, ring, "L01/POI/Z6_Vila", cull_m=500)
        elif r == "SM_Barricade":
            swap(k, i, "PRP_Barricada", yaw=ring, cull_m=500)
        elif r == "ZombieKit/Barrel":
            swap(k, i, "PRP_Barril", cull_m=300)
    for n, a, d in (("PRP_Poste", 20, 2300), ("PRP_Poste", 200, 2300), ("PRP_Gerador", 110, 1700),
                    ("PRP_Placa", 300, 3000), ("PRP_Ossos", 250, 4000), ("PRP_CarroBatido1", 160, 3600)):
        x, y = vx + math.cos(math.radians(a)) * d, vy + math.sin(math.radians(a)) * d
        put(n, x, y, yaw_to(x, y, vx, vy), "L01/POI/Z6_Vila", cull_m=600, check=True)
    k = "DiscoVoador"
    for i, e in enumerate(poi[k]["pieces"]):
        if ref(e) == "SM_UFOWreck":
            swap(k, i, "MRC_DiscoVoador", yaw=e["rot"][1])
    for g in L["gates"]:
        if g["type"] == "car_block" and have("CON_Portao"):
            # portão (6 m) + barricada (3 m) com vão de 1,7 m no meio: a pé passa, o carro não
            P["gates"][g["label"]] = [("CON_Portao", -385.0), ("PRP_Barricada", 235.0), ("CON_Cerca", 585.0)]
            for n, side in P["gates"][g["label"]]:
                x, y = offset(g["loc"][0], g["loc"][1], g["yaw"], side=side)
                put(n, x, y, g["yaw"], "L01/Gameplay/Portoes", cull_m=600)
        elif g["type"] == "explosive" and have("NAT_Arvore3"):
            P["gates"][g["label"]] = {"mesh": "NAT_Arvore3", "scale": 2.0, "rel_loc": [0, -800, 120], "rel_rot": [-88, 90, 0]}

    # ---------------- Z7 Portão norte
    k = "PortaoNorte"
    e = poi[k]["pieces"][0]
    for n, side, f in (("PRP_Poste", 1500, 600), ("PRP_Poste", -1500, 600), ("PRP_Placa", 1900, 900),
                       ("PRP_Barricada", -2200, 300), ("PRP_Ossos", 2600, -900)):
        x, y = offset(e["loc"][0], e["loc"][1], e["rot"][1], f=f, side=side)
        put(n, x, y, e["rot"][1] + 180, "L01/POI/Z7_PortaoNorte", cull_m=600, check=True)

    # ---------------- grupos de cenário ao longo das rotas (para as zonas parecerem habitadas)
    groups = {
        "alerta": [("PRP_Placa", 0, 0, 0), ("PRP_Barricada", 350, 200, 10), ("PRP_Barril", -250, 250, 0), ("PRP_Barril", -330, 150, 50)],
        "destroco": [("PRP_CarroBatido1", 0, 0, 0), ("PRP_Ossos", 600, 500, 30), ("NAT_Pedra2", -500, 400, 0), ("NAT_Arbusto2", 300, -450, 0)],
        "capotado": [("PRP_CarroBatido2", 0, 0, 0), ("PRP_Barril", 450, 300, 0), ("NAT_Pedra1", -400, -300, 0), ("NAT_Pedra1", -250, 420, 0)],
        "deserto": [("NAT_Arvore3", 0, 0, 0), ("PRP_Ossos", 650, 250, 60), ("NAT_Pedra2", -450, -350, 0), ("NAT_Pedra1", 300, -500, 0)],
        "pedras": [("NAT_Pedra3", 0, 0, 0), ("NAT_Pedra2", 650, 300, 40), ("NAT_Pedra1", -500, 450, 0), ("NAT_Pedra1", 450, -500, 0)],
        "cristal": [("MRC_Cristal", 0, 0, 0), ("NAT_Arbusto2", 600, 200, 0), ("NAT_Pedra2", -550, 300, 0)],
        "cogumelos": [("NAT_Cogumelo", 0, 0, 0), ("NAT_Cogumelos", 450, 200, 0), ("NAT_Cogumelos", -350, 380, 0), ("NAT_Flor", 250, -400, 0), ("NAT_Flor2", -300, -300, 0)],
        "acampado": [("PRP_Gerador", 0, 0, 0), ("PRP_Poste", 350, 250, 0), ("PRP_Barril", -300, 200, 0), ("ITM_Galao", -150, -250, 0)],
        "onibus": [("PRP_Onibus", 0, 0, 0), ("PRP_Barricada", 700, 400, 15), ("PRP_Placa", -700, 500, 0)],
        "tentaculos": [("NAT_Tentaculo", 0, 0, 0), ("NAT_Tentaculo", 300, 250, 40), ("NAT_Arbusto3", -350, 200, 0), ("NAT_Flor", 200, -300, 0)],
    }
    by_zone = {0: ["acampado", "alerta"], 1: ["destroco", "deserto", "pedras", "cristal", "capotado"],
               2: ["alerta", "capotado", "acampado"], 3: ["cogumelos", "tentaculos", "cristal", "destroco"],
               4: ["cogumelos", "tentaculos", "pedras"], 5: ["onibus", "destroco", "pedras", "alerta", "capotado", "deserto"],
               6: ["alerta", "acampado", "cogumelos"], 7: ["deserto", "pedras", "cristal", "capotado"]}
    zones = {z["id"]: z for z in L["zones"]}
    rnd = random.Random(7)
    count = {}
    for key, half, pts in C.routes:
        step = 9 if key == "main" else 7                    # amostras a cada ~20 m: um grupo a cada ~140-180 m
        for j in range(3, len(pts) - 3, step):
            x0, y0 = pts[j]
            zid = min(zones, key=lambda z: math.hypot(zones[z]["center"][0] - x0, zones[z]["center"][1] - y0)
                      / max(1.0, zones[z]["radius_cm"]))
            if any(math.hypot(p["loc"][0] - x0, p["loc"][1] - y0) < 3500 for p in L["pois"]):
                continue
            kinds = by_zone.get(zid, ["pedras"])
            g = kinds[(j // step + len(key)) % len(kinds)]
            if g == "onibus" and count.get("onibus", 0) >= 2:
                g = "destroco"
            tang = math.degrees(math.atan2(pts[j + 1][1] - pts[j - 1][1], pts[j + 1][0] - pts[j - 1][0]))
            side = 1 if (j // step) % 2 == 0 else -1
            dist = half + rnd.uniform(1400, 2600)
            gx, gy = offset(x0, y0, tang, side=side * dist)
            gyaw = tang + (90 if side > 0 else -90) + rnd.uniform(-25, 25)
            placed = 0
            for n, ox, oy, yw in groups[g]:
                x, y = offset(gx, gy, gyaw, f=ox, side=oy)
                yaw = gyaw + yw if n not in ("PRP_Onibus", "PRP_CarroBatido1", "PRP_CarroBatido2") else tang + rnd.uniform(-30, 30)
                small = n.startswith(("NAT_Flor", "NAT_Cogumelos", "NAT_Pedra1", "NAT_Arbusto", "NAT_Tentaculo", "ITM_"))
                if put(n, x, y, yaw, f"L01/Cenario/Grupos/Z{zid}", nocol=small, cull_m=250 if small else 700, check=True):
                    placed += 1
            if placed:
                count[g] = count.get(g, 0) + 1
    P["group_counts"] = count
    # [A-070] construções com interior (assets/work/interiors): trocam modelos/blockout, ocupam a área, levam baús
    if interiors:
        try:
            import l01_interiors  # noqa: E402
            l01_interiors.apply_to_plan(P, L, reg, have)
        except Exception as exc:  # noqa: BLE001
            P["notes"].append(f"interiores não aplicados: {exc}")
    else:
        P["interiors"] = []
    # peças de blockout trocadas ou puladas saem do registro (o modelo do usuário já ocupa o lugar)
    reg.remove_ids(f"{k_}[{i_}]" for k_, i_ in P["skip"])
    P["placement_rejected"] = rejected
    return P


# ====================================================================== parte da Unreal
def unreal_mod():
    import unreal  # noqa: E402
    return unreal


def mesh(name):
    """StaticMesh do usuário ou None (import_user_assets.py não rodou)."""
    unreal = unreal_mod()
    try:
        p = asset_path(name)
    except KeyError:
        return None
    eal = unreal.EditorAssetLibrary
    return eal.load_asset(p) if eal.does_asset_exist(p) else None


def ground_z_batch(points, terrain_actors):
    """Altura do TERRENO (ignora tudo que não é terreno) para cada (x, y). None se não acertar."""
    unreal = unreal_mod()
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    keep = set(a.get_path_name() for a in terrain_actors)
    ignore = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
              if a.get_path_name() not in keep]
    out = []
    for x, y in points:
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 100000), unreal.Vector(x, y, -100000),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                                     unreal.DrawDebugTrace.NONE, True)
        if isinstance(hit, tuple):
            hit = hit[-1]
        t = hit.to_tuple() if hit else None
        out.append(round(t[5].z, 1) if t and t[0] else None)
    return out
