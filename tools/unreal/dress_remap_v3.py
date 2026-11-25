"""[A-086] Remap v3: veste a cidade e a arena com os modelos do usuário (sem cinza, sem parede invisível).

RODA NO EDITOR (caixa Cmd, sem Play), DEPOIS de compilar e de importar os modelos (run_v3_setup.py faz tudo):
  py "E:/game/utrazin-game/tools/unreal/dress_remap_v3.py"

Cidade (/Game/Levels/Remap/L_Cidade), tudo com a tag CidadeV3 (rodar de novo refaz):
  - some com os blocos cinza (quarteirões, prédios, balcões, portão, muralha e monumento do F1)
  - chão de grama alienígena, praça de concreto, 2 avenidas de asfalto
  - Armeiro (Krug) = SM_BLD_Armeiro, Bancada (Ix-Vel) = SM_BLD_Bancada, Portão (Kaar) = SM_BLD_PortaoArena
  - monumento = nave de resgate caída (MRC_NaveResgate) no meio da praça
  - quarteirões com casas do usuário (BLD_Casa01/02, CasaVila, Cabana), postes com luz, árvores, barris
  - muralha da vila (BLD_MuroArena + BLD_TorreArena) em volta, fechada, com colisão da própria malha
Arena (/Game/Levels/Remap/L_Arena_F1): chão maior (420 m) de areia vermelha (o resto vem do AJRArenaGenerator).
Céu alienígena e exposição fixa nos dois mapas: setup_alien_sky.py (chamado no fim).
Relatório: reports/dress_remap_v3.json
"""
import json
import math
import os
import random
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
EAL = unreal.EditorAssetLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
CITY_MAP = "/Game/Levels/Remap/L_Cidade"
ARENA_MAP = "/Game/Levels/Remap/L_Arena_F1"
TAG = "CidadeV3"
U = "/Game/Environment/User"
MAT = f"{U}/Materials"
M = {
    "armeiro": f"{U}/Vila/SM_BLD_Armeiro", "bancada": f"{U}/Vila/SM_BLD_Bancada", "portao": f"{U}/Vila/SM_BLD_PortaoArena",
    "muro": f"{U}/Vila/SM_BLD_MuroArena", "torre": f"{U}/Vila/SM_BLD_TorreArena",
    "casa1": f"{U}/Vila/SM_BLD_Casa01", "casa2": f"{U}/Vila/SM_BLD_Casa02",
    "casavila": f"{U}/Construcoes/SM_CON_CasaVila", "cabana": f"{U}/Construcoes/SM_CON_Cabana",
    "nave": f"{U}/Marcos/SM_MRC_NaveResgate", "poste": f"{U}/Props/SM_PRP_Poste", "barril": f"{U}/Props/SM_PRP_Barril",
    "gerador": f"{U}/Props/SM_PRP_Gerador", "placa": f"{U}/Props/SM_PRP_Placa",
    "arv1": f"{U}/Natureza/SM_NAT_Arvore1", "arv3": f"{U}/Natureza/SM_NAT_Arvore3", "arv4": f"{U}/Natureza/SM_NAT_Arvore4",
    "arb1": f"{U}/Natureza/SM_NAT_Arbusto1", "arb2": f"{U}/Natureza/SM_NAT_Arbusto2", "flor": f"{U}/Natureza/SM_NAT_Flor",
    "cogu": f"{U}/Natureza/SM_NAT_Cogumelo", "pedra2": f"{U}/Natureza/SM_NAT_Pedra2",
}
GREY_PREFIXES = ("Quarteirao_", "Predio_", "Balcao_", "Portao_", "Muralha_", "Monumento")
R = {"steps": [], "warnings": [], "errors": [], "placed": {}}
_cache = {}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[dress_v3] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[dress_v3] {m}")


def err(where, exc):
    R["errors"].append(f"{where}: {exc}")
    unreal.log_error(f"[dress_v3] {where}: {exc}\n{traceback.format_exc()[-1200:]}")


def asset(path):
    if path not in _cache:
        name = path.rsplit("/", 1)[1]
        full = f"{path}.{name}"
        _cache[path] = EAL.load_asset(full) if EAL.does_asset_exist(path) else None
        if _cache[path] is None:
            warn(f"não achei {path}")
    return _cache[path]


def find_mesh(key):
    p = M[key]
    a = asset(p)
    if a is None and key == "nave":
        # a pasta da nave pode variar entre importações
        for cand in EAL.list_assets(U, recursive=True, include_folder=False):
            if cand.split(".")[0].endswith("SM_MRC_NaveResgate"):
                a = EAL.load_asset(cand)
                break
    return a


def put(key, x, y, yaw=0.0, scale=1.0, folder="CidadeV3", label=None, z=0.0, collide=True):
    """Malha com origem no centro de baixo apoiada em z."""
    mesh = find_mesh(key)
    if mesh is None:
        return None
    a = ACTORS.spawn_actor_from_object(mesh, unreal.Vector(x, y, z), unreal.Rotator(0.0, 0.0, yaw))
    if a is None:
        return None
    if isinstance(scale, (tuple, list)):
        a.set_actor_scale3d(unreal.Vector(*scale))
    else:
        a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    c = a.static_mesh_component
    c.set_collision_profile_name("BlockAll" if collide else "NoCollision")
    a.tags = [unreal.Name(TAG)]
    a.set_folder_path(unreal.Name(f"Remap/{folder}"))
    a.set_actor_label(label or f"{key}_{R['placed'].get(key, 0):03d}")
    R["placed"][key] = R["placed"].get(key, 0) + 1
    return a


def light(x, y, z, color=(1.0, 0.72, 0.42), intensity=40.0, radius=2400.0):
    # [A-088] unidade explícita: sem ela 5000 virava 5000 candelas e a cidade estourava de branco
    a = ACTORS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(x, y, z), unreal.Rotator(0, 0, 0))
    lc = a.point_light_component
    lc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    lc.set_editor_property("intensity", intensity)
    lc.set_editor_property("cast_shadows", False)
    lc.set_editor_property("attenuation_radius", radius)
    lc.set_editor_property("light_color", unreal.Color(r=int(color[0] * 255), g=int(color[1] * 255), b=int(color[2] * 255), a=255))
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    a.tags = [unreal.Name(TAG)]
    a.set_folder_path(unreal.Name("Remap/CidadeV3/Luz"))
    return a


def flat(label, x, y, sx, sy, mat, z=1.0):
    cube = EAL.load_asset("/Engine/BasicShapes/Cube")
    a = ACTORS.spawn_actor_from_object(cube, unreal.Vector(x, y, z - 5.0), unreal.Rotator(0, 0, 0))
    a.set_actor_scale3d(unreal.Vector(sx / 100.0, sy / 100.0, 0.1))
    m = asset(f"{MAT}/{mat}")
    if m:
        a.static_mesh_component.set_material(0, m)
    a.static_mesh_component.set_collision_profile_name("BlockAll")
    a.tags = [unreal.Name(TAG)]
    a.set_folder_path(unreal.Name("Remap/CidadeV3/Chao"))
    a.set_actor_label(label)
    return a


def mesh_size(key):
    mesh = find_mesh(key)
    if mesh is None:
        return (100.0, 100.0, 100.0)
    b = mesh.get_bounding_box()
    return (b.max.x - b.min.x, b.max.y - b.min.y, b.max.z - b.min.z)


def labels():
    return {a: a.get_actor_label() for a in ACTORS.get_all_level_actors()}


def wall_ring(half):
    """Muralha em volta: segmentos do muro (afinados) + torre a cada 3 segmentos e nas quinas."""
    wx, wy, wz = mesh_size("muro")
    thick, height = 300.0, 780.0
    seg_target = wy
    n = max(1, round((2 * half) / seg_target))
    seg = (2 * half) / n
    for side, (ox, oy, ax, ay) in enumerate(((0, 1, 1, 0), (1, 0, 0, 1), (0, -1, 1, 0), (-1, 0, 0, 1))):
        yaw = math.degrees(math.atan2(-oy, -ox))  # frente para dentro
        for k in range(n):
            t = -half + seg * (k + 0.5)
            x = ax * t + ox * (half + thick / 2)
            y = ay * t + oy * (half + thick / 2)
            put("muro", x, y, yaw, (thick / wx, seg * 1.03 / wy, height / wz), "CidadeV3/Muralha")
            if k % 3 == 0:
                tx = ax * (t - seg / 2) + ox * (half + thick / 2)
                ty = ay * (t - seg / 2) + oy * (half + thick / 2)
                tsx, tsy, tsz = mesh_size("torre")
                ts = max(thick * 1.6 / min(tsx, tsy), height * 1.3 / tsz)
                put("torre", tx, ty, 90.0 * random.randint(0, 3), ts, "CidadeV3/Muralha")
    tsx, tsy, tsz = mesh_size("torre")
    ts = max(thick * 1.8 / min(tsx, tsy), height * 1.4 / tsz)
    for cx in (-1, 1):
        for cy in (-1, 1):
            put("torre", cx * (half + thick / 2), cy * (half + thick / 2), 0.0, ts, "CidadeV3/Muralha")


def dress_city():
    LES.load_level(CITY_MAP)
    old = [a for a in ACTORS.get_all_level_actors() if TAG in [str(t) for t in a.tags]]
    for a in old:
        ACTORS.destroy_actor(a)
    log(f"cidade: {len(old)} atores v3 antigos removidos")
    hidden = 0
    lab = labels()
    for a, name in lab.items():
        if name.startswith(GREY_PREFIXES):
            ACTORS.destroy_actor(a)
            hidden += 1
        elif name == "Chao":
            m = asset(f"{MAT}/MI_User_GramaAlien")
            if m:
                a.static_mesh_component.set_material(0, m)
        elif name == "Praca":
            m = asset(f"{MAT}/MI_User_Concreto")
            if m:
                a.static_mesh_component.set_material(0, m)
    log(f"cidade: {hidden} blocos cinza removidos")

    half = 20000.0
    # avenidas (asfalto) cruzando a praça
    flat("Avenida_NS", 0, 0, 1400, 2 * half, "MI_User_Asfalto", z=3.0)
    flat("Avenida_LO", 0, 0, 2 * half, 1400, "MI_User_Asfalto", z=3.0)
    flat("Praca_V3", 0, 0, 6000, 6000, "MI_User_Concreto", z=6.0)

    # prédios dos vendedores (frente para a praça)
    put("armeiro", 0, 4600 + 900, 270.0, 1.0, "CidadeV3/Vendedores", "Armeiro_Krug")
    put("bancada", 4600 + 900, 0, 180.0, 1.0, "CidadeV3/Vendedores", "Bancada_IxVel")
    gx, gy, gz = mesh_size("portao")
    put("portao", 0, -4600 - 900 - gx * 1.1 / 2, 90.0, 1.1, "CidadeV3/Vendedores", "Portao_Arena")
    # monumento: a nave caída no meio da praça (versão restaurada vem depois, ver arte_vila_pendencias.md)
    nx, ny, nz = mesh_size("nave")
    put("nave", 0, 0, 35.0, 1400.0 / max(nx, ny), "CidadeV3/Praca", "Monumento_Nave")
    light(0, 0, 900, color=(0.4, 0.9, 1.0), intensity=60.0, radius=3500.0)

    # postes ao longo das avenidas e em volta da praça
    for d in range(-18000, 18001, 2400):
        if abs(d) < 3400:
            continue
        for side in (-1, 1):
            lit = (d // 2400) % 2 == 0  # luz em um poste sim, outro não (desempenho)
            put("poste", side * 900, d, 0.0 if side > 0 else 180.0, 1.0, "CidadeV3/Postes")
            put("poste", d, side * 900, 90.0 if side > 0 else 270.0, 1.0, "CidadeV3/Postes")
            if lit:
                light(side * 800, d, 470)
                light(d, side * 800, 470)
    for ang in range(0, 360, 45):
        x, y = math.cos(math.radians(ang)) * 3300, math.sin(math.radians(ang)) * 3300
        put("poste", x, y, ang + 180, 1.0, "CidadeV3/Postes")
        light(x * 0.97, y * 0.97, 470)

    # quarteirões: casas viradas para a rua mais perto, com variação
    rng = random.Random(4242)
    houses = ["casa1", "casa2", "casavila", "cabana", "casa1", "casa2"]
    cell = 4000.0
    n_house = 0
    for gx_ in range(-4, 5):
        for gy_ in range(-4, 5):
            if (abs(gx_) <= 1 and abs(gy_) <= 1) or gx_ == 0 or gy_ == 0:
                continue
            cx, cy = gx_ * cell, gy_ * cell
            # 4 lotes por quarteirão, cada casa olha para fora do quarteirão
            for lx, ly in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                if rng.random() < 0.15:
                    # lote vazio: árvore grande e arbustos
                    put(rng.choice(["arv1", "arv3", "arv4", "cogu"]), cx + lx * 900, cy + ly * 900, rng.uniform(0, 360),
                        rng.uniform(0.8, 1.1), "CidadeV3/Natureza")
                    continue
                key = rng.choice(houses)
                hx, hy = cx + lx * 950, cy + ly * 950
                face = math.degrees(math.atan2(0, lx)) if rng.random() < 0.5 else math.degrees(math.atan2(ly, 0))
                sx, sy, sz = mesh_size(key)
                target = rng.uniform(800, 1050)
                put(key, hx, hy, face, target / max(sx, sy), "CidadeV3/Casas")
                n_house += 1
                # enfeites na frente
                fx, fy = math.cos(math.radians(face)), math.sin(math.radians(face))
                for _ in range(rng.randint(1, 3)):
                    k2 = rng.choice(["barril", "arb1", "arb2", "flor", "pedra2", "gerador", "placa"])
                    off = rng.uniform(-350, 350)
                    put(k2, hx + fx * 620 - fy * off, hy + fy * 620 + fx * off, rng.uniform(0, 360), 1.0,
                        "CidadeV3/Enfeites", collide=k2 in ("barril", "gerador", "pedra2"))
    log(f"cidade: {n_house} casas")
    wall_ring(half)
    unreal.EditorLevelLibrary.save_current_level()
    log("cidade salva")


def dress_arena():
    LES.load_level(ARENA_MAP)
    for a, name in labels().items():
        if name == "Chao":
            a.set_actor_scale3d(unreal.Vector(420.0, 420.0, 1.0))
            m = asset(f"{MAT}/MI_User_AreiaVermelha")
            if m:
                a.static_mesh_component.set_material(0, m)
            log("arena: chão 420 m de areia vermelha")
    unreal.EditorLevelLibrary.save_current_level()


def sky():
    import importlib.util
    spec = importlib.util.spec_from_file_location("setup_alien_sky", os.path.join(os.path.dirname(__file__), "setup_alien_sky.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.EXTRA_MAPS = [CITY_MAP, ARENA_MAP]

    # [A-087] o céu já foi montado no L01: os materiais existem e estão em uso. Recriar (apagar os nós) derruba a
    # Unreal (assert !IsRooted). Construtor "de mentira": material existente é só carregado, sem mexer nos nós.
    base_mb = mod.MB

    class _Keep:
        def __init__(self, m):
            self.m = m

        def finish(self):
            return self.m

        def __getattr__(self, _name):
            return lambda *a, **k: self

    def safe_mb(path, *args, **kwargs):
        if EAL.does_asset_exist(path):
            return _Keep(EAL.load_asset(path))
        return base_mb(path, *args, **kwargs)

    mod.MB = safe_mb
    mod.main([])
    log("céu alienígena + exposição fixa na cidade e na arena")


def main():
    for step in (dress_city, dress_arena, sky):
        try:
            step()
        except Exception as exc:  # noqa: BLE001
            err(step.__name__, exc)
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "dress_remap_v3.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[dress_v3] fim | avisos {len(R['warnings'])} | erros {len(R['errors'])}")


main()
