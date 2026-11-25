"""[A-097] Interiores da Villa Star (Armeiro do Krug, Bancada da Ix-Vel, Casa do herói, Casa saqueada, Bar) + bicicleta.

RODA NO EDITOR (caixa Cmd, sem Play), DEPOIS de compilar o C++ (AJRInteriorPortal, AJRBike), de importar os modelos
(import_user_assets.py: SM_VEH_Bike*) e de montar a cidade (dress_city_v4.py):
  py "E:/game/utrazin-game/tools/unreal/build_interiors_vila.py"
Pode rodar de novo: apaga o que tem a tag VilaInterior antes. Relatório: reports/build_interiors_vila.json

Como funciona: os prédios da cidade são modelos fechados (Tripo), então cada interior é um cômodo montado 45 m
embaixo do próprio prédio (mesmo X/Y: o radar continua apontando certo). Na porta de fora fica um AJRInteriorPortal
("Entrar ..."); dentro, outro na porta ("Sair"). E escurece a tela e leva de um lado para o outro.
Cada cômodo: piso de tábuas, paredes em duas cores (madeira embaixo, reboco em cima) com rodapé e faixa de metal,
vigas de metal no teto, porta dupla de metal com batente, móveis do Forge (SM_INT_*), luz quente no meio + luz
ciano de destaque (candelas) e zona de câmera (braço curto, AJRCameraZone).
Krug fica atrás do balcão do Armeiro e a Ix-Vel entre as bancadas da oficina, os dois virados para a porta.
A bicicleta (AJRBike) fica estacionada ao lado de onde o herói nasce (planta: "bike").
Coordenadas da planta (metros, x leste, y norte) -> Unreal X = x, Y = -y, yaw = -yaw (igual ao dress_city_v4.py).
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
MEL = unreal.MaterialEditingLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
CITY_MAP = "/Game/Levels/Remap/L_Cidade"
WORK = os.path.join(REPO, "assets", "work", "city_v6")  # [A-098]
if not os.path.isfile(os.path.join(WORK, "city_layout.json")):
    WORK = os.path.join(REPO, "assets", "work", "city_v5")
if not os.path.isfile(os.path.join(WORK, "city_layout.json")):
    WORK = os.path.join(REPO, "assets", "work", "city_v4")
TAG = "VilaInterior"
FOLDER = "Remap/Interiores"
DEPTH_CM = 4500.0      # piso do cômodo 45 m abaixo do chão do prédio
WALL_H = 380.0         # pé-direito
WALL_T = 20.0
DOOR_W = 150.0
DOOR_H = 240.0
WAINSCOT = 110.0       # madeira até 1,10 m
CUBE = "/Engine/BasicShapes/Cube"
INT = "/Game/Environment/User/Interior"
MATS = "/Game/Environment/User/Materials"
MAT = {"piso": f"{MATS}/MI_User_MadeiraPiso", "madeira": f"{MATS}/MI_User_MadeiraTabuas", "reboco": f"{MATS}/MI_User_Reboco",
       "teto": f"{MATS}/MI_User_MadeiraVelha", "metal": f"{MATS}/MI_User_MetalAlien"}
DOOR_LEAF = "/Game/Environment/Interiors/SM_INT_PortaMetal"
BIKE_MI = ("/Game/Environment/User/Veiculos/Materials/MI_VEH_BikeQuadro", "/Game/Environment/User/Veiculos/Materials/MI_VEH_BikeRoda")
GLOW_PARENT = f"{MATS}/M_User_PropGlow"
R = {"steps": [], "warnings": [], "errors": [], "rooms": {}}
_cache = {}

# móveis: (malha, x, y, z, yaw, roll) em cm/graus no espaço do cômodo (+X = para a porta; frente dos móveis = +X)
ROOMS = {
    # [A-098] 10 x 8 m: o Krug (tartaruga de 4 braços e rabo comprido) cabia atravessando o balcão no 8 x 7.
    # Pivô dos móveis do Forge = canto mínimo (o móvel cresce para +X/+Y a partir do ponto, girado pelo yaw).
    # Krug a 3,1 m do meio, ajustado para 2,1 m de altura (4o valor do "npc"): rabo para até ~25 cm da parede do
    # fundo, mãos a ~75 cm do balcão; balcão centrado (x -150..-80, y -120..120), atendimento por cima dele.
    "Armeiro_Krug": {
        "size": (1000.0, 800.0), "prompt": "Entrar no Armeiro", "npc": ("Krug", -310.0, 0.0, 210.0),
        "furniture": [
            ("Balcao", -150, -120, 0, 0, 0), ("Luminaria", -130, -95, 105, 20, 0),
            ("SuporteArmas", -494, 200, 105, 0, 0), ("SuporteArmas", -494, -344, 105, 0, 0),
            ("Prateleira", -200, 373, 0, -90, 0), ("Prateleira", 100, 373, 0, -90, 0),
            ("Armario", -200, -372, 0, 90, 0), ("Caixotes", 320, 230, 0, 20, 0), ("Caixotes", 325, -330, 0, -15, 0),
        ],
    },
    "Bancada_IxVel": {
        "size": (800.0, 700.0), "prompt": "Entrar na Bancada", "npc": ("IxVel", -250.0, 0.0),
        "furniture": [
            ("Bancada", -355, -150, 0, 0, 0), ("Bancada", -355, 150, 0, 0, 0), ("Luminaria", -350, -210, 95, 0, 0),
            ("Armario", -100, 322, 0, -90, 0), ("Prateleira", -40, -325, 0, 90, 0),
            ("Mesa", 140, 140, 0, 0, 0), ("Cadeira", 140, 70, 0, 90, 0),
            ("Caixotes", 260, 235, 0, 10, 0), ("Caixotes", 250, -230, 0, -25, 0), ("Caixotes", 150, -255, 0, 40, 0),
        ],
    },
    "Casa_Heroi": {
        "size": (700.0, 600.0), "prompt": "Entrar em casa", "npc": None,
        "furniture": [
            ("Cama", -240, 235, 0, 0, 0), ("Mesa", 60, -70, 0, 0, 0), ("Luminaria", 60, -70, 78, 0, 0),
            ("Cadeira", 60, -140, 0, 90, 0), ("Cadeira", 60, 0, 0, -90, 0),
            ("Armario", -322, -170, 0, 0, 0), ("Prateleira", 190, 275, 0, -90, 0), ("Caixotes", 250, -225, 0, 10, 0),
        ],
    },
    "Casa_Saqueada": {
        "size": (700.0, 600.0), "prompt": "Entrar na casa saqueada", "npc": None,
        "furniture": [
            ("Cama", -235, 230, 0, 9, 0), ("Mesa", 30, -40, 0, 14, 0), ("Cadeira", 130, 70, 23, 35, 90),
            ("Cadeira", -50, -130, 0, 200, 0), ("Armario", -318, -150, 0, 11, 0), ("Prateleira", -325, 90, 0, -4, 0),
            ("Caixotes", 210, -215, 0, 35, 0), ("Caixotes", -110, 120, 0, -20, 0),
        ],
    },
    "Bar_Conversa": {
        "size": (900.0, 700.0), "prompt": "Entrar no Bar", "npc": None,
        "furniture": [
            ("Balcao", -290, -120, 0, 0, 0), ("Balcao", -290, 120, 0, 0, 0), ("Luminaria", -290, 0, 105, 0, 0),
            ("Prateleira", -425, -120, 0, 0, 0), ("Prateleira", -425, 120, 0, 0, 0),
            ("Mesa", 150, 200, 0, 0, 0), ("Cadeira", 150, 130, 0, 90, 0), ("Cadeira", 150, 270, 0, -90, 0), ("Luminaria", 150, 200, 78, 0, 0),
            ("Mesa", 150, -200, 0, 0, 0), ("Cadeira", 150, -270, 0, 90, 0), ("Cadeira", 150, -130, 0, -90, 0), ("Luminaria", 150, -200, 78, 0, 0),
            ("Mesa", -40, -235, 0, 0, 0), ("Cadeira", 30, -235, 0, 180, 0), ("Caixotes", 360, -270, 0, 15, 0),
        ],
    },
}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[interiores] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[interiores] {m}")


def asset(path):
    if path not in _cache:
        _cache[path] = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
        if _cache[path] is None:
            warn(f"não existe {path}")
    return _cache[path]


class Ground:
    """Altura do chão pelo heightmap (igual ao dress_city_v4.py)."""

    def __init__(self, land, res):
        self.res = res
        self.h = array("H")
        with open(os.path.join(WORK, "city_height.r16"), "rb") as fh:
            self.h.frombytes(fh.read())
        loc, sc = land.get_actor_location(), land.get_actor_scale3d()
        self.ox, self.oy, self.oz, self.sx, self.sy, self.sz = loc.x, loc.y, loc.z, sc.x, sc.y, sc.z

    def z(self, X, Y):
        fx = min(max((X - self.ox) / self.sx, 0.0), self.res - 1.001)
        fy = min(max((Y - self.oy) / self.sy, 0.0), self.res - 1.001)
        ix, iy = int(fx), int(fy)
        tx, ty = fx - ix, fy - iy
        r = self.res
        v = self.h
        top = v[iy * r + ix] * (1 - tx) + v[iy * r + ix + 1] * tx
        bot = v[(iy + 1) * r + ix] * (1 - tx) + v[(iy + 1) * r + ix + 1] * tx
        return self.oz + ((top * (1 - ty) + bot * ty) - 32768.0) * self.sz / 128.0


class Room:
    """Espaço local do cômodo: +X para a porta, origem no meio do piso."""

    def __init__(self, label, X, Y, Z, yaw_ue):
        self.label, self.X, self.Y, self.Z, self.yaw = label, X, Y, Z, yaw_ue
        self.c, self.s = math.cos(math.radians(yaw_ue)), math.sin(math.radians(yaw_ue))

    def w(self, lx, ly, lz):
        return unreal.Vector(self.X + lx * self.c - ly * self.s, self.Y + lx * self.s + ly * self.c, self.Z + lz)

    def tag(self, a, sub, name):
        a.tags = [unreal.Name(TAG)]
        a.set_folder_path(unreal.Name(f"{FOLDER}/{self.label}/{sub}"))
        a.set_actor_label(f"{self.label}_{name}")
        return a

    def box(self, name, mat, center, size, sub="Casca"):
        m = asset(CUBE)
        if m is None:
            return None
        a = ACTORS.spawn_actor_from_object(m, self.w(*center), unreal.Rotator(0, 0, self.yaw))
        a.set_actor_scale3d(unreal.Vector(size[0] / 100.0, size[1] / 100.0, size[2] / 100.0))
        c = a.static_mesh_component
        c.set_mobility(unreal.ComponentMobility.STATIC)
        c.set_collision_profile_name("BlockAll")
        mi = asset(MAT[mat])
        if mi:
            c.set_material(0, mi)
        return self.tag(a, sub, name)

    def mesh(self, name, path, lx, ly, lz, yaw=0.0, roll=0.0, scale=(1.0, 1.0, 1.0), collide=True, sub="Moveis"):
        m = asset(path)
        if m is None:
            return None
        a = ACTORS.spawn_actor_from_object(m, self.w(lx, ly, lz), unreal.Rotator(roll, 0, self.yaw + yaw))
        a.set_actor_scale3d(unreal.Vector(*scale))
        c = a.static_mesh_component
        c.set_mobility(unreal.ComponentMobility.STATIC)
        c.set_collision_profile_name("BlockAll" if collide else "NoCollision")
        return self.tag(a, sub, name)

    def light(self, name, lx, ly, lz, cd, color, radius, shadows=True):
        a = ACTORS.spawn_actor_from_class(unreal.PointLight, self.w(lx, ly, lz), unreal.Rotator(0, 0, 0))
        lc = a.point_light_component
        lc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
        lc.set_editor_property("intensity", float(cd))
        lc.set_editor_property("attenuation_radius", float(radius))
        lc.set_editor_property("cast_shadows", shadows)
        lc.set_editor_property("light_color", unreal.Color(r=int(color[0] * 255), g=int(color[1] * 255), b=int(color[2] * 255), a=255))
        return self.tag(a, "Luz", name)


def wall_run(room, name, axis, pos, a0, a1, z0=0.0, z1=WALL_H):
    """Trecho de parede de a0 até a1 (ao longo de Y se axis='x', ao longo de X se axis='y'), em duas cores."""
    length = a1 - a0
    mid = (a0 + a1) / 2
    for part, mat, lo, hi in (("baixo", "madeira", z0, min(z1, WAINSCOT)), ("cima", "reboco", max(z0, WAINSCOT), z1)):
        if hi - lo < 1:
            continue
        if axis == "x":
            room.box(f"{name}_{part}", mat, (pos, mid, (lo + hi) / 2), (WALL_T, length, hi - lo))
        else:
            room.box(f"{name}_{part}", mat, (mid, pos, (lo + hi) / 2), (length, WALL_T, hi - lo))


def trims(room, W, D):
    """Rodapé e faixa de metal na altura da madeira, por dentro das 4 paredes (a da porta em dois pedaços)."""
    for z, h, t, tag in ((6.0, 12.0, 4.0, "rodape"), (WAINSCOT, 7.0, 5.0, "faixa")):
        room.box(f"{tag}_fundo", "metal", (-W / 2 + t / 2, 0, z), (t, D, h), sub="Acabamento")
        for sgn in (-1, 1):
            room.box(f"{tag}_lado{sgn:+d}", "metal", (0, sgn * (D / 2 - t / 2), z), (W, t, h), sub="Acabamento")
            seg = D / 2 - DOOR_W / 2 - 14
            room.box(f"{tag}_frente{sgn:+d}", "metal", (W / 2 - t / 2, sgn * (DOOR_W / 2 + 14 + seg / 2), z), (t, seg, h), sub="Acabamento")


def build_room(label, spec, b, ground, layout):
    W, D = spec["size"]
    X, Y = b["x"] * 100.0, -b["y"] * 100.0
    yaw = -b["yaw"]
    floor_z = ground.z(X, Y) - DEPTH_CM
    room = Room(label, X, Y, floor_z, yaw)
    # casca
    room.box("piso", "piso", (0, 0, -10), (W + 2 * WALL_T, D + 2 * WALL_T, 20))
    room.box("teto", "teto", (0, 0, WALL_H + 10), (W + 2 * WALL_T, D + 2 * WALL_T, 20))
    n_beams = max(2, int(W // 150))
    for i in range(n_beams):
        x = -W / 2 + (i + 0.5) * W / n_beams
        room.box(f"viga_{i}", "metal", (x, 0, WALL_H - 12), (22, D, 24), sub="Acabamento")
    wall_run(room, "parede_fundo", "x", -W / 2 - WALL_T / 2, -D / 2 - WALL_T, D / 2 + WALL_T)
    for sgn in (-1, 1):
        wall_run(room, f"parede_lado{sgn:+d}", "y", sgn * (D / 2 + WALL_T / 2), -W / 2, W / 2)
        # parede da porta: dois pedaços dos lados do vão
        a0, a1 = (DOOR_W / 2, D / 2 + WALL_T) if sgn > 0 else (-D / 2 - WALL_T, -DOOR_W / 2)
        wall_run(room, f"parede_frente{sgn:+d}", "x", W / 2 + WALL_T / 2, a0, a1)
    wall_run(room, "parede_frente_verga", "x", W / 2 + WALL_T / 2, -DOOR_W / 2, DOOR_W / 2, DOOR_H, WALL_H)
    trims(room, W, D)
    # batente e porta dupla de metal (fechada; a passagem é pelo E)
    for sgn in (-1, 1):
        room.box(f"batente{sgn:+d}", "metal", (W / 2 - 4, sgn * (DOOR_W / 2 + 7), DOOR_H / 2), (16, 14, DOOR_H), sub="Porta")
    room.box("batente_cima", "metal", (W / 2 - 4, 0, DOOR_H + 7), (16, DOOR_W + 28, 14), sub="Porta")
    leaf = asset(DOOR_LEAF)
    if leaf:
        half = DOOR_W / 2
        room.mesh("porta_a", DOOR_LEAF, W / 2 + 2, -half, 0, 0, 0, (1.0, half / 100.0, DOOR_H / 220.0), True, "Porta")
        room.mesh("porta_b", DOOR_LEAF, W / 2 + 2, half, 0, 180, 0, (1.0, half / 100.0, DOOR_H / 220.0), True, "Porta")
    else:
        room.box("porta", "metal", (W / 2 + 6, 0, DOOR_H / 2), (8, DOOR_W, DOOR_H), sub="Porta")
    # móveis
    for i, (name, lx, ly, lz, fyaw, froll) in enumerate(spec["furniture"]):
        room.mesh(f"{name}_{i:02d}", f"{INT}/SM_INT_{name}", lx, ly, lz, fyaw, froll, collide=name != "Luminaria")
    # luz: quente no meio (sombra), ciano de destaque no fundo
    room.light("luz_meio", 0, 0, WALL_H - 45, 45.0, (1.0, 0.78, 0.52), max(W, D) * 1.3)
    room.light("luz_ciano", -W / 2 + 90, 0, WALL_H - 90, 14.0, (0.35, 0.9, 1.0), max(W, D) * 0.8, False)
    # câmera de braço curto dentro
    zone = ACTORS.spawn_actor_from_class(unreal.JRCameraZone, room.w(0, 0, WALL_H / 2), unreal.Rotator(0, 0, yaw))
    try:
        zone.set_editor_property("arm_length", 170.0)
    except Exception as exc:  # noqa: BLE001
        warn(f"{label}: arm_length {exc}")
    zb = zone.get_component_by_class(unreal.BoxComponent)
    if zb:
        zb.set_box_extent(unreal.Vector(W / 2 + 20, D / 2 + 20, WALL_H / 2 + 30))
    room.tag(zone, "Camera", "zona_camera")
    # portas de passagem
    door = b.get("door") or [b["x"], b["y"]]
    fyaw = math.radians(yaw)
    DX, DY = door[0] * 100.0 + math.cos(fyaw) * 60.0, -door[1] * 100.0 + math.sin(fyaw) * 60.0
    out = ACTORS.spawn_actor_from_class(unreal.JRInteriorPortal, unreal.Vector(DX, DY, ground.z(DX, DY)), unreal.Rotator(0, 0, yaw))
    out.set_editor_property("portal_id", unreal.Name(f"{label}_Fora"))
    out.set_editor_property("target_id", unreal.Name(f"{label}_Dentro"))
    out.set_editor_property("prompt", text(spec["prompt"]))
    room.tag(out, "Porta", "portal_fora")
    inside = ACTORS.spawn_actor_from_class(unreal.JRInteriorPortal, room.w(W / 2 - 40, 0, 0), unreal.Rotator(0, 0, yaw + 180))
    inside.set_editor_property("portal_id", unreal.Name(f"{label}_Dentro"))
    inside.set_editor_property("target_id", unreal.Name(f"{label}_Fora"))
    inside.set_editor_property("prompt", text("Sair"))
    room.tag(inside, "Porta", "portal_dentro")
    # vendedor dentro, virado para a porta
    if spec["npc"]:
        # [A-098] ("Nome", x, y[, altura alvo cm]): escala pela malha e pés no piso (antes Z fixo +100 cm)
        name, lx, ly = spec["npc"][:3]
        target_h = spec["npc"][3] if len(spec["npc"]) > 3 else None
        npc = next((a for a in ACTORS.get_all_level_actors() if a.get_actor_label() == f"NPC_{name}"), None)
        if npc is None:
            warn(f"NPC_{name} não está no mapa")
        else:
            z_off, scale, info = 100.0, 1.0, {}
            try:
                comp = npc.get_editor_property("mesh")
                sk = comp.get_skeletal_mesh_asset() if comp else None
                if sk is not None:
                    try:
                        bnd = sk.get_bounds()
                    except Exception:  # noqa: BLE001
                        bnd = sk.get_imported_bounds()
                    ext = bnd.box_extent
                    if target_h:
                        scale = min(1.5, max(0.4, float(target_h) / max(1.0, 2.0 * ext.z)))
                    npc.set_actor_scale3d(unreal.Vector(scale, scale, scale))
                    # o AJRShopkeeper põe a cápsula com meia altura = max(60, extent Z) e a malha em -meia altura
                    z_off = max(60.0, ext.z) * scale + 2.0
                    info = {"malha_cm": [round(ext.x * 2), round(ext.y * 2), round(ext.z * 2)], "escala": round(scale, 3),
                            "altura_final_cm": round(ext.z * 2 * scale)}
                    if npc.get_editor_property("idle_anim") is None:  # parado sem animação = "estátua"
                        folder = f"/Game/Characters/NPC/{name}"
                        for p_ in (EAL.list_assets(folder, True, False) if EAL.does_directory_exist(folder) else []):
                            if "Breathing_Idle" in p_:
                                npc.set_editor_property("idle_anim", EAL.load_asset(p_.split(".")[0]))
                                info["idle"] = "Breathing_Idle (ligada agora)"
                                break
                    else:
                        info["idle"] = npc.get_editor_property("idle_anim").get_name()
            except Exception as exc:  # noqa: BLE001
                warn(f"NPC_{name}: medida da malha ({exc}); fica no Z padrão")
            npc.set_actor_location(room.w(lx, ly, z_off), False, False)
            npc.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
            R.setdefault("npcs", {})[name] = info
            log(f"NPC_{name} dentro do {label}: {info}")
    R["rooms"][label] = {"floor_z_cm": round(floor_z), "size_cm": [W, D], "furniture": len(spec["furniture"])}
    log(f"{label}: cômodo {W / 100:.0f} x {D / 100:.0f} m, {len(spec['furniture'])} móveis, piso em Z {floor_z:.0f}")


def text(v):
    try:
        return unreal.Text(v)
    except Exception:  # noqa: BLE001
        return v


def place_bike(layout, ground):
    bk = layout.get("bike")
    if not bk:
        warn("planta sem 'bike'")
        return
    for p in BIKE_MI:
        parent = asset(GLOW_PARENT)
        mi = EAL.load_asset(p) if EAL.does_asset_exist(p) else None
        if mi and parent and mi.get_editor_property("parent") != parent:
            MEL.set_material_instance_parent(mi, parent)
            MEL.update_material_instance(mi)
            EAL.save_loaded_asset(mi)
            log(f"{p.rsplit('/', 1)[1]} brilha nas faixas ciano")
    X, Y = bk["x"] * 100.0, -bk["y"] * 100.0
    a = ACTORS.spawn_actor_from_class(unreal.JRBike, unreal.Vector(X, Y, ground.z(X, Y)), unreal.Rotator(0, 0, -bk["yaw"]))
    a.tags = [unreal.Name(TAG)]
    a.set_folder_path(unreal.Name("Remap/Bicicleta"))
    a.set_actor_label("Bicicleta")
    log(f"bicicleta em ({bk['x']:.0f}, {bk['y']:.0f}) m")


def fix_kill_z():
    """[A-098] O KillZ da L_Cidade era -3000 (build_remap_f1): os cômodos ficam a -45 m, então o herói era apagado ao
    passar pela porta (tela parada, sem controle). Agora fica 30 m abaixo do piso mais fundo."""
    floors = [r["floor_z_cm"] for r in R["rooms"].values()] or [-5000.0]
    kz = float(min(floors)) - 3000.0
    ws = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    old = ws.get_editor_property("kill_z")
    if old > kz:
        ws.set_editor_property("kill_z", kz)
        log(f"KillZ {old:.0f} -> {kz:.0f} (abaixo dos cômodos)")


def main():
    if not LES.load_level(CITY_MAP):
        raise RuntimeError(f"não abriu {CITY_MAP}")
    with open(os.path.join(WORK, "city_layout.json"), encoding="utf-8") as fh:
        layout = json.load(fh)
    land = next((a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.LandscapeProxy)), None)
    if land is None:
        raise RuntimeError("não há Landscape na L_Cidade (rode fix_city_landscape.py)")
    ground = Ground(land, int(layout["landscape"]["res"]))
    n = 0
    for a in ACTORS.get_all_level_actors():
        if TAG in [str(t) for t in a.tags]:
            ACTORS.destroy_actor(a)
            n += 1
    log(f"{n} atores da rodada anterior removidos")
    for b in layout["buildings"]:
        if b.get("label") in ROOMS:
            build_room(b["label"], ROOMS[b["label"]], b, ground, layout)
    missing = set(ROOMS) - set(R["rooms"])
    if missing:
        warn(f"prédios não achados na planta: {sorted(missing)}")
    place_bike(layout, ground)
    fix_kill_z()
    LES.save_current_level()
    log("L_Cidade salva")


try:
    main()
except Exception as exc:  # noqa: BLE001
    R["errors"].append(str(exc))
    unreal.log_error(f"[interiores] {exc}\n{traceback.format_exc()[-1500:]}")
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "build_interiors_vila.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[interiores] fim | avisos {len(R['warnings'])} | erros {len(R['errors'])}")
