"""Graveto alien (1ª arma, corpo a corpo): galho torto que parece uma espada, com veias brilhando.
Uso: bpy52 python make_stick.py -- <pasta_saida>
Saída: SM_AlienStick.fbx (~0,95 m; pegada na origem; lâmina ao longo de +X; slots M_L01_VertexColor e M_L01_Glow)
"""
import math
import os
import sys

import bpy
import bmesh  # noqa: E402 (bmesh só existe depois do bpy)
from mathutils import Vector

OUT = sys.argv[-1]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
m_col = bpy.data.materials.new("M_L01_VertexColor")
m_glow = bpy.data.materials.new("M_L01_Glow")
me = bpy.data.meshes.new("SM_AlienStick")
me.materials.append(m_col)
me.materials.append(m_glow)
bm = bmesh.new()
col_layer = bm.loops.layers.color.new("Col")

BARK = (0.24, 0.13, 0.22)
BARK_L = (0.36, 0.2, 0.33)
WRAP = (0.55, 0.42, 0.28)
GLOW = (0.25, 1.0, 0.85)


def paint(faces, c, mat=0):
    for f in faces:
        f.material_index = mat
        for lp in f.loops:
            lp[col_layer] = (*c, 1.0)


def tube(pts, radii, sides, c, mat=0, flat=1.0):
    rings = []
    for i, (p, r) in enumerate(zip(pts, radii)):
        p = Vector(p)
        t = (Vector(pts[min(i + 1, len(pts) - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((0, 1, 0))
        a = t.cross(up).normalized()
        b = t.cross(a).normalized()
        ring = []
        for k in range(sides):
            th = k / sides * 2 * math.pi
            ring.append(bm.verts.new(p + a * math.cos(th) * r + b * math.sin(th) * r * flat))
        rings.append(ring)
    faces = []
    for i in range(len(rings) - 1):
        for k in range(sides):
            faces.append(bm.faces.new((rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k])))
    faces.append(bm.faces.new(rings[0][::-1]))
    faces.append(bm.faces.new(rings[-1]))
    paint(faces, c, mat)
    return faces


# cabo (pegada na origem, de -0,14 a +0,1 m) com faixas de cipó
handle = [(-0.15 + 0.03 * i, 0.0, 0.0) for i in range(10)]
tube(handle, [0.024] * 10, 8, WRAP)
for x in (-0.12, -0.06, 0.0, 0.06):
    tube([(x - 0.008, 0, 0), (x + 0.008, 0, 0)], [0.029, 0.029], 8, BARK)
# pomo: nó de madeira com cristal
tube([(-0.17, 0, 0), (-0.15, 0, 0), (-0.13, 0, 0)], [0.02, 0.038, 0.03], 8, BARK_L)
tube([(-0.22, 0, 0), (-0.18, 0, 0), (-0.165, 0, 0)], [0.0, 0.024, 0.015], 6, GLOW, 1)
# guarda: dois galhinhos cruzados
for s in (-1, 1):
    tube([(0.11, 0, 0), (0.13, s * 0.06, 0.01), (0.12, s * 0.11, 0.03)], [0.02, 0.014, 0.004], 6, BARK)
# lâmina: galho achatado, levemente torto, afinando até a ponta
blade = []
radii = []
n = 16
for i in range(n + 1):
    t = i / n
    x = 0.12 + t * 0.66
    blade.append((x, 0.018 * math.sin(t * 5.0), 0.02 * math.sin(t * 3.1)))
    radii.append(0.034 * (1 - t) ** 0.7 + 0.004)
bf = tube(blade, radii, 8, BARK, 0, flat=0.45)
for i, f in enumerate(bf):
    if i % 7 == 3:
        paint([f], BARK_L)
# veias brilhando ao longo da lâmina (dos dois lados)
for s in (-1, 1):
    vein = [(p[0], p[1], p[2] + s * r * 0.42) for p, r in zip(blade[1:-2], radii[1:-2])]
    tube(vein, [0.0045] * len(vein), 4, GLOW, 1)
# brotos laterais com pontas de cristal
for (t, s) in ((0.35, 1), (0.6, -1)):
    i = int(t * n)
    base = Vector(blade[i])
    tip = base + Vector((0.05, s * 0.05, 0.02))
    tube([tuple(base), tuple(base.lerp(tip, 0.6)), tuple(tip)], [0.012, 0.008, 0.002], 5, BARK)
    tube([tuple(tip), tuple(tip + Vector((0.02, s * 0.02, 0.0)))], [0.008, 0.0], 5, GLOW, 1)

bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bm.to_mesh(me)
bm.free()
ob = bpy.data.objects.new("SM_AlienStick", me)
bpy.context.scene.collection.objects.link(ob)
ob.select_set(True)
dims = ob.dimensions
print("dims", [round(d, 3) for d in dims], "tris", sum(len(p.vertices) - 2 for p in me.polygons))
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "SM_AlienStick.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, mesh_smooth_type="FACE", colors_type="SRGB")
print("ok")
