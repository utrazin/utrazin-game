"""Pickups 3D do chão (A-082): munição (células de plasma), cura, bandagem, kit médico, fúria, nitro, conserto e o anel de brilho.

Gera tudo por código (fonte reproduzível; não há .blend para editar à mão):
  assets/work/props/pickups/SM_Pickup_<Nome>.fbx   malha para a Unreal (tamanho real em m, pivô na base, frente +X)
  assets/work/props/pickups/SM_Pickup_<Nome>.glb   mesma malha com materiais (para olhar fora da Unreal)
  assets/work/props/pickups/SM_Pickup_<Nome>_preview.png   prévia (Workbench)
  assets/work/props/pickups/pickups_contact_sheet.png      todas juntas
  assets/work/props/pickups/T_Pickup_Palette.png  paleta 4x4 (UV de cada face cai no meio de uma cor)
  assets/work/props/pickups/T_Pickup_RingGlow.png anel de brilho do chão (máscara em tons de cinza)
  assets/work/props/pickups/pickups.json          medidas, triângulos e cor do núcleo de cada malha

Materiais (nomes dos slots na Unreal): "Body" (paleta, fosco tipo argila) e "Core" (núcleo que brilha; o C++ pulsa).
O anel usa um slot só: "Ring".

Uso (Blender 5.3 em modo fundo):
  blender -b --python tools/blender/pickups/make_pickups.py -- --out assets/work/props/pickups [--no-preview]
ou com o módulo bpy:
  python -I tools/blender/pickups/make_pickups.py -- --out <pasta>
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys

# ------------------------------------------------------------------ lógica pura (sem bpy)

# Paleta "argila alienígena" (sRGB). Índice = posição na grade 4x4 (linha de cima primeiro).
PALETTE = [
    (0x2B, 0x2F, 0x3A),  # 0 metal escuro
    (0x5B, 0x64, 0x75),  # 1 metal médio
    (0xA9, 0xB4, 0xC2),  # 2 metal claro
    (0x6A, 0x2B, 0xA0),  # 3 violeta (pistola)
    (0xC4, 0x56, 0x1E),  # 4 laranja (escopeta)
    (0xC9, 0xA0, 0x4A),  # 5 latão
    (0x1F, 0x8F, 0xA8),  # 6 ciano (rifle)
    (0xED, 0xE3, 0xCC),  # 7 creme (bandagem)
    (0xF2, 0xF2, 0xF0),  # 8 branco
    (0xC0, 0x28, 0x2D),  # 9 vermelho
    (0x2A, 0x1B, 0x3D),  # 10 rocha roxa
    (0x21, 0x56, 0xA8),  # 11 azul (nitro)
    (0x2E, 0x9E, 0x4F),  # 12 verde (conserto)
    (0x15, 0x16, 0x1A),  # 13 borracha preta
    (0xE2, 0xB3, 0x3A),  # 14 amarelo de aviso
    (0xD9, 0x57, 0x7A),  # 15 rosa
]
GRID = 4
SWATCH_PX = 32


def swatch_uv(index: int) -> tuple[float, float]:
    """Centro da cor na textura (UV do Blender: v=1 em cima)."""
    col, row = index % GRID, index // GRID
    return (col + 0.5) / GRID, 1.0 - (row + 0.5) / GRID


def palette_pixels():
    size = GRID * SWATCH_PX
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            row.append(PALETTE[(y // SWATCH_PX) * GRID + (x // SWATCH_PX)])
        rows.append(row)
    return rows


def ring_value(u: float, v: float) -> float:
    """Anel do chão: aro brilhante em r=0,78 e um véu fraco por dentro; 0 na borda do quad."""
    r = math.hypot(u - 0.5, v - 0.5) * 2.0
    rim = math.exp(-((r - 0.78) / 0.07) ** 2)
    fill = 0.28 * max(0.0, 1.0 - r / 0.8) ** 1.5
    fade = max(0.0, min(1.0, (1.0 - r) / 0.08))
    return max(0.0, min(1.0, (rim + fill) * fade))


# Cada pickup: cor do núcleo (linear, igual ao C++), escala de jogo sugerida (o C++ aplica).
ITEMS = {
    "CellPistol": {"core": (0.55, 0.12, 1.0), "game_scale": 1.8, "what": "3 células de plasma da pistola num pente"},
    "ShellShotgun": {"core": (1.0, 0.35, 0.04), "game_scale": 1.7, "what": "3 cartuchos de plasma da escopeta amarrados"},
    "CellRifle": {"core": (0.1, 0.85, 1.0), "game_scale": 1.7, "what": "célula longa sextavada do rifle, em pé nas aletas"},
    "HealthGel": {"core": (1.0, 0.12, 0.2), "game_scale": 1.8, "what": "injetor de gel de cura (vida na hora)"},
    "Bandage": {"core": (1.0, 0.25, 0.25), "game_scale": 1.6, "what": "rolo de bandagem deitado com cruz vermelha"},
    "Medkit": {"core": (1.0, 0.2, 0.15), "game_scale": 1.5, "what": "maleta de kit médico em pé com alça"},
    "FuryCrystal": {"core": (0.75, 0.2, 1.0), "game_scale": 1.6, "what": "cristais de fúria saindo de uma pedra"},
    "Nitro": {"core": (0.1, 0.55, 1.0), "game_scale": 1.6, "what": "galão de nitro com faixas brilhando (carro)"},
    "Repair": {"core": (0.2, 1.0, 0.35), "game_scale": 1.5, "what": "caixa de ferramentas com faixa verde (carro)"},
}


def parse_args(argv):
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, help="pasta de saída (ex.: assets/work/props/pickups)")
    p.add_argument("--no-preview", action="store_true", help="não renderiza as prévias")
    p.add_argument("--only", default="", help="nomes separados por vírgula (padrão: todos)")
    return p.parse_args(argv)


# ------------------------------------------------------------------ editor (bpy)

def _bpy():
    import bpy  # noqa: PLC0415
    import bmesh  # noqa: PLC0415
    from mathutils import Matrix, Vector  # noqa: PLC0415
    return bpy, bmesh, Matrix, Vector


class Builder:
    """Monta uma malha num bmesh só; cada peça escolhe cor da paleta (Body) ou núcleo (Core)."""

    BODY, CORE = 0, 1

    def __init__(self):
        bpy, bmesh, Matrix, Vector = _bpy()
        self.bpy, self.bmesh, self.Matrix, self.Vector = bpy, bmesh, Matrix, Vector
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def _tag(self, before, swatch, core, smooth):
        new = [f for f in self.bm.faces if f not in before]
        u, v = swatch_uv(swatch)
        for f in new:
            f.material_index = self.CORE if core else self.BODY
            f.smooth = smooth
            for loop in f.loops:
                loop[self.uv].uv = (u, v)
        return new

    def cyl(self, r, h, z0=0.0, segs=12, x=0.0, y=0.0, sw=0, core=False, r2=None, rot=None, smooth=True):
        before = set(self.bm.faces)
        m = self.Matrix.Translation((x, y, z0 + h / 2.0))
        if rot is not None:
            m = self.Matrix.Translation((x, y, z0)) @ rot @ self.Matrix.Translation((0, 0, h / 2.0))
        self.bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=True, segments=segs, radius1=r,
                                   radius2=r if r2 is None else r2, depth=h, matrix=m)
        faces = self._tag(before, sw, core, smooth and segs > 6)
        # tampas sempre retas (sombreamento duro na borda)
        axis = (rot.to_3x3() if rot is not None else self.Matrix.Identity(3)) @ self.Vector((0.0, 0.0, 1.0))
        for f in faces:
            f.normal_update()
            if abs(f.normal.dot(axis)) > 0.95:
                f.smooth = False
        return faces

    def box(self, sx, sy, sz, x=0.0, y=0.0, z0=0.0, sw=0, core=False, rotz=0.0, bevel=0.0):
        before = set(self.bm.faces)
        m = (self.Matrix.Translation((x, y, z0 + sz / 2.0)) @ self.Matrix.Rotation(rotz, 4, "Z")
             @ self.Matrix.Diagonal((sx, sy, sz, 1.0)))
        res = self.bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        if bevel > 0.0:
            verts = set(res["verts"])
            edges = [e for e in self.bm.edges if e.verts[0] in verts and e.verts[1] in verts]
            self.bmesh.ops.bevel(self.bm, geom=edges, offset=bevel, segments=1, affect="EDGES", profile=0.5,
                                 clamp_overlap=True)
        return self._tag(before, sw, core, False)

    def crystal(self, r, h, x, y, z0, tilt_x=0.0, tilt_y=0.0, spin=0.0, sw=0, core=True, top=0.32):
        """Prisma sextavado com ponta (sem n-gons: fundo em leque de triângulos)."""
        before = set(self.bm.faces)
        m = (self.Matrix.Translation((x, y, z0)) @ self.Matrix.Rotation(tilt_y, 4, "Y")
             @ self.Matrix.Rotation(tilt_x, 4, "X") @ self.Matrix.Rotation(spin, 4, "Z"))
        body_h = h * (1.0 - top)
        bot, mid = [], []
        for i in range(6):
            a = i * math.pi / 3.0
            bot.append(self.bm.verts.new(m @ self.Vector((r * 0.85 * math.cos(a), r * 0.85 * math.sin(a), 0.0))))
            mid.append(self.bm.verts.new(m @ self.Vector((r * math.cos(a), r * math.sin(a), body_h))))
        apex = self.bm.verts.new(m @ self.Vector((0.0, 0.0, h)))
        base_c = self.bm.verts.new(m @ self.Vector((0.0, 0.0, 0.0)))
        for i in range(6):
            j = (i + 1) % 6
            self.bm.faces.new((bot[i], bot[j], mid[j], mid[i]))
            self.bm.faces.new((mid[i], mid[j], apex))
            self.bm.faces.new((bot[j], bot[i], base_c))
        return self._tag(before, sw, core, False)

    def rock(self, radius, squash, z, sw, seed=7):
        before = set(self.bm.faces)
        res = self.bmesh.ops.create_icosphere(self.bm, subdivisions=1, radius=radius,
                                              matrix=self.Matrix.Translation((0, 0, z)))
        rnd = random.Random(seed)
        for v in res["verts"]:
            k = 1.0 + rnd.uniform(-0.18, 0.18)
            v.co.x *= k
            v.co.y *= k
            v.co.z = z + (v.co.z - z) * squash
            v.co.z = max(v.co.z, 0.0)
        return self._tag(before, sw, False, False)

    def quad(self, size, sw=0):
        before = set(self.bm.faces)
        h = size / 2.0
        vs = [self.bm.verts.new(c) for c in ((-h, -h, 0.0), (h, -h, 0.0), (h, h, 0.0), (-h, h, 0.0))]
        f = self.bm.faces.new(vs)
        f.material_index = 0
        for loop, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[self.uv].uv = uv
        return [f for f in self.bm.faces if f not in before]

    def finish(self, name):
        bpy = self.bpy
        self.bmesh.ops.recalc_face_normals(self.bm, faces=list(self.bm.faces))
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


# ------------------------------------------------------------------ peças

def build_cell_pistol(b):
    # pente: base e trilhos laterais (metal escuro); 3 células em pé
    b.box(0.096, 0.036, 0.012, z0=0.0, sw=0, bevel=0.003)
    for side in (-1, 1):
        b.box(0.096, 0.004, 0.020, y=side * 0.0175, z0=0.010, sw=1, bevel=0.001)
    for x in (-0.031, 0.0, 0.031):
        b.cyl(0.0145, 0.012, z0=0.010, x=x, sw=2)            # tampa de baixo
        b.cyl(0.0100, 0.046, z0=0.022, x=x, core=True)       # núcleo de plasma
        b.cyl(0.0118, 0.003, z0=0.044, x=x, sw=2)            # aro fino de metal
        b.cyl(0.0145, 0.010, z0=0.068, x=x, sw=3)            # tampa de cima violeta
        b.cyl(0.0070, 0.006, z0=0.078, x=x, sw=2)            # contato


def build_shell_shotgun(b):
    pos = [(0.020 * math.cos(a), 0.020 * math.sin(a)) for a in (0.0, 2.0944, 4.1888)]
    for x, y in pos:
        b.cyl(0.0180, 0.003, z0=0.000, x=x, y=y, sw=5)                      # aro do culote
        b.cyl(0.0168, 0.011, z0=0.003, x=x, y=y, sw=5)                      # culote de latão
        b.cyl(0.0165, 0.040, z0=0.014, x=x, y=y, sw=4)                      # corpo laranja
        b.cyl(0.0172, 0.005, z0=0.040, x=x, y=y, core=True)                 # faixa brilhante
        b.cyl(0.0165, 0.008, z0=0.054, x=x, y=y, sw=4, r2=0.0110)           # ombro
        b.cyl(0.0110, 0.006, z0=0.062, x=x, y=y, core=True, r2=0.0045)      # ponta de plasma


def build_cell_rifle(b):
    b.cyl(0.020, 0.012, z0=0.0, segs=6, sw=0)                               # base sextavada
    for i in range(3):
        a = i * 2.0944
        b.box(0.030, 0.004, 0.030, x=0.020 * math.cos(a), y=0.020 * math.sin(a), z0=0.0, sw=1, rotz=a)  # aletas
    b.cyl(0.016, 0.010, z0=0.012, segs=6, sw=6)                             # colar de baixo
    b.cyl(0.011, 0.072, z0=0.022, segs=6, core=True)                        # núcleo
    for i in range(3):
        a = math.radians(30 + i * 120)
        b.box(0.003, 0.003, 0.072, x=0.0135 * math.cos(a), y=0.0135 * math.sin(a), z0=0.022, sw=2, rotz=a)  # grades
    b.cyl(0.016, 0.010, z0=0.094, segs=6, sw=6)                             # colar de cima
    b.cyl(0.012, 0.016, z0=0.104, segs=6, sw=2, r2=0.004)                   # ponta


def build_health_gel(b):
    b.cyl(0.016, 0.014, z0=0.000, sw=8)                                     # tampa de baixo
    b.cyl(0.017, 0.004, z0=0.014, sw=9)                                     # aro vermelho
    b.cyl(0.012, 0.050, z0=0.018, core=True)                                # gel
    for i in range(3):
        a = math.radians(i * 120)
        b.box(0.003, 0.003, 0.050, x=0.0128 * math.cos(a), y=0.0128 * math.sin(a), z0=0.018, sw=8, rotz=a)
    b.cyl(0.016, 0.014, z0=0.068, sw=8)                                     # tampa de cima
    b.cyl(0.017, 0.004, z0=0.068, sw=9)
    b.cyl(0.008, 0.008, z0=0.082, sw=9)                                     # botão


def build_bandage(b):
    _, _, Matrix, _ = _bpy()
    rot = Matrix.Rotation(math.radians(90), 4, "Y")
    b.cyl(0.035, 0.050, z0=0.035, x=-0.025, segs=16, sw=7, rot=rot)         # rolo (eixo X)
    b.cyl(0.013, 0.052, z0=0.035, x=-0.026, segs=10, sw=2, rot=rot)         # tubo do meio
    b.box(0.048, 0.060, 0.002, y=-0.038, z0=0.0, sw=7)                      # ponta solta no chão
    for side in (-1, 1):
        xx = side * 0.0258
        b.box(0.002, 0.024, 0.008, x=xx, z0=0.031, core=True)               # cruz
        b.box(0.002, 0.008, 0.024, x=xx, z0=0.023, core=True)


def build_medkit(b):
    b.box(0.160, 0.060, 0.110, z0=0.0, sw=8, bevel=0.008)                   # maleta
    b.box(0.163, 0.063, 0.006, z0=0.072, sw=1)                              # fresta da tampa
    for x in (-0.035, 0.035):
        b.box(0.010, 0.014, 0.018, x=x, z0=0.108, sw=13)                    # hastes da alça
        b.box(0.012, 0.064, 0.012, x=x * 1.9, z0=0.062, sw=14)              # travas amarelas
    b.box(0.082, 0.014, 0.010, z0=0.126, sw=13, bevel=0.003)                # alça
    for side in (-1, 1):
        y = side * 0.0312
        b.box(0.050, 0.003, 0.016, y=y, z0=0.034, core=True)                # cruz
        b.box(0.016, 0.003, 0.050, y=y, z0=0.017, core=True)


def build_fury(b):
    b.rock(0.040, 0.45, 0.012, sw=10)
    spec = [  # r, h, x, y, tilt_x, tilt_y, spin
        (0.014, 0.115, 0.000, 0.000, 0.0, 0.0, 0.2),
        (0.010, 0.070, 0.018, 0.006, -0.15, 0.45, 0.9),
        (0.009, 0.060, -0.016, 0.012, -0.40, -0.35, 0.4),
        (0.008, 0.052, -0.004, -0.019, 0.50, 0.05, 1.3),
        (0.006, 0.036, 0.012, -0.014, 0.45, 0.50, 0.1),
    ]
    for r, h, x, y, tx, ty, sp in spec:
        b.crystal(r, h, x, y, 0.004, tilt_x=tx, tilt_y=ty, spin=sp)


def build_nitro(b):
    b.cyl(0.052, 0.008, z0=0.000, segs=16, sw=0)
    b.cyl(0.050, 0.160, z0=0.008, segs=16, sw=11)
    for z in (0.045, 0.125):
        b.cyl(0.0515, 0.012, z0=z, segs=16, core=True)
    b.box(0.040, 0.004, 0.034, y=-0.050, z0=0.070, sw=14)                   # placa de aviso
    b.cyl(0.050, 0.025, z0=0.168, segs=16, sw=1, r2=0.025)                  # ombro
    b.cyl(0.014, 0.020, z0=0.193, sw=2)                                     # válvula
    b.box(0.050, 0.008, 0.006, z0=0.213, sw=13, bevel=0.002)                # alavanca


def build_repair(b):
    b.box(0.200, 0.090, 0.080, z0=0.0, sw=12, bevel=0.006)                  # caixa verde
    b.box(0.206, 0.096, 0.008, z0=0.048, core=True)                         # faixa que brilha
    b.box(0.204, 0.094, 0.012, z0=0.080, sw=1, bevel=0.003)                 # tampa
    for x in (-0.050, 0.050):
        b.box(0.010, 0.014, 0.020, x=x, z0=0.090, sw=13)
    b.box(0.112, 0.016, 0.010, z0=0.108, sw=13, bevel=0.003)                # alça
    for x in (-0.07, 0.07):
        b.box(0.016, 0.098, 0.014, x=x, z0=0.066, sw=14)                    # travas


BUILDERS = {
    "CellPistol": build_cell_pistol, "ShellShotgun": build_shell_shotgun, "CellRifle": build_cell_rifle,
    "HealthGel": build_health_gel, "Bandage": build_bandage, "Medkit": build_medkit,
    "FuryCrystal": build_fury, "Nitro": build_nitro, "Repair": build_repair,
}


# ------------------------------------------------------------------ materiais, export e prévia

def reset_scene():
    bpy = _bpy()[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_image(name, path=None, rgb=None):
    bpy = _bpy()[0]
    if path:
        img = bpy.data.images.load(path)
        img.name = name
        return img
    img = bpy.data.images.new(name, 4, 4)
    img.pixels = [rgb[0], rgb[1], rgb[2], 1.0] * 16
    return img


def make_material(name, image, emission=None, strength=0.0, rough=0.62):
    bpy = _bpy()[0]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.interpolation = "Closest"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.nodes.active = tex
    bsdf.inputs["Roughness"].default_value = rough
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
    return m


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def export(ob, out_dir, name):
    bpy = _bpy()[0]
    for o in bpy.context.scene.objects:
        o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob
    fbx = os.path.join(out_dir, f"SM_Pickup_{name}.fbx")
    glb = os.path.join(out_dir, f"SM_Pickup_{name}.glb")
    bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
                             mesh_smooth_type="FACE", add_leaf_bones=False, colors_type="NONE", path_mode="STRIP")
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True)
    return fbx, glb


def render_preview(ob, path, core_rgb):
    bpy = _bpy()[0]
    from mathutils import Vector  # noqa: PLC0415
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "TEXTURE"
    sc.display.shading.show_cavity = True
    sc.display.shading.cavity_type = "WORLD"
    sc.display.shading.show_object_outline = True
    sc.display.shading.object_outline_color = (0.02, 0.02, 0.04)
    sc.display.shading.background_type = "VIEWPORT"
    sc.display.shading.background_color = (0.035, 0.03, 0.06)
    sc.render.resolution_x = sc.render.resolution_y = 512
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    world = bpy.data.worlds.new("W")
    world.color = (0.035, 0.03, 0.06)
    sc.world = world
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    center = sum(pts, Vector()) / 8.0
    size = max((p - center).length for p in pts)
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 60
    cam = bpy.data.objects.new("Cam", cam_data)
    sc.collection.objects.link(cam)
    direction = Vector((0.75, -1.0, 0.62)).normalized()
    cam.location = center + direction * size * 4.1
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.clip_start = 0.001
    sc.camera = cam
    # anel de chão (só na prévia) para dar a ideia do brilho embaixo
    ring = bpy.data.meshes.new("PrevRing")
    rv, rf = [], []
    n = 48
    for i in range(n):
        a = 2.0 * math.pi * i / n
        for rr in (size * 0.95, size * 1.05):
            rv.append((center.x + rr * math.cos(a), center.y + rr * math.sin(a), 0.0005))
    for i in range(n):
        j = (i + 1) % n
        rf.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    ring.from_pydata(rv, [], rf)
    ring.uv_layers.new(name="UVMap")
    ro = bpy.data.objects.new("PrevRing", ring)
    sc.collection.objects.link(ro)
    rm = make_material("PrevRingMat", make_image("PrevRingImg", rgb=core_rgb))
    ro.data.materials.append(rm)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def build_one(name, out_dir, palette_png, preview):
    bpy = _bpy()[0]
    reset_scene()
    b = Builder()
    BUILDERS[name](b)
    ob = b.finish(f"SM_Pickup_{name}")
    core = ITEMS[name]["core"]
    pal = make_image("T_Pickup_Palette", path=palette_png)
    core_img = make_image(f"T_Core_{name}", rgb=tuple(min(1.0, c * 1.25 + 0.15) for c in core))
    ob.data.materials.append(make_material("Body", pal))
    ob.data.materials.append(make_material("Core", core_img, emission=core, strength=4.0, rough=0.25))
    fbx, glb = export(ob, out_dir, name)
    dims = [round(d, 4) for d in ob.dimensions]
    info = {"fbx": os.path.basename(fbx), "glb": os.path.basename(glb), "dims_m": dims, "tris": tri_count(ob),
            "core_linear": core, "game_scale": ITEMS[name]["game_scale"], "what": ITEMS[name]["what"],
            "min_z": round(min((ob.matrix_world @ v.co).z for v in ob.data.vertices), 5)}
    if preview:
        p = os.path.join(out_dir, f"SM_Pickup_{name}_preview.png")
        render_preview(ob, p, core)
        info["preview"] = os.path.basename(p)
    return info


def build_ring(out_dir, ring_png):
    reset_scene()
    b = Builder()
    b.quad(1.0)
    ob = b.finish("SM_Pickup_Ring")
    ob.data.materials.append(make_material("Ring", make_image("T_Pickup_RingGlow", path=ring_png), rough=1.0))
    fbx, glb = export(ob, out_dir, "Ring")
    return {"fbx": os.path.basename(fbx), "glb": os.path.basename(glb), "dims_m": [1.0, 1.0, 0.0], "tris": 2}


def write_textures(out_dir):
    from PIL import Image  # noqa: PLC0415
    rows = palette_pixels()
    size = len(rows)
    img = Image.new("RGB", (size, size))
    img.putdata([px for row in rows for px in row])
    pal = os.path.join(out_dir, "T_Pickup_Palette.png")
    img.save(pal)
    n = 256
    ring = Image.new("L", (n, n))
    ring.putdata([int(round(255 * ring_value((x + 0.5) / n, (y + 0.5) / n))) for y in range(n) for x in range(n)])
    rp = os.path.join(out_dir, "T_Pickup_RingGlow.png")
    ring.save(rp)
    return pal, rp


def contact_sheet(out_dir, names):
    from PIL import Image  # noqa: PLC0415
    tiles = [Image.open(os.path.join(out_dir, f"SM_Pickup_{n}_preview.png")).convert("RGB").resize((256, 256))
             for n in names if os.path.exists(os.path.join(out_dir, f"SM_Pickup_{n}_preview.png"))]
    if not tiles:
        return None
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 256, rows * 256), (9, 8, 15))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * 256, (i // cols) * 256))
    p = os.path.join(out_dir, "pickups_contact_sheet.png")
    sheet.save(p)
    return p


def main(argv):
    args = parse_args(argv)
    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    names = [n for n in BUILDERS if not args.only or n in args.only.split(",")]
    pal, ring_png = write_textures(out_dir)
    report = {"items": {}, "palette": os.path.basename(pal), "ring_texture": os.path.basename(ring_png)}
    for n in names:
        report["items"][n] = build_one(n, out_dir, pal, not args.no_preview)
        print(f"[make_pickups] {n}: {report['items'][n]['tris']} tri, {report['items'][n]['dims_m']} m")
    report["items"]["Ring"] = build_ring(out_dir, ring_png)
    if not args.no_preview:
        report["contact_sheet"] = os.path.basename(contact_sheet(out_dir, names) or "")
    with open(os.path.join(out_dir, "pickups.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print(f"[make_pickups] pronto: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
