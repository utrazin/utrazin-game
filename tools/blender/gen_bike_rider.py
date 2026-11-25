"""[A-098] Bicicleta de verdade: pedivela separado + pedalada em loop no esqueleto de cada herói (Blender 5.3 / bpy).

Sem Mixamo: o Mixamo não tem ciclista. A pedalada sai daqui, com IK analítico de 2 ossos feito em Python
(quadril no selim, mãos nas manoplas, bola do pé no pedal), usando as medidas reais da SM_VEH_BikeQuadro.

Uso (Blender 5.3 em background, ou Python 3.13 com o módulo bpy 5.3):
  blender -b --factory-startup --python-exit-code 1 --python tools/blender/gen_bike_rider.py -- [escala]
  (ou E:\\game\\gerar_bike_anim.bat)
  escala opcional (ex. 1.1): tamanho da bicicleta em relação ao modelo; sem ela o script escolhe a maior que
  ainda deixa a heroína mais baixa alcançar o pedal de baixo com o joelho um pouco dobrado.

Entradas:
  assets/work/tripo/SM_VEH_BikeQuadro.fbx            (quadro com pedivela, do polish_forge.py; frente +X, chão = pedal)
  assets/work/tripo/SM_VEH_BikeRoda.fbx              (só para a prévia)
  assets/work/characters/CHR-00N/SK_HeroNN_rig.fbx   (o mesmo FBX que virou /Game/Characters/HeroNN/Mesh/SK_HeroNN)
Saídas:
  assets/work/tripo/SM_VEH_BikeQuadroSemPedivela.fbx (+ UCX)  quadro sem pedivela/pedais, MESMA origem do original
  assets/work/tripo/SM_VEH_BikePedivela.fbx          coroa + eixo + 2 braços; origem no eixo do movimento central,
                                                      braço direito apontando para a frente (+X) = fase 0
  assets/work/tripo/SM_VEH_BikePedal.fbx             um pedal (o direito); origem no eixo do pedal
  assets/work/tripo/SM_VEH_BikeSelim.fbx             selim + canote (mesma origem do quadro; o C++ desce SeatDrop)
  assets/work/tripo/SM_VEH_BikeGuidao.fbx            garfo, guidão, manoplas, para-lama da frente (mesma origem do quadro;
                                                      gira no eixo da caixa de direção, SteerPivot/SteerTilt no json)
  assets/work/anims/bike/A_Bike_Pedal_HeroNN.fbx     só o esqueleto + a ação: 1 volta do pedivela em 36 quadros
                                                      (30 fps, 1,2 s; quadro 36 = quadro 0), fase = 10 graus/quadro
  assets/work/anims/bike/bike_rider_info.json        escala, medidas para o C++ (cm) e conferências
  assets/work/anims/bike/previews/*.png              herói + bicicleta montados em 4 fases (lado e 3/4)

Convenções (conferidas com o AJRBike):
  quadro no espaço da bicicleta na Unreal (cm): (x, -y, z + 15,8) do FBX do quadro (x frente, z para cima)
  herói: malha a (0,0,-90) com yaw -90 na cápsula -> ponto da Unreal (ux,uy,uz) = Blender (-uy, -ux, uz)
  fase phi (graus): pedal direito no eixo + L*(cos phi, 0, -sin phi) (0 = frente, 90 = embaixo); na Unreal o
  pedivela gira com Pitch = -phi, o pedal direito com Pitch = +phi e o esquerdo com (-phi, yaw 180).
"""
import json
import math
import os
import sys

import bpy
import bmesh  # noqa: E402  (precisa do bpy carregado antes)
from mathutils import Matrix, Vector

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FORCED_SCALE = float(ARGS[0]) if ARGS and ARGS[0].replace(".", "", 1).isdigit() else None
TRIPO = os.path.join(REPO, "assets", "work", "tripo")
OUT = os.path.join(REPO, "assets", "work", "anims", "bike")
HEROES = {
    "Hero01": os.path.join(REPO, "assets", "work", "characters", "CHR-001", "SK_Hero01_rig.fbx"),
    "Hero02": os.path.join(REPO, "assets", "work", "characters", "CHR-002", "SK_Hero02_rig.fbx"),
}
FRAME_GROUND = 0.158      # = AJRBike::FrameGroundOffset (o pedal mais baixo do FBX original fica no z=0)
FPS = 30
NF = 36                   # quadros por volta (quadro NF = quadro 0)
LEG_REACH = 0.97          # quadril->tornozelo no ponto mais longe / (coxa + canela): joelho ~25 graus dobrado
SEAT_DROP = 0.04          # selim (malha própria) desce 4 cm no canote: os heróis têm perna curta para o quadro
HIP_ABOVE_SEAT = 0.06     # junta do quadril acima do selim (herói de 1,75 m; proporcional à altura)
ARM_REACH = 0.90          # ombro->punho / (braço + antebraço): cotovelo dobrado
SCALE_RANGE = (0.80, 1.30)
INFO = {"fps": FPS, "frames": NF, "heroes": {}, "checks": {}}


# ------------------------------------------------------------------ utilidades
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 0, NF


def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path, automatic_bone_orientation=False, ignore_leaf_bones=False)
    return [o for o in bpy.data.objects if o not in before]


def islands(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    seen, out = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, comp = [v], []
        seen.add(v.index)
        while stack:
            a = stack.pop()
            comp.append(a.index)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index)
                    stack.append(b)
        out.append(comp)
    bm.free()
    return out


def box(me, idx):
    pts = [me.vertices[i].co for i in idx]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def sub_object(src, keep, name):
    """Cópia de src só com os vértices de keep (e as faces deles)."""
    me = src.data.copy()
    me.name = name
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
    bm.to_mesh(me)
    bm.free()
    me.update()
    return ob


def export_mesh(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    # mesmas opções do polish_forge.py (o SM_VEH_BikeQuadro original saiu assim)
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
                             mesh_smooth_type="FACE", add_leaf_bones=False, colors_type="NONE", path_mode="STRIP")


def rot2(a, b):
    """Matriz de rotação que leva a base (a0,a1) para (b0,b1) (vetores quaisquer, ortonormalizados aqui)."""
    def basis(x, y):
        x = x.normalized()
        z = x.cross(y).normalized()
        y = z.cross(x).normalized()
        return Matrix((x, y, z)).transposed()
    return basis(*b) @ basis(*a).transposed()


# ------------------------------------------------------------------ 1. bicicleta: separa o pedivela
def split_bike():
    reset()
    objs = import_fbx(os.path.join(TRIPO, "SM_VEH_BikeQuadro.fbx"))
    frame = next(o for o in objs if o.type == "MESH" and not o.name.startswith("UCX_"))
    ucx = next((o for o in objs if o.name.startswith("UCX_")), None)
    for o in objs:   # tudo no espaço do FBX (o import às vezes deixa rotação/escala no objeto)
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    me = frame.data
    isl = islands(me)
    # coroa: ilha plana (fina em Y) de ~20 cm de diâmetro perto do chão -> centro = eixo do movimento central
    ring = None
    for c in isl:
        mn, mx = box(me, c)
        sz = mx - mn
        if 0.17 < sz.x < 0.24 and 0.17 < sz.z < 0.24 and sz.y < 0.03 and mx.z < 0.40:
            ring = (mn + mx) / 2
            break
    if ring is None:
        raise RuntimeError("não achei a coroa (pedivela) no SM_VEH_BikeQuadro.fbx")
    bb = Vector((ring.x, 0.0, ring.z))
    crank, pedals, arms = [], [], []
    for c in isl:
        pts = [me.vertices[i].co for i in c]
        if all(math.hypot(p.x - bb.x, p.z - bb.z) < 0.215 and abs(p.y) < 0.21 for p in pts):
            crank += c
            ctr = sum(pts, Vector()) / len(pts)
            d = math.hypot(ctr.x - bb.x, ctr.z - bb.z)
            if d > 0.12:
                pedals.append((ctr, c))
            elif d > 0.04:
                arms.append((ctr, c))
    if len(pedals) != 2 or len(arms) < 2:
        raise RuntimeError(f"pedivela inesperado: {len(pedals)} pedais, {len(arms)} braços")
    right_ped = min(pedals, key=lambda t: t[0].y)       # Blender -Y = Unreal +Y = lado direito do ciclista
    right_arm = min(arms, key=lambda t: t[0].y)
    pmn, pmx = box(me, right_ped[1])
    amn, amx = box(me, right_arm[1])
    ped_c = (pmn + pmx) / 2
    spindle_y = (amn.y + amx.y) / 2                      # o braço do pedivela fica no plano do eixo do pedal
    crank_len = math.hypot(ped_c.x - bb.x, ped_c.z - bb.z)
    a0 = math.atan2(ped_c.z - bb.z, ped_c.x - bb.x)       # ângulo atual do braço direito (0 = frente)
    half_thick = (pmx.z - pmn.z) / 2
    # selim + base + canote: malha própria (desce SEAT_DROP no C++), mesma origem do quadro
    seat_set = []
    for c in isl:
        mn, mx = box(me, c)
        if mn.z > 0.68 and mn.x > -0.40 and mx.x < -0.05 and abs(mn.y) < 0.08 and abs(mx.y) < 0.08:
            seat_set += c
    if not seat_set:
        raise RuntimeError("selim não achado")
    # quadro sem pedivela (MESMA origem do original: o C++ continua com FrameGroundOffset = 15,8)
    crank_set = set(crank)
    # direção: garfo + coroa do garfo + avanço + guidão + manoplas + para-lama da frente (gira no eixo da caixa de
    # direção; a caixa, o farol e o cristal ficam no quadro)
    steer_set = []
    for c in isl:
        mn, mx = box(me, c)
        if mn.x <= 0.2:
            continue
        on_head_tube = max(abs(mn.y), abs(mx.y)) < 0.06 and mn.x > 0.35 and mx.x < 0.51 and mn.z > 0.49 and mx.z < 0.86
        if not on_head_tube:
            steer_set += c
    q = sub_object(frame, set(range(len(me.vertices))) - crank_set - set(seat_set) - set(steer_set),
                   "SM_VEH_BikeQuadroSemPedivela")
    sl = sub_object(frame, set(seat_set), "SM_VEH_BikeSelim")
    gd = sub_object(frame, set(steer_set), "SM_VEH_BikeGuidao")
    # pedivela: origem no eixo, braço direito para a frente
    pv = sub_object(frame, crank_set - set(right_ped[1]) - set(next(c for p, c in pedals if c is not right_ped[1])),
                    "SM_VEH_BikePedivela")
    rot = Matrix.Rotation(a0, 4, "Y")   # Ry(+a) leva o ângulo a0 (no plano XZ) para 0
    pv.data.transform(rot @ Matrix.Translation(-bb))
    test = rot @ (ped_c - bb)
    if test.x < 0 or abs(test.z) > 0.01:
        raise RuntimeError(f"giro do pedivela errado: {tuple(test)}")
    # pedal direito: origem no eixo do pedal, nível (o pedal do Forge já é uma caixa alinhada)
    spindle = Vector((ped_c.x, spindle_y, ped_c.z))
    pd = sub_object(frame, set(right_ped[1]), "SM_VEH_BikePedal")
    pd.data.transform(Matrix.Translation(-spindle))
    outs = {}
    path = os.path.join(TRIPO, "SM_VEH_BikeQuadroSemPedivela.fbx")
    exp = [q]
    if ucx:
        ucx.name = "UCX_SM_VEH_BikeQuadroSemPedivela_00"
        exp.append(ucx)
    export_mesh(exp, path)
    outs["quadro"] = os.path.relpath(path, REPO)
    for ob in (pv, pd, sl, gd):
        path = os.path.join(TRIPO, f"{ob.name}.fbx")
        export_mesh([ob], path)
        outs[ob.name] = os.path.relpath(path, REPO)
    # pontos de contato (espaço do FBX do quadro, metros)
    seat, grips = None, []
    for c in isl:
        mn, mx = box(me, c)
        ctr = (mn + mx) / 2
        if mx.z > 0.75 and ctr.x < -0.08 and (mx.x - mn.x) > 0.2 and (seat is None or mx.z > seat[1].z):
            seat = (mn, mx)
        if abs(ctr.y) > 0.25 and mx.z > 0.8:
            grips.append(ctr)
    if seat is None or len(grips) != 2:
        raise RuntimeError(f"selim/manoplas não achados (selim={seat is not None}, manoplas={len(grips)})")
    # eixo da direção (villa_kit.py: HEAD_B=(0,0.68,0.47), HEAD_T=(0,0.95,0.40) no Forge; BB do Forge = (0,0.30,0))
    off = Vector((bb.x - 0.0, 0.0, bb.z - (0.30 - FRAME_GROUND)))
    head_b = Vector((0.47, 0.0, 0.68 - FRAME_GROUND)) + off
    head_t = Vector((0.40, 0.0, 0.95 - FRAME_GROUND)) + off
    geo = {
        "head_b": head_b, "head_tilt_deg": math.degrees(math.atan2(head_b.x - head_t.x, head_t.z - head_b.z)),
        "bb": bb, "crank_len": crank_len, "spindle_y": abs(spindle_y), "pedal_out": abs(ped_c.y) - abs(spindle_y),
        "pedal_half_thick": half_thick,
        "seat_top": Vector(((seat[0].x + seat[1].x) / 2, 0.0, seat[1].z - SEAT_DROP)), "seat_len": seat[1].x - seat[0].x,
        "grip_r": min(grips, key=lambda g: g.y), "grip_l": max(grips, key=lambda g: g.y),
    }
    INFO["bike_fbx"] = outs
    INFO["bike_raw_m"] = {k: (list(map(lambda x: round(x, 4), v)) if isinstance(v, Vector) else round(v, 4))
                          for k, v in geo.items()}
    print(f"[bike] eixo {tuple(round(x, 3) for x in bb)} pedivela {crank_len:.3f} m, selim {geo['seat_top']}, "
          f"manoplas {geo['grip_r']} / {geo['grip_l']}")
    return geo


# ------------------------------------------------------------------ 2. geometria no espaço do herói
class Bike:
    """Pontos da bicicleta (escala s) no espaço do herói no Blender (frente -Y, direita -X, chão z=0)."""

    def __init__(self, geo, s):
        self.g, self.s = geo, s
        # quadro FBX (fx,fy,fz) -> Unreal (fx,-fy,fz+0.158) -> herói Blender (-uy,-ux,uz) = (fy,-fx,fz+0.158), x s
        self.M = Matrix.Translation((0, 0, s * FRAME_GROUND)) @ Matrix.Rotation(math.radians(-90), 4, "Z") @ \
            Matrix.Diagonal((s, s, s, 1))

    def p(self, f):
        return self.M @ Vector(f)

    def crank(self, phi_deg):
        return Matrix.Translation(self.g["bb"]) @ Matrix.Rotation(math.radians(phi_deg), 4, "Y")

    def pedal_top(self, phi_deg, side):
        """side +1 = direito (FBX -Y), -1 = esquerdo. Centro de cima do pedal (que fica sempre nivelado)."""
        g = self.g
        a = phi_deg if side > 0 else phi_deg + 180.0
        y = -side * g["spindle_y"]
        spindle = self.crank(0) @ Vector((g["crank_len"] * math.cos(math.radians(a)), y,
                                          -g["crank_len"] * math.sin(math.radians(a))))
        top = spindle + Vector((0, -side * g["pedal_out"], g["pedal_half_thick"]))
        return self.p(top)

    def seat(self):
        return self.p(self.g["seat_top"])

    def grip(self, side):
        return self.p(self.g["grip_r"] if side > 0 else self.g["grip_l"])


# ------------------------------------------------------------------ 3. herói
class Rig:
    def __init__(self, path):
        objs = import_fbx(path)
        self.arm = next(o for o in objs if o.type == "ARMATURE")
        self.meshes = [o for o in objs if o.type == "MESH"]
        self.mw = self.arm.matrix_world.copy()
        self.A = self.mw.to_3x3().normalized()
        self.pb = self.arm.pose.bones
        for b in self.pb:
            b.rotation_mode = "QUATERNION"
        self.rest_rot = {b.name: self.A @ b.bone.matrix_local.to_3x3().normalized() for b in self.pb}
        self.rest_head = {b.name: self.mw @ b.bone.head_local for b in self.pb}
        h = self.rest_head
        self.L = {s: ((h[f"calf_{s}"] - h[f"thigh_{s}"]).length, (h[f"foot_{s}"] - h[f"calf_{s}"]).length)
                  for s in "lr"}
        self.La = {s: ((h[f"lowerarm_{s}"] - h[f"upperarm_{s}"]).length, (h[f"hand_{s}"] - h[f"lowerarm_{s}"]).length)
                   for s in "lr"}
        self.height = max((o.matrix_world @ Vector(v)).z for o in self.meshes for v in o.bound_box) if self.meshes \
            else h["head"].z + 0.12

    def upd(self):
        bpy.context.view_layer.update()

    def head(self, n):
        return self.mw @ self.pb[n].head

    def rot(self, n):
        return self.A @ self.pb[n].matrix.to_3x3().normalized()

    def set(self, n, R=None, pos=None):
        R = R if R is not None else self.rot(n)
        pos = pos if pos is not None else self.head(n)
        la = self.mw.inverted() @ pos
        self.pb[n].matrix = Matrix.Translation(la) @ (self.A.inverted() @ R).to_4x4()
        self.upd()

    def turn(self, n, R):
        """Gira o osso (no mundo) em volta da própria cabeça."""
        self.set(n, R @ self.rot(n))

    def clear(self):
        for b in self.pb:
            b.location = (0, 0, 0)
            b.rotation_quaternion = (1, 0, 0, 0)
            b.scale = (1, 1, 1)
        self.upd()


def two_bone(rig, upper, lower, end, target, pole, rest_ref):
    """IK analítico: posiciona upper/lower para a cabeça de 'end' chegar em target, dobrando para 'pole'.
    rest_ref = direção do mundo que, na pose de descanso, aponta para o lado do pole (frente do joelho / ponta do
    cotovelo). Devolve o erro de alcance (m)."""
    L1 = (rig.rest_head[lower] - rig.rest_head[upper]).length
    L2 = (rig.rest_head[end] - rig.rest_head[lower]).length
    H = rig.head(upper)
    d = target - H
    dist = d.length
    reach_err = max(0.0, dist - (L1 + L2) * 0.999)
    dist = min(max(dist, abs(L1 - L2) + 1e-4), (L1 + L2) * 0.999)
    dn = d.normalized()
    pp = (pole - dn * pole.dot(dn)).normalized()
    ca = (L1 * L1 + dist * dist - L2 * L2) / (2 * L1 * dist)
    a = math.acos(max(-1.0, min(1.0, ca)))
    K = H + (dn * math.cos(a) + pp * math.sin(a)) * L1
    E = H + dn * dist
    for bone, child, p0, p1 in ((upper, lower, H, K), (lower, end, K, E)):
        Rr = rig.rest_rot[bone]
        ax_rest = (rig.rest_head[child] - rig.rest_head[bone]).normalized()
        ref_rest = (rest_ref - ax_rest * rest_ref.dot(ax_rest)).normalized()
        ax = (p1 - p0).normalized()
        ref = (pp - ax * pp.dot(ax)).normalized()
        R = rot2((ax_rest, ref_rest), (ax, ref)) @ Rr
        rig.set(bone, R, p0 if bone == upper else None)
    return reach_err


SPINE = ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05")


def pose_torso(rig, hip_target, lean, roll=0.0):
    """Pelve inclinada para a frente (0,35 da inclinação) e coluna dobrando o resto; quadril no lugar pedido."""
    rig.clear()
    RX = lambda a: Matrix.Rotation(a, 3, "X")   # noqa: E731  (+a = topo vai para a frente, -Y)
    RY = lambda a: Matrix.Rotation(a, 3, "Y")   # noqa: E731
    Rp = RY(roll) @ RX(lean * 0.35) @ rig.rest_rot["pelvis"]
    rig.set("pelvis", Rp)
    for _ in range(2):
        mid = (rig.head("thigh_l") + rig.head("thigh_r")) / 2
        rig.set("pelvis", Rp, rig.head("pelvis") + (hip_target - mid))
    for n in SPINE:
        if n in rig.pb:
            rig.turn(n, RX(lean * 0.13) @ RY(-roll * 0.25))
    # pescoço/cabeça quase em pé (olhando a rua, um pouco para baixo)
    for n, k in (("neck_01", 0.55), ("neck_02", 0.35)):
        if n in rig.pb:
            rig.set(n, RX(lean * k) @ rig.rest_rot[n])
    rig.set("head", RX(0.16) @ rig.rest_rot["head"])


def hand_frame(rig, side):
    """Base da mão no descanso: dedos (punho -> meio dos dedos) e normal da palma (para baixo no descanso em A)."""
    s = "l" if side < 0 else "r"
    h = rig.rest_head
    fd = (h[f"middle_01_{s}"] - h[f"hand_{s}"]).normalized()
    across = (h[f"index_01_{s}"] - h[f"pinky_01_{s}"]).normalized()
    n = fd.cross(across).normalized()
    # a palma fica do lado do polegar dobrado; no descanso em A ela olha para baixo
    if n.z > 0:
        n = -n
    return fd, n


def hand_target(rig, side, bike):
    """Rotação do mundo (delta) e posição do punho para a palma abraçar a manopla."""
    s = "l" if side < 0 else "r"
    out = 1.0 if side < 0 else -1.0     # para fora: +X do Blender na esquerda, -X na direita
    fd0, n0 = hand_frame(rig, side)
    fd = Vector((out * 0.30, -0.90, -0.32)).normalized()
    n = Vector((-out * 0.12, 0.20, -1.0))
    n = (n - fd * n.dot(fd)).normalized()
    D = rot2((fd0, n0), (fd, n))
    h = rig.rest_head
    palm_off = (h[f"middle_01_{s}"] - h[f"hand_{s}"]) * 0.55 + n0 * 0.022
    grip = bike.grip(side)
    palm = grip - n * 0.021           # palma em cima da manopla (raio 2 cm)
    wrist = palm - D @ palm_off
    return D, wrist, fd, n


FINGERS = ("index", "middle", "ring", "pinky")


def pose_hand(rig, side, D, fd, n):
    s = "l" if side < 0 else "r"
    rig.set(f"hand_{s}", D @ rig.rest_rot[f"hand_{s}"])
    axis = fd.cross(n).normalized()          # girar em volta dele leva os dedos para o lado da palma
    for f in FINGERS:
        for seg, ang in (("01", 52), ("02", 60), ("03", 38)):
            b = f"{f}_{seg}_{s}"
            if b in rig.pb:
                rig.turn(b, Matrix.Rotation(math.radians(ang), 3, axis))
    for seg, ang in (("02", 22), ("03", 25)):
        b = f"thumb_{seg}_{s}"
        if b in rig.pb:
            rig.turn(b, Matrix.Rotation(math.radians(ang), 3, axis))


def foot_targets(rig, side, bike, phi):
    """Tornozelo-alvo e rotação do pé para a bola do pé (ball) ficar em cima do pedal."""
    s = "l" if side < 0 else "r"
    a = phi if side > 0 else phi + 180.0
    toe_down = math.radians(12.0 + 10.0 * math.cos(math.radians(a - 165.0)))   # tornozelo trabalha na volta
    R = Matrix.Rotation(toe_down, 3, "X")
    h = rig.rest_head
    ball_rest_h = h[f"ball_{s}"].z                     # altura da junta da bola acima da sola no descanso
    top = bike.pedal_top(phi, side)
    ball = top + Vector((0, 0, ball_rest_h * 0.9))
    ankle = ball - R @ (h[f"ball_{s}"] - h[f"foot_{s}"])
    return ankle, R, ball


def hip_target(rig, bike):
    hsit = HIP_ABOVE_SEAT * rig.height / 1.75
    return bike.seat() + Vector((0, 0.025 * bike.s, hsit))   # +Y = para trás: senta na parte larga do selim


def leg_ratio(rig, bike):
    """Pior caso (quadril -> tornozelo) / (coxa + canela) numa volta, sem posar (para escolher a escala)."""
    hip = hip_target(rig, bike)
    worst = 0.0
    for s, side in (("l", -1), ("r", 1)):
        hp = hip + Vector((rig.rest_head[f"thigh_{s}"].x, 0, 0))
        for k in range(NF):
            ankle, _, _ = foot_targets(rig, side, bike, k * 360.0 / NF)
            worst = max(worst, (ankle - hp).length / sum(rig.L[s]))
    return worst


def solve_lean(rig, bike, hip):
    wr = {side: hand_target(rig, side, bike)[1] for side in (-1, 1)}

    def ratio(lean):
        pose_torso(rig, hip, lean)
        return max((rig.head(f"upperarm_{s}") - wr[side]).length / sum(rig.La[s]) for s, side in (("l", -1), ("r", 1)))

    lo, hi = 0.0, 1.3
    if ratio(lo) <= ARM_REACH:
        return 0.0
    for _ in range(16):
        mid = (lo + hi) / 2
        if ratio(mid) > ARM_REACH:
            lo = mid
        else:
            hi = mid
    return hi


def pose_frame(rig, bike, hip, lean, phi):
    roll = math.radians(2.2) * math.sin(math.radians(phi))   # quadril balança de leve com cada pedalada
    pose_torso(rig, hip, lean, roll)
    errs = {}
    for s, side in (("l", -1), ("r", 1)):
        D, wrist, fd, n = hand_target(rig, side, bike)
        out = 1.0 if side < 0 else -1.0
        errs[f"arm_{s}"] = two_bone(rig, f"upperarm_{s}", f"lowerarm_{s}", f"hand_{s}", wrist,
                                    Vector((out * 0.75, 0.45, -0.55)), Vector((0, 1, 0)))
        pose_hand(rig, side, D, fd, n)
    for s, side in (("l", -1), ("r", 1)):
        ankle, R, _ = foot_targets(rig, side, bike, phi)
        out = 1.0 if side < 0 else -1.0
        errs[f"leg_{s}"] = two_bone(rig, f"thigh_{s}", f"calf_{s}", f"foot_{s}", ankle,
                                    Vector((out * 0.12, -1.0, 0.35)), Vector((0, -1, 0)))
        rig.set(f"foot_{s}", R @ rig.rest_rot[f"foot_{s}"])
    return errs


def key_all(rig, frame):
    for b in rig.pb:
        b.keyframe_insert("location", frame=frame)
        b.keyframe_insert("rotation_quaternion", frame=frame)


def ue_cm(v):
    """Ponto do Blender (espaço do herói) -> espaço do componente da malha na Unreal (cm)."""
    return [round(v.x * 100, 2), round(-v.y * 100, 2), round(v.z * 100, 2)]


def export_anim(rig, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for o in rig.meshes:
        bpy.data.objects.remove(o, do_unlink=True)
    rig.meshes = []
    bpy.ops.object.select_all(action="DESELECT")
    rig.arm.select_set(True)
    bpy.context.view_layer.objects.active = rig.arm
    # mesmas opções do gen_bandage_anim.py (animação que já entrou na Unreal certinha)
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE"},
                             add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X",
                             armature_nodetype="NULL", use_armature_deform_only=False,
                             bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                             bake_anim_force_startend_keying=True, bake_anim_step=1.0, bake_anim_simplify_factor=0.0,
                             axis_forward="-Z", axis_up="Y", global_scale=1.0, apply_scale_options="FBX_SCALE_NONE",
                             use_space_transform=True, apply_unit_scale=True)


def build_hero(name, path, geo, s):
    reset()
    rig = Rig(path)
    bike = Bike(geo, s)
    for o in rig.meshes:          # sem a malha o update de pose é bem mais rápido
        o.hide_viewport = True
    act = bpy.data.actions.new(f"Bike_Pedal_{name}")
    rig.arm.animation_data_create()
    rig.arm.animation_data.action = act
    hip = hip_target(rig, bike)
    lean = solve_lean(rig, bike, hip)
    info = {"height_m": round(rig.height, 3), "leg_len_m": {k: round(sum(v), 3) for k, v in rig.L.items()},
            "arm_len_m": {k: round(sum(v), 3) for k, v in rig.La.items()}, "lean_deg": round(math.degrees(lean), 1),
            "leg_ratio_worst": round(leg_ratio(rig, bike), 3)}
    worst = {"reach_m": 0.0, "ball_to_pedal_m": 0.0, "palm_to_grip_m": 0.0}
    ref = {}
    for k in range(NF + 1):
        phi = (k % NF) * 360.0 / NF
        bpy.context.scene.frame_set(k)
        errs = pose_frame(rig, bike, hip, lean, phi)
        key_all(rig, k)
        worst["reach_m"] = max(worst["reach_m"], max(errs.values()))
        for s, side in (("l", -1), ("r", 1)):
            _, _, ball = foot_targets(rig, side, bike, phi)
            worst["ball_to_pedal_m"] = max(worst["ball_to_pedal_m"], (rig.head(f"ball_{s}") - ball).length)
            D, wrist, fd, n = hand_target(rig, side, bike)
            worst["palm_to_grip_m"] = max(worst["palm_to_grip_m"], (rig.head(f"hand_{s}") - wrist).length)
        if k in (0, 9, 18, 27):
            for b in ("pelvis", "hand_l", "hand_r", "ball_l", "ball_r", "head"):
                ref[(k, b)] = rig.head(b).copy()
    info["checks"] = {k: round(v, 4) for k, v in worst.items()}
    info["ue_component_cm_frame0"] = {b: ue_cm(ref[(0, b)]) for b in ("pelvis", "hand_l", "hand_r", "ball_l", "ball_r")}
    info["ue_component_cm_frame9"] = {b: ue_cm(ref[(9, b)]) for b in ("ball_l", "ball_r")}
    info["previews"] = preview(rig, name, geo, bike.s)
    out = os.path.join(OUT, f"A_Bike_Pedal_{name}.fbx")
    export_anim(rig, out)
    info["fbx"] = os.path.relpath(out, REPO)
    info["roundtrip_max_err_cm"] = roundtrip(out, ref)
    INFO["heroes"][name] = info
    print(f"[bike] {name}: inclinação {info['lean_deg']} graus, perna {info['leg_ratio_worst']}, {info['checks']}, "
          f"ida e volta {info['roundtrip_max_err_cm']} cm")
    return info


def roundtrip(path, ref):
    objs = import_fbx(path)
    arm2 = next(o for o in objs if o.type == "ARMATURE")
    sc = bpy.context.scene
    worst = 0.0
    start = int(round(arm2.animation_data.action.frame_range[0])) if arm2.animation_data else 0
    for (k, b), p in ref.items():
        sc.frame_set(k + start)
        bpy.context.view_layer.update()
        worst = max(worst, ((arm2.matrix_world @ arm2.pose.bones[b].head) - p).length)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    return round(worst * 100, 2)


# ------------------------------------------------------------------ 4. prévia (herói com malha + bicicleta)
def preview(rig, name, geo, s):
    """Prévia com a cena viva (malha do herói deformada pela ação recém-chaveada) + bicicleta montada."""
    for o in rig.meshes:
        o.hide_viewport = False
        o.hide_render = False
    bike = Bike(geo, s)
    added = []
    parts = {}
    for n in ("SM_VEH_BikeQuadroSemPedivela", "SM_VEH_BikePedivela", "SM_VEH_BikePedal", "SM_VEH_BikeSelim",
              "SM_VEH_BikeGuidao"):
        objs = import_fbx(os.path.join(TRIPO, f"{n}.fbx"))
        added += objs
        parts[n] = next(o for o in objs if o.type == "MESH" and not o.name.startswith("UCX"))
    for o in [o for o in added if o.name.startswith("UCX")]:
        o.hide_render = True
    pedal_l = parts["SM_VEH_BikePedal"].copy()
    bpy.context.scene.collection.objects.link(pedal_l)
    added.append(pedal_l)
    wheels = []
    for x in (0.56, -0.56):
        objs = import_fbx(os.path.join(TRIPO, "SM_VEH_BikeRoda.fbx"))
        added += objs
        w = next(o for o in objs if o.type == "MESH")
        w.matrix_world = bike.M @ Matrix.Translation((x, 0, -FRAME_GROUND))
        wheels.append(w)
    parts["SM_VEH_BikeQuadroSemPedivela"].matrix_world = bike.M
    parts["SM_VEH_BikeSelim"].matrix_world = bike.M @ Matrix.Translation((0, 0, -SEAT_DROP))
    parts["SM_VEH_BikeGuidao"].matrix_world = bike.M
    mat = bpy.data.materials.new("bike")
    mat.diffuse_color = (0.30, 0.36, 0.70, 1)
    for o in list(parts.values()) + [pedal_l] + wheels:
        o.data.materials.clear()
        o.data.materials.append(mat)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x, sc.render.resolution_y = 640, 640
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    added.append(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 2.2
    aim = bpy.data.objects.new("aim", None)
    sc.collection.objects.link(aim)
    added.append(aim)
    aim.location = (0, 0, 0.8)
    tc = cam.constraints.new("TRACK_TO")
    tc.target, tc.track_axis, tc.up_axis = aim, "TRACK_NEGATIVE_Z", "UP_Y"
    os.makedirs(os.path.join(OUT, "previews"), exist_ok=True)
    g = geo
    files = []
    for k in (0, 9, 18, 27):
        phi = k * 360.0 / NF
        sc.frame_set(k)
        C = bike.M @ bike.crank(phi)
        parts["SM_VEH_BikePedivela"].matrix_world = C
        for ob, side in ((parts["SM_VEH_BikePedal"], 1), (pedal_l, -1)):
            a = 0.0 if side > 0 else 180.0
            sp = Vector((g["crank_len"] * math.cos(math.radians(a)), -side * g["spindle_y"],
                         -g["crank_len"] * math.sin(math.radians(a))))
            local = Matrix.Translation(sp) @ Matrix.Rotation(math.radians(-phi), 4, "Y")
            if side < 0:
                local = local @ Matrix.Rotation(math.pi, 4, "Z")
            ob.matrix_world = C @ local
        for view, loc, rot in (("lado", (-2.6, 0.0, 0.8), None), ("tres_quartos", (-1.8, -2.0, 1.4), None),
                               ("frente", (0.0, -2.8, 1.0), None)):
            if k not in (0, 9) and view != "lado":
                continue
            cam.location = loc
            f = os.path.join(OUT, "previews", f"{name}_{view}_f{k:02d}.png")
            sc.render.filepath = f
            bpy.ops.render.render(write_still=True)
            files.append(os.path.relpath(f, REPO).replace(os.sep, "/"))
    # guidão virado 20 graus (direita) no eixo da caixa de direção, com a roda da frente junto
    sc.frame_set(0)
    axis = Vector((-0.07, 0.0, 0.27)).normalized()   # HEAD_T - HEAD_B do villa_kit.py (topo para trás)
    St = Matrix.Translation(g["head_b"]) @ Matrix.Rotation(math.radians(-20), 4, axis) @ Matrix.Translation(-g["head_b"])
    parts["SM_VEH_BikeGuidao"].matrix_world = bike.M @ St
    wheels[0].matrix_world = bike.M @ St @ Matrix.Translation((0.56, 0, -FRAME_GROUND))
    cam.location = (-1.6, -2.2, 1.6)
    f = os.path.join(OUT, "previews", f"{name}_guidao20.png")
    sc.render.filepath = f
    bpy.ops.render.render(write_still=True)
    files.append(os.path.relpath(f, REPO).replace(os.sep, "/"))
    for o in added:
        bpy.data.objects.remove(o, do_unlink=True)
    return files


# ------------------------------------------------------------------ main
def choose_scale(geo):
    if FORCED_SCALE:
        return FORCED_SCALE, "pedida na linha de comando"
    best = SCALE_RANGE[0]
    for i in range(int((SCALE_RANGE[1] - SCALE_RANGE[0]) / 0.01) + 1):
        s = round(SCALE_RANGE[0] + i * 0.01, 2)
        worst = 0.0
        for name, path in HEROES.items():
            reset()
            rig = Rig(path)
            worst = max(worst, leg_ratio(rig, Bike(geo, s)))
        if worst <= LEG_REACH:
            best = s
        else:
            break
    return best, f"maior escala com perna <= {LEG_REACH} nos dois heróis"


def main():
    os.makedirs(OUT, exist_ok=True)
    geo = split_bike()
    s, why = choose_scale(geo)
    INFO["bike_scale"] = s
    INFO["bike_scale_why"] = why
    g = geo
    INFO["cpp"] = {   # valores para o AJRBike (cm, espaço da bicicleta SEM a escala; o C++ multiplica por BikeScale)
        "BikeScale": s,
        "CrankPivot": [round(g["bb"].x * 100, 2), 0.0, round((g["bb"].z + FRAME_GROUND) * 100, 2)],
        "CrankLength": round(g["crank_len"] * 100, 2),
        "SeatDrop": round(SEAT_DROP * 100, 2),
        "SteerPivot": [round(g["head_b"].x * 100, 2), 0.0, round((g["head_b"].z + FRAME_GROUND) * 100, 2)],
        "SteerTiltDeg": round(g["head_tilt_deg"], 2),
        "PedalSpindleY": round(g["spindle_y"] * 100, 2),
        "PedalAnimLength_s": NF / FPS,
        "PhaseAtFrame0_deg": 0.0,
    }
    for name, path in HEROES.items():
        build_hero(name, path, geo, s)
    with open(os.path.join(OUT, "bike_rider_info.json"), "w", encoding="utf-8") as fh:
        json.dump(INFO, fh, ensure_ascii=False, indent=1)
    print(f"[bike] pronto: escala {s} ({why}); {os.path.join(OUT, 'bike_rider_info.json')}")


main()
