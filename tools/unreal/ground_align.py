"""[A-098] Assentar objetos no chão da cidade (heightmap r16 do Landscape): altura, normal e regras por tipo.

Módulo reutilizável (não roda sozinho). A matemática é Python puro (testada em tests/python/test_ground_align.py);
só as funções do fim (from_landscape, mesh_local_min_z, place_on_ground) usam o módulo `unreal`, importado tarde.

API
---
HeightField(h16, res, ox, oy, oz=0, sx=100, sy=100, sz=100)
    h16: sequência de uint16 (res * res, linha a linha, igual ao city_height.r16); ox/oy/oz = posição do Landscape;
    sx/sy/sz = escala do Landscape (100 = 1 m por quad e 512 m de faixa de altura).
  .z(X, Y)                 altura do chão (cm) com interpolação bilinear
  .normal(X, Y, step=None) normal (nx, ny, nz) por diferenças centrais (step padrão = 1 quad)
  .slope_deg(X, Y)         inclinação em graus
  HeightField.from_r16(path, res, ox, oy, oz, sx, sy, sz)
  HeightField.from_landscape(land, r16_path, res)         (usa unreal)
  HeightField.from_city(land, work_dir)                   (lê res do city_layout.json + city_height.r16)

Regras (devolvem Placement(z, roll, pitch, yaw, tilt_deg, sink_cm); z = onde vai o PIVÔ do ator):
  rule_building(hf, X, Y, yaw, half_x, half_y, min_z_local=0, sink=15)
      casa/prédio: média do chão nos 4 cantos da caixa GIRADA, menos 15 cm; fica reto (sem inclinar)
  rule_plant(hf, X, Y, yaw, radius, min_z_local=0, fraction=0.35, max_deg=10, sink=3)
      árvore/planta: inclina 35% da normal, no máximo 10 graus; afunda tan(inclinação) * raio * 0,5 + 3 cm
  rule_align(hf, X, Y, yaw, half_x, half_y, min_z_local=0, sink=4, max_extra_sink=35)
      pedra/prop/carro: alinha à normal inteira; o plano passa pelo centro e o ator afunda o quanto o canto mais
      "flutuante" ficaria acima do chão (até 35 cm) + 4 cm
  KIND_RULES: "building"/"casa"/"predio" -> building; "tree"/"plant"/"arvore" -> plant; "rock"/"prop"/"car"/"carro" -> align
  min_z_local = menor Z da malha no espaço dela (cm, já com escala): pivô fora da base também assenta certo

rotator_from_up(up, yaw_deg)  -> (roll, pitch, yaw) da Unreal com o eixo Z do ator = up e a frente no yaw pedido
partial_up(normal, fraction, max_deg) -> normal "meio caminho" com limite de graus
rotated_corners(X, Y, yaw_deg, half_x, half_y) -> 4 cantos da caixa girada

Com a Unreal:
  mesh_local_box(actor) -> (min_x, min_y, min_z, max_x, max_y, max_z) da malha em cm, já com a escala do ator
      (StaticMeshActor: bounding box da malha; outro ator: get_actor_bounds no momento, sem girar)
  place_on_ground(actor, kind, hf, sink=None, **kw) -> dict
      lê X, Y, yaw do ator, mede a malha, aplica a regra do tipo e move/gira o ator (sem varrer colisão)

Uso no dress (exemplo):
    import ground_align as ga
    hf = ga.HeightField.from_city(land, WORK)
    a = ACTORS.spawn_actor_from_object(mesh, unreal.Vector(X, Y, 0), unreal.Rotator(0, 0, yaw))
    a.set_actor_scale3d(...)
    ga.place_on_ground(a, "car", hf)        # ou "building", "plant", "rock", "prop"
Coordenadas: as da Unreal (cm). A planta da cidade usa X = x * 100, Y = -y * 100 (ver dress_city_v*.py).
"""
from __future__ import annotations

import json
import math
import os
from array import array
from collections import namedtuple

Placement = namedtuple("Placement", "z roll pitch yaw tilt_deg sink_cm")


# ------------------------------------------------------------------ vetores
def _norm(v):
    ln = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if ln < 1e-9:
        return (0.0, 0.0, 1.0)
    return (v[0] / ln, v[1] / ln, v[2] / ln)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


# ------------------------------------------------------------------ campo de altura
class HeightField:
    def __init__(self, h16, res, ox, oy, oz=0.0, sx=100.0, sy=100.0, sz=100.0):
        if len(h16) != res * res:
            raise ValueError(f"heightmap com {len(h16)} amostras; esperado {res * res}")
        self.h, self.res = h16, int(res)
        self.ox, self.oy, self.oz = float(ox), float(oy), float(oz)
        self.sx, self.sy, self.sz = float(sx), float(sy), float(sz)

    @classmethod
    def from_r16(cls, path, res, ox, oy, oz=0.0, sx=100.0, sy=100.0, sz=100.0):
        h = array("H")
        with open(path, "rb") as fh:
            h.frombytes(fh.read())
        return cls(h, res, ox, oy, oz, sx, sy, sz)

    @classmethod
    def from_landscape(cls, land, r16_path, res):
        loc, sc = land.get_actor_location(), land.get_actor_scale3d()
        return cls.from_r16(r16_path, res, loc.x, loc.y, loc.z, sc.x, sc.y, sc.z)

    @classmethod
    def from_city(cls, land, work_dir):
        with open(os.path.join(work_dir, "city_layout.json"), encoding="utf-8") as fh:
            res = int(json.load(fh)["landscape"]["res"])
        return cls.from_landscape(land, os.path.join(work_dir, "city_height.r16"), res)

    def z(self, X, Y):
        r = self.res
        fx = min(max((X - self.ox) / self.sx, 0.0), r - 1.001)
        fy = min(max((Y - self.oy) / self.sy, 0.0), r - 1.001)
        ix, iy = int(fx), int(fy)
        tx, ty = fx - ix, fy - iy
        h = self.h
        top = h[iy * r + ix] * (1 - tx) + h[iy * r + ix + 1] * tx
        bot = h[(iy + 1) * r + ix] * (1 - tx) + h[(iy + 1) * r + ix + 1] * tx
        return self.oz + ((top * (1 - ty) + bot * ty) - 32768.0) * self.sz / 128.0

    def normal(self, X, Y, step=None):
        st = float(step) if step else self.sx
        dzx = (self.z(X + st, Y) - self.z(X - st, Y)) / (2 * st)
        dzy = (self.z(X, Y + st) - self.z(X, Y - st)) / (2 * st)
        return _norm((-dzx, -dzy, 1.0))

    def slope_deg(self, X, Y):
        return math.degrees(math.acos(max(-1.0, min(1.0, self.normal(X, Y)[2]))))


# ------------------------------------------------------------------ rotação
def rotator_from_up(up, yaw_deg):
    """(roll, pitch, yaw) da Unreal com o eixo Z do ator = up, mantendo a frente (X) o mais perto do yaw pedido."""
    zax = _norm(up)
    f0 = (math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg)), 0.0)
    d = _dot(f0, zax)
    xax = _norm((f0[0] - d * zax[0], f0[1] - d * zax[1], f0[2] - d * zax[2]))
    yax = _cross(zax, xax)  # Unreal: Y = Z x X
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, xax[2]))))
    yaw = math.degrees(math.atan2(xax[1], xax[0]))
    roll = math.degrees(math.atan2(-yax[2], zax[2]))
    return roll, pitch, yaw


def up_from_rotator(roll, pitch, yaw):
    """Eixo Z do ator para um rotator da Unreal (para conferir)."""
    r, p, y = (math.radians(a) for a in (roll, pitch, yaw))
    return (-(math.cos(r) * math.sin(p) * math.cos(y) + math.sin(r) * math.sin(y)),
            -(math.cos(r) * math.sin(p) * math.sin(y) - math.sin(r) * math.cos(y)),
            math.cos(r) * math.cos(p))


def partial_up(normal, fraction=1.0, max_deg=90.0):
    n = _norm(normal)
    v = _norm((n[0] * fraction, n[1] * fraction, 1.0 - fraction + n[2] * fraction))
    ang = math.degrees(math.acos(max(-1.0, min(1.0, v[2]))))
    if ang > max_deg:
        hl = math.hypot(v[0], v[1]) or 1.0
        s, c = math.sin(math.radians(max_deg)), math.cos(math.radians(max_deg))
        v = (v[0] / hl * s, v[1] / hl * s, c)
    return v


def rotated_corners(X, Y, yaw_deg, half_x, half_y):
    c, s = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    out = []
    for dx, dy in ((half_x, half_y), (half_x, -half_y), (-half_x, half_y), (-half_x, -half_y)):
        out.append((X + dx * c - dy * s, Y + dx * s + dy * c))
    return out


# ------------------------------------------------------------------ regras
def rule_building(hf, X, Y, yaw, half_x, half_y, min_z_local=0.0, sink=15.0):
    zs = [hf.z(x, y) for x, y in rotated_corners(X, Y, yaw, half_x, half_y)]
    base = sum(zs) / 4.0
    return Placement(base - sink - min_z_local, 0.0, 0.0, yaw, 0.0, sink)


def rule_plant(hf, X, Y, yaw, radius, min_z_local=0.0, fraction=0.35, max_deg=10.0, sink=3.0):
    up = partial_up(hf.normal(X, Y), fraction, max_deg)
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, up[2]))))
    roll, pitch, yaw2 = rotator_from_up(up, yaw)
    extra = math.tan(math.radians(tilt)) * radius * 0.5
    total = sink + extra
    return Placement(hf.z(X, Y) - total - min_z_local, roll, pitch, yaw2, tilt, total)


def rule_align(hf, X, Y, yaw, half_x, half_y, min_z_local=0.0, sink=4.0, max_extra_sink=35.0):
    n = hf.normal(X, Y, step=max(hf.sx, min(half_x, half_y)))  # normal na escala do objeto (carro não "pula" em calombo)
    roll, pitch, yaw2 = rotator_from_up(n, yaw)
    z0 = hf.z(X, Y)
    float_max = 0.0
    for x, y in rotated_corners(X, Y, yaw, half_x, half_y):
        # altura do plano do objeto naquele canto: z0 - (n.x * dx + n.y * dy) / n.z
        plane = z0 - (n[0] * (x - X) + n[1] * (y - Y)) / max(0.2, n[2])
        float_max = max(float_max, plane - hf.z(x, y))
    extra = min(max_extra_sink, float_max)
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, n[2]))))
    total = sink + extra
    # pivô: o deslocamento min_z_local é ao longo do eixo Z inclinado; na vertical, ~ min_z_local * n.z
    return Placement(z0 - total - min_z_local * n[2], roll, pitch, yaw2, tilt, total)


KIND_RULES = {"building": "building", "casa": "building", "predio": "building",
              "tree": "plant", "plant": "plant", "arvore": "plant", "planta": "plant",
              "rock": "align", "pedra": "align", "prop": "align", "car": "align", "carro": "align"}


def place(hf, kind, X, Y, yaw, box, sink=None, **kw):
    """box = (min_x, min_y, min_z, max_x, max_y, max_z) local em cm (com escala). Devolve Placement."""
    rule = KIND_RULES.get(kind, "align")
    half_x = max(1.0, (box[3] - box[0]) * 0.5)
    half_y = max(1.0, (box[4] - box[1]) * 0.5)
    # centro da caixa fora do pivô (malha deslocada): corrige X/Y da conta dos cantos
    cx, cy = (box[0] + box[3]) * 0.5, (box[1] + box[4]) * 0.5
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    BX, BY = X + cx * c - cy * s, Y + cx * s + cy * c
    if rule == "building":
        p = rule_building(hf, BX, BY, yaw, half_x, half_y, box[2], 15.0 if sink is None else sink)
    elif rule == "plant":
        p = rule_plant(hf, X, Y, yaw, kw.get("radius", min(half_x, half_y) * 0.35), box[2],
                       kw.get("fraction", 0.35), kw.get("max_deg", 10.0), 3.0 if sink is None else sink)
    else:
        p = rule_align(hf, BX, BY, yaw, half_x, half_y, box[2], 4.0 if sink is None else sink,
                       kw.get("max_extra_sink", 35.0))
    return p


# ------------------------------------------------------------------ Unreal
def mesh_local_box(actor):
    import unreal  # noqa: WPS433

    sc = actor.get_actor_scale3d()
    comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    sm = comp.static_mesh if comp else None
    if sm is not None:
        bb = sm.get_bounding_box()
        return (bb.min.x * sc.x, bb.min.y * sc.y, bb.min.z * sc.z, bb.max.x * sc.x, bb.max.y * sc.y, bb.max.z * sc.z)
    # ator com outras malhas (Blueprint, esqueleto): bounds no mundo, medidos sem giro
    rot = actor.get_actor_rotation()
    actor.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
    origin, ext = actor.get_actor_bounds(False)
    loc = actor.get_actor_location()
    actor.set_actor_rotation(rot, False)
    return (origin.x - ext.x - loc.x, origin.y - ext.y - loc.y, origin.z - ext.z - loc.z,
            origin.x + ext.x - loc.x, origin.y + ext.y - loc.y, origin.z + ext.z - loc.z)


def place_on_ground(actor, kind, hf, sink=None, **kw):
    """Aplica a regra do tipo no ator já criado (usa X, Y e yaw atuais). Devolve um dict para o relatório."""
    import unreal  # noqa: WPS433

    loc = actor.get_actor_location()
    yaw = actor.get_actor_rotation().yaw
    box = mesh_local_box(actor)
    p = place(hf, kind, loc.x, loc.y, yaw, box, sink, **kw)
    actor.set_actor_location(unreal.Vector(loc.x, loc.y, p.z), False, False)
    actor.set_actor_rotation(unreal.Rotator(p.roll, p.pitch, p.yaw), False)
    return {"label": actor.get_actor_label(), "kind": kind, "z": round(p.z, 1), "tilt": round(p.tilt_deg, 1),
            "sink": round(p.sink_cm, 1)}
