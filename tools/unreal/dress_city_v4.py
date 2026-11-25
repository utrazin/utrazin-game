"""[A-091] Villa Star v4: monta a cidade a partir da planta gerada (assets/work/city_v4/city_layout.json).

RODA NO EDITOR (caixa Cmd, sem Play), DEPOIS de importar o Landscape e rodar setup_city_landscape.py:
  py "E:/game/utrazin-game/tools/unreal/dress_city_v4.py"
Rodar de novo refaz tudo (apaga o que tem a tag CidadeV4 antes).

O que faz em /Game/Levels/Remap/L_Cidade:
  - some com a cidade v3 (tag CidadeV3: chão de caixas, casas em grade, muralha, postes) e com os blocos cinza do F1
  - altura de cada peça lida do próprio heightmap (city_height.r16) + posição/escala do Landscape real
    (nada flutua nem entra no chão; prédio em desnível senta no ponto mais baixo e afunda 10 cm)
  - prédios com função, casas de frente para a rua, postes (luz em candelas, um sim um não), árvores, jardins,
    grupos de barris/placas só onde faz sentido, ruínas, pedras ao pé da muralha, penhascos/árvores fora
  - muralha (400 x 400 na v4, 200 x 200 na v5) com torres e o portão norte com campo de força (M_ForceField do setup_vila_glow.py)
  - move os vendedores (Krug, Ix-Vel, Kaar) e o PlayerStart para os lugares da planta
Coordenadas: planta em metros (x leste, y norte) -> Unreal X = x, Y = -y (a imagem do heightmap cresce para baixo).
Relatório: reports/dress_city_v4.json
"""
import json
import math
import os
import traceback
from array import array

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
EAL = unreal.EditorAssetLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
CITY_MAP = "/Game/Levels/Remap/L_Cidade"
# [A-096] planta v5 (200 x 200 m com relevo) quando existir; a v4 (400 m) fica como reserva
WORK = os.path.join(REPO, "assets", "work", "city_v5")
if not os.path.isfile(os.path.join(WORK, "city_layout.json")):
    WORK = os.path.join(REPO, "assets", "work", "city_v4")
TAG = "CidadeV4"
OLD_TAGS = ("CidadeV3",)
GREY_PREFIXES = ("Quarteirao_", "Predio_", "Balcao_", "Portao_", "Muralha_", "Monumento", "Chao", "Praca")
U = "/Game/Environment/User"
MESH = {
    "armeiro": f"{U}/Vila/SM_BLD_Armeiro", "bancada": f"{U}/Vila/SM_BLD_Bancada", "casa1": f"{U}/Vila/SM_BLD_Casa01",
    "casa2": f"{U}/Vila/SM_BLD_Casa02", "casavila": f"{U}/Construcoes/SM_CON_CasaVila", "cabana": f"{U}/Construcoes/SM_CON_Cabana",
    "posto_loja": f"{U}/Construcoes/SM_CON_PostoLoja", "torre_radio": f"{U}/Construcoes/SM_CON_TorreRadio",
    "barraca": f"{U}/Construcoes/SM_CON_Barraca", "conteiner": f"{U}/Construcoes/SM_CON_Conteiner",
    "muro": f"{U}/Vila/SM_BLD_MuroArena", "torre": f"{U}/Vila/SM_BLD_TorreArena", "portao": f"{U}/Vila/SM_BLD_PortaoArena",
    "nave": f"{U}/Marcos/SM_MRC_NaveResgate", "cristal": f"{U}/Marcos/SM_MRC_Cristal", "cristal_peq": f"{U}/Marcos/SM_MRC_Cristal",
    "arvoremae": f"{U}/Marcos/SM_MRC_ArvoreMae", "colmeia": f"{U}/Marcos/SM_MRC_Colmeia",
    "poste": f"{U}/Props/SM_PRP_Poste", "barril": f"{U}/Props/SM_PRP_Barril", "gerador": f"{U}/Props/SM_PRP_Gerador",
    "placa": f"{U}/Props/SM_PRP_Placa", "barricada": f"{U}/Props/SM_PRP_Barricada", "ossos": f"{U}/Props/SM_PRP_Ossos",
    "arv1": f"{U}/Natureza/SM_NAT_Arvore1", "arv2": f"{U}/Natureza/SM_NAT_Arvore2", "arv3": f"{U}/Natureza/SM_NAT_Arvore3",
    "arv4": f"{U}/Natureza/SM_NAT_Arvore4", "arb1": f"{U}/Natureza/SM_NAT_Arbusto1", "arb2": f"{U}/Natureza/SM_NAT_Arbusto2",
    "arb3": f"{U}/Natureza/SM_NAT_Arbusto3", "flor": f"{U}/Natureza/SM_NAT_Flor", "flor2": f"{U}/Natureza/SM_NAT_Flor2",
    "cogu": f"{U}/Natureza/SM_NAT_Cogumelo", "pedra1": f"{U}/Natureza/SM_NAT_Pedra1", "pedra2": f"{U}/Natureza/SM_NAT_Pedra2",
    "pedra3": f"{U}/Natureza/SM_NAT_Pedra3", "tronco": f"{U}/Natureza/SM_NAT_Tronco", "penhasco": f"{U}/Natureza/SM_NAT_Penhasco",
    "tentaculo": f"{U}/Natureza/SM_NAT_Tentaculo",
}
R = {"steps": [], "warnings": [], "errors": [], "placed": {}}
_cache = {}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[city_v4] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[city_v4] {m}")


def mesh(key):
    if key not in _cache:
        p = MESH.get(key)
        _cache[key] = EAL.load_asset(p) if p and EAL.does_asset_exist(p) else None
        if _cache[key] is None:
            warn(f"malha não encontrada: {key} ({p})")
    return _cache[key]


class Ground:
    """Altura do chão lida do city_height.r16 com a transformação do Landscape do mapa."""

    def __init__(self, land, res):
        self.res = res
        self.h = array("H")
        with open(os.path.join(WORK, "city_height.r16"), "rb") as fh:
            self.h.frombytes(fh.read())
        if len(self.h) != res * res:
            raise RuntimeError(f"city_height.r16 com tamanho errado ({len(self.h)})")
        loc = land.get_actor_location()
        sc = land.get_actor_scale3d()
        self.ox, self.oy, self.oz = loc.x, loc.y, loc.z
        self.sx, self.sy, self.sz = sc.x, sc.y, sc.z

    def z(self, X, Y):
        fx = (X - self.ox) / self.sx
        fy = (Y - self.oy) / self.sy
        fx = min(max(fx, 0.0), self.res - 1.001)
        fy = min(max(fy, 0.0), self.res - 1.001)
        ix, iy = int(fx), int(fy)
        tx, ty = fx - ix, fy - iy
        r = self.res

        def v(i, j):
            return self.h[j * r + i]
        top = v(ix, iy) * (1 - tx) + v(ix + 1, iy) * tx
        bot = v(ix, iy + 1) * (1 - tx) + v(ix + 1, iy + 1) * tx
        val = top * (1 - ty) + bot * ty
        return self.oz + (val - 32768.0) * self.sz / 128.0

    def z_min_footprint(self, X, Y, half_cm):
        pts = [(0, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        return min(self.z(X + dx * half_cm, Y + dy * half_cm) for dx, dy in pts)


def ue(x, y):
    return x * 100.0, -y * 100.0


def ue_yaw(yaw):
    return -yaw


def put(ground, key, x, y, yaw, scale, folder, collide=True, label=None, sink=0.0):
    m = mesh(key)
    if m is None:
        return None
    X, Y = ue(x, y)
    bb = m.get_bounding_box()
    s_max = max(scale) if isinstance(scale, (list, tuple)) else float(scale)
    half = max(bb.max.x - bb.min.x, bb.max.y - bb.min.y) * 0.5 * s_max * 0.6
    Z = (ground.z_min_footprint(X, Y, half) if half > 150 else ground.z(X, Y)) - sink
    a = ACTORS.spawn_actor_from_object(m, unreal.Vector(X, Y, Z), unreal.Rotator(0, 0, ue_yaw(yaw)))
    if a is None:
        return None
    if isinstance(scale, (list, tuple)):
        a.set_actor_scale3d(unreal.Vector(*scale))
    else:
        a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    c = a.static_mesh_component
    c.set_mobility(unreal.ComponentMobility.STATIC)
    c.set_collision_profile_name("BlockAll" if collide else "NoCollision")
    a.tags = [unreal.Name(TAG)]
    a.set_folder_path(unreal.Name(f"Remap/CidadeV4/{folder}"))
    a.set_actor_label(label or f"{key}_{R['placed'].get(key, 0):03d}")
    R["placed"][key] = R["placed"].get(key, 0) + 1
    return a


def light(ground, x, y, z_above, cd, color=(1.0, 0.72, 0.42), radius=2400.0):
    X, Y = ue(x, y)
    a = ACTORS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(X, Y, ground.z(X, Y) + z_above), unreal.Rotator(0, 0, 0))
    lc = a.point_light_component
    lc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    lc.set_editor_property("intensity", float(cd))
    lc.set_editor_property("attenuation_radius", radius)
    lc.set_editor_property("cast_shadows", False)
    lc.set_editor_property("light_color", unreal.Color(r=int(color[0] * 255), g=int(color[1] * 255), b=int(color[2] * 255), a=255))
    a.tags = [unreal.Name(TAG)]
    a.set_folder_path(unreal.Name("Remap/CidadeV4/Luz"))
    return a


def clear_old():
    n = 0
    for a in ACTORS.get_all_level_actors():
        tags = [str(t) for t in a.tags]
        label = a.get_actor_label()
        if TAG in tags or any(t in tags for t in OLD_TAGS) or (label.startswith(GREY_PREFIXES) and isinstance(a, unreal.StaticMeshActor)):
            ACTORS.destroy_actor(a)
            n += 1
    log(f"{n} atores antigos removidos (v3, cinza do F1 e v4 anterior)")


def wall(ground, layout):
    half = float(layout["wall"]["half"])
    gate_w = float(layout["wall"]["gate"]["width"])
    m = mesh("muro")
    t = mesh("torre")
    g = mesh("portao")
    if m is None or t is None:
        return
    bm, bt = m.get_bounding_box(), t.get_bounding_box()
    wx, wy, wz = bm.max.x - bm.min.x, bm.max.y - bm.min.y, bm.max.z - bm.min.z
    tx, ty, tz = bt.max.x - bt.min.x, bt.max.y - bt.min.y, bt.max.z - bt.min.z
    thick, height = 300.0, 820.0
    tscale = max(thick * 1.6 / min(tx, ty), height * 1.3 / tz)
    t_half = min(tx, ty) * tscale * 0.5
    every = float(layout["wall"]["tower_every"])
    sides = (("N", (0, 1)), ("L", (1, 0)), ("S", (0, -1)), ("O", (-1, 0)))
    for name, (ox, oy) in sides:
        ax, ay = (1, 0) if ox == 0 else (0, 1)  # ao longo
        yaw = math.degrees(math.atan2(-oy, -ox))  # frente (+X da malha) para dentro
        # trechos entre torres; no norte, o vão do portão
        cuts = [(-half, half)]
        if name == "N":
            cuts = [(-half, -gate_w / 2 - 1.5), (gate_w / 2 + 1.5, half)]
        n_t = max(1, round(2 * half / every))
        tower_ts = [-half + k * (2 * half / n_t) for k in range(n_t + 1)]
        for (a0, a1) in cuts:
            seg_n = max(1, round((a1 - a0) * 100 / wy))
            seg = (a1 - a0) / seg_n
            for k in range(seg_n):
                tt = a0 + seg * (k + 0.5)
                x = ax * tt + ox * (half + thick / 200)
                y = ay * tt + oy * (half + thick / 200)
                put(ground, "muro", x, y, yaw, [thick / wx, seg * 100 * 1.06 / wy, height / wz], "Muralha", True, sink=30)
        for tt in tower_ts:
            if name == "N" and abs(tt) < gate_w / 2 + t_half / 100 + 2:
                continue
            x = ax * tt + ox * (half + thick / 200)
            y = ay * tt + oy * (half + thick / 200)
            put(ground, "torre", x, y, yaw, tscale, "Muralha", True, sink=20)
    # portão norte com torre dos dois lados e campo de força
    if g is not None:
        bg = g.get_bounding_box()
        gs = gate_w * 100 / (bg.max.y - bg.min.y)
        gy = half + thick / 200
        put(ground, "portao", 0.0, gy, -90.0, gs, "Portao", True, label="Portao_Arena", sink=10)
        for sx in (-1, 1):
            put(ground, "torre", sx * (gate_w / 2 + t_half / 100), gy, -90.0, tscale * 1.1, "Portao", True, sink=20)
        plane = EAL.load_asset("/Engine/BasicShapes/Plane")
        ff = EAL.load_asset("/Game/Materials/Remap/M_ForceField") if EAL.does_asset_exist("/Game/Materials/Remap/M_ForceField") else None
        if plane and ff:
            fh = min((bg.max.z - bg.min.z) * gs * 0.72, 900.0)
            fw = gate_w * 100 * 0.62
            X, Y = ue(0.0, gy)
            a = ACTORS.spawn_actor_from_object(plane, unreal.Vector(X, Y, ground.z(X, Y) + fh / 2 + 5),
                                               unreal.Rotator(roll=0.0, pitch=90.0, yaw=ue_yaw(-90.0)))
            a.set_actor_scale3d(unreal.Vector(fh / 100, fw / 100, 1))
            a.static_mesh_component.set_material(0, ff)
            a.static_mesh_component.set_collision_profile_name("NoCollision")
            a.static_mesh_component.set_editor_property("cast_shadow", False)
            a.tags = [unreal.Name(TAG)]
            a.set_folder_path(unreal.Name("Remap/CidadeV4/Portao"))
            a.set_actor_label("Portao_CampoDeForca")
            light(ground, 0.0, gy - 4, 500, 50.0, (0.35, 0.9, 1.0), 1800)
        else:
            warn("campo de força: rode setup_vila_glow.py antes (M_ForceField)")
    log("muralha com torres e portão norte")


def move_people(ground, layout):
    for name, n in layout["npcs"].items():
        if not n:
            continue
        a = None
        for act in ACTORS.get_all_level_actors():
            if act.get_actor_label() == f"NPC_{name}":
                a = act
                break
        if a is None:
            warn(f"NPC_{name} não está no mapa")
            continue
        X, Y = ue(n["x"], n["y"])
        a.set_actor_location(unreal.Vector(X, Y, ground.z(X, Y) + 130.0), False, False)
        a.set_actor_rotation(unreal.Rotator(0, 0, ue_yaw(n["yaw"])), False)
        log(f"NPC_{name} -> ({n['x']:.0f}, {n['y']:.0f}) m")
    ps = layout["player_start"]
    for act in ACTORS.get_all_level_actors():
        if isinstance(act, unreal.PlayerStart):
            X, Y = ue(ps["x"], ps["y"])
            act.set_actor_location(unreal.Vector(X, Y, ground.z(X, Y) + 120.0), False, False)
            act.set_actor_rotation(unreal.Rotator(0, 0, ue_yaw(ps["yaw"])), False)
            log("PlayerStart na praça, olhando para a nave")


def main():
    if not LES.load_level(CITY_MAP):
        raise RuntimeError(f"não abriu {CITY_MAP}")
    with open(os.path.join(WORK, "city_layout.json"), encoding="utf-8") as fh:
        layout = json.load(fh)
    land = None
    for a in ACTORS.get_all_level_actors():
        if isinstance(a, unreal.LandscapeProxy):
            land = a
            break
    if land is None:
        raise RuntimeError("não há Landscape na L_Cidade: importe city_height.png (docs/design/CIDADE_V4.md)")
    ground = Ground(land, int(layout["landscape"]["res"]))
    clear_old()
    for b in layout["buildings"]:
        put(ground, b["key"], b["x"], b["y"], b["yaw"], b["scale"], b["folder"], b["collide"], label=b["label"], sink=10)
    for h in layout["houses"]:
        put(ground, h["key"], h["x"], h["y"], h["yaw"], h["scale"], "Casas", True, sink=10)
    lights = 0
    for p in layout["props"]:
        put(ground, p["key"], p["x"], p["y"], p["yaw"], p["scale"], p["folder"], p["collide"], sink=5)
        if p.get("light"):
            yaw = math.radians(p["yaw"])
            light(ground, p["x"] + math.cos(yaw) * 0.6, p["y"] + math.sin(yaw) * 0.6, 470, p["light"])
            lights += 1
    # luz fria no monumento
    light(ground, 0, 0, 900, 60.0, (0.4, 0.9, 1.0), 3500)
    log(f"{len(layout['buildings'])} prédios, {len(layout['houses'])} casas, {len(layout['props'])} props, {lights + 1} luzes")
    wall(ground, layout)
    move_people(ground, layout)
    # o NavMesh precisa cobrir o Landscape (os NPCs e, no futuro, moradores andando)
    for a in ACTORS.get_all_level_actors():
        if isinstance(a, unreal.NavMeshBoundsVolume):
            a.set_actor_location(unreal.Vector(0, 0, 0), False, False)
            # [A-096] cobre a cidade e a borda (a caixa padrão tem 2 m): (meia muralha + 40 m) para cada lado
            half_m = float(layout.get("city_half_m", 200.0)) + 40.0
            a.set_actor_scale3d(unreal.Vector(half_m, half_m, 60))
    LES.save_current_level()
    log("L_Cidade salva")


try:
    main()
except Exception as exc:  # noqa: BLE001
    R["errors"].append(str(exc))
    unreal.log_error(f"[city_v4] {exc}\n{traceback.format_exc()[-1500:]}")
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "dress_city_v4.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[city_v4] fim | avisos {len(R['warnings'])} | erros {len(R['errors'])}")
