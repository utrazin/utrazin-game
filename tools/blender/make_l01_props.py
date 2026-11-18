"""L01 cartoon low-poly props generator (Blender 5.2 / bpy).
Run: python make_l01_props.py -- [out_dir]
Builds 18 static meshes with vertex colors ("Col"), one shared material,
renders a preview, exports L01_Props.fbx and props_info.json.
"""
import bpy, bmesh, math, random, json, sys, os
from mathutils import Matrix, Vector, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "/mnt/user-data/outputs/l01"
os.makedirs(OUT, exist_ok=True)
MAT_NAME = "M_L01_VertexColor"

# ---------------- palette (sRGB 0-1) ----------------
def hx(h):
    h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
TRUNK = hx('6b4528'); TRUNK_D = hx('4e321d')
PINE1 = hx('2f6b3a'); PINE2 = hx('3d8746'); PINE3 = hx('4f9d4f')
LEAF1 = hx('5e9e3a'); LEAF2 = hx('7bb247'); LEAF3 = hx('4a8a33')
DEADW = hx('6e6258')
BUSH1 = hx('4f8a35'); BUSH2 = hx('69a33f'); BUSH3 = hx('3e7a2e')
ROCK = hx('8a8a86'); ROCK_W = hx('9a948a')
CONC = hx('a4a29b'); CONC_D = hx('6a6862'); CONC_B = hx('8e8b84')
WOOD = hx('9a6a3c'); WOOD_L = hx('b58450'); WOOD_D = hx('6d4726')
KHAKI = hx('b8a873'); KHAKI_D = hx('9c8d5c')
RUST = hx('a5552a'); RUST_D = hx('7a3a1c'); RUST_L = hx('c06a34')
GLASS = hx('2a2f36'); TIRE = hx('2b2b2b'); METAL = hx('6f7275')
BARREL = hx('b03a2a'); METAL_D = hx('3a3d42'); BAR = hx('44484e')
SIGN_R = hx('c8322a'); STONE = hx('9b968c'); STONE_D = hx('767167')


def clamp01(x):
    return max(0.0, min(1.0, x))


class Builder:
    def __init__(self, seed):
        self.bm = bmesh.new()
        self.cl = self.bm.loops.layers.color.new("Col")  # BYTE_COLOR, CORNER
        self.rng = random.Random(seed)

    # -- color
    def paint(self, faces, col, var=0.0):
        for f in faces:
            k = 1.0 + (self.rng.random() * 2 - 1) * var if var else 1.0
            c = (clamp01(col[0] * k), clamp01(col[1] * k), clamp01(col[2] * k), 1.0)
            for l in f.loops:
                l[self.cl] = c

    def _faces(self, verts):
        s = set()
        for v in verts:
            s.update(v.link_faces)
        return list(s)

    def _place(self, verts, M, col, var):
        bmesh.ops.transform(self.bm, matrix=M, verts=verts)
        faces = self._faces(verts)
        self.paint(faces, col, var)
        return faces

    # -- primitives
    def box(self, center, size, col, rot=(0, 0, 0), var=0.04, taper=None):
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        if taper:
            for v in r['verts']:
                if v.co.z > 0:
                    v.co.x *= taper[0]; v.co.y *= taper[1]
        M = (Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4()
             @ Matrix.Diagonal(Vector((size[0], size[1], size[2], 1))))
        return self._place(r['verts'], M, col, var)

    def box_between(self, p0, p1, w, t, col, var=0.04, roll=0.0):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        q = Vector((0, 0, 1)).rotation_difference(d)
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        M = (Matrix.Translation(p0) @ q.to_matrix().to_4x4() @ Matrix.Rotation(roll, 4, 'Z')
             @ Matrix.Translation((0, 0, d.length / 2)) @ Matrix.Diagonal(Vector((w, t, d.length, 1))))
        return self._place(r['verts'], M, col, var)

    def cyl(self, base, r1, h, segs, col, r2=None, rot=(0, 0, 0), var=0.04, edit=None, scale=(1, 1, 1)):
        r2 = r1 if r2 is None else r2
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segs,
                                  radius1=r1, radius2=r2, depth=h)
        verts = r['verts']
        if r2 == 0:  # merge apex
            top = [v for v in verts if v.co.z > 0]
            if len(top) > 1:
                bmesh.ops.pointmerge(self.bm, verts=top, merge_co=Vector((0, 0, h / 2)))
                verts = [v for v in verts if v.is_valid]
        if edit:
            edit(verts, h)
        M = (Matrix.Translation(base) @ Euler(rot).to_matrix().to_4x4()
             @ Matrix.Diagonal(Vector((scale[0], scale[1], scale[2], 1)))
             @ Matrix.Translation((0, 0, h / 2)))
        return self._place(verts, M, col, var)

    def cyl_between(self, p0, p1, r1, segs, col, r2=None, var=0.04):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        r2 = r1 if r2 is None else r2
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segs,
                                  radius1=r1, radius2=r2, depth=d.length)
        q = Vector((0, 0, 1)).rotation_difference(d)
        M = Matrix.Translation(p0) @ q.to_matrix().to_4x4() @ Matrix.Translation((0, 0, d.length / 2))
        return self._place(r['verts'], M, col, var)

    def ico(self, center, scale, subd, col, jitter=0.0, var=0.06, zclamp=None, rot=(0, 0, 0)):
        r = bmesh.ops.create_icosphere(self.bm, subdivisions=subd, radius=1.0)
        for v in r['verts']:
            v.co *= 1.0 + (self.rng.random() * 2 - 1) * jitter
        M = (Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4()
             @ Matrix.Diagonal(Vector((scale[0], scale[1], scale[2], 1))))
        faces = self._place(r['verts'], M, col, var)
        if zclamp is not None:
            for v in r['verts']:
                if v.co.z < zclamp:
                    v.co.z = zclamp
        return faces

    def paint_where(self, faces, pred, col, var=0.0):
        sel = []
        for f in faces:
            f.normal_update()
            if pred(f.normal):
                sel.append(f)
        self.paint(sel, col, var)

    # -- finish
    def finish(self, name, mat, center_xy=True):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        bm.verts.ensure_lookup_table()
        xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]; zs = [v.co.z for v in bm.verts]
        off = Vector(((min(xs) + max(xs)) / 2 if center_xy else 0,
                      (min(ys) + max(ys)) / 2 if center_xy else 0, min(zs)))
        for v in bm.verts:
            v.co -= off
        # drop degenerate faces created by clamping
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        for f in bm.faces:
            f.smooth = False
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(mat)
        ca = me.color_attributes.get("Col")
        assert ca is not None and ca.data_type == 'BYTE_COLOR', (name, ca and ca.data_type)
        me.color_attributes.active_color = ca
        me.color_attributes.render_color_index = me.color_attributes.find("Col")
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


# =================== PROPS ===================
def tree_pine(b):
    b.cyl((0, 0, 0), 0.30, 2.4, 8, TRUNK, r2=0.18)
    levels = [(1.5, 2.5, 2.9, PINE1), (3.1, 2.0, 2.6, PINE2), (4.5, 1.5, 2.3, PINE1),
              (5.8, 1.0, 2.2, PINE3)]
    for i, (z, rad, h, col) in enumerate(levels):
        def star(verts, hh, i=i):
            base = sorted([v for v in verts if v.co.z < 0], key=lambda v: math.atan2(v.co.y, v.co.x))
            for j, v in enumerate(base):
                k = 1.0 if j % 2 == 0 else 0.78
                v.co.x *= k; v.co.y *= k
                v.co.z += (0.18 if j % 2 else -0.05)
        b.cyl((0, 0, z), rad, h, 14, col, r2=0, rot=(0, 0, i * 0.4), edit=star, var=0.07)


def tree_round(b):
    b.cyl((0, 0, 0), 0.28, 3.4, 8, TRUNK, r2=0.18)
    b.cyl_between((0, 0, 2.2), (0.75, 0.3, 3.4), 0.1, 6, TRUNK, r2=0.06)
    b.ico((0, 0, 4.3), (1.7, 1.6, 1.55), 3, LEAF2, jitter=0.07, var=0.07)
    b.ico((0.95, 0.45, 3.65), (0.95, 0.9, 0.85), 2, LEAF1, jitter=0.08, var=0.07)
    b.ico((-0.8, -0.55, 3.75), (0.9, 0.9, 0.8), 2, LEAF3, jitter=0.08, var=0.07)


def tree_dead(b):
    pts = [Vector((0, 0, 0)), Vector((0.1, 0.05, 1.6)), Vector((-0.05, 0.12, 3.0)), Vector((0.12, 0.0, 4.4))]
    rads = [0.32, 0.22, 0.15, 0.08]
    for i in range(3):
        b.cyl_between(pts[i] - Vector((0, 0, 0.05 if i else 0)), pts[i + 1], rads[i], 7, DEADW, r2=rads[i + 1], var=0.05)
    b.cyl_between(pts[3], pts[3] + Vector((0.15, 0.05, 0.55)), 0.08, 6, DEADW, r2=0.02)
    branches = [((0.08, 0.05, 1.9), (1.4, 0.3, 3.0), 0.11, (1.4, 0.3, 3.0), (1.75, -0.2, 3.6)),
                ((-0.02, 0.1, 2.5), (-1.3, 0.5, 3.4), 0.1, (-1.3, 0.5, 3.4), (-1.5, 0.9, 4.1)),
                ((0.0, 0.1, 3.3), (0.3, -1.2, 4.3), 0.08, (0.3, -1.2, 4.3), (0.6, -1.5, 4.85)),
                ((0.05, 0.08, 1.2), (-0.7, -0.9, 1.9), 0.09, None, None)]
    for p0, p1, r, q0, q1 in branches:
        b.cyl_between(p0, p1, r, 6, DEADW, r2=r * 0.55, var=0.06)
        if q0:
            b.cyl_between(q0, q1, r * 0.55, 5, DEADW, r2=0.02, var=0.06)
    # root flare
    for a in (0.3, 2.4, 4.4):
        b.cyl_between((0, 0, 0.35), (math.cos(a) * 0.7, math.sin(a) * 0.7, 0.0), 0.13, 5, TRUNK_D, r2=0.05)


def bush(b):
    b.ico((-0.45, -0.1, 0.45), (0.8, 0.75, 0.62), 2, BUSH1, jitter=0.1, var=0.08, zclamp=0.0)
    b.ico((0.5, 0.15, 0.42), (0.75, 0.7, 0.58), 2, BUSH2, jitter=0.1, var=0.08, zclamp=0.0)
    b.ico((0.0, 0.1, 0.72), (0.65, 0.6, 0.5), 2, BUSH3, jitter=0.1, var=0.08, zclamp=0.0)


def rock(b, size, extra=True):
    sx, sy, sz = size
    b.ico((0, 0, sz * 0.35), (sx * 0.5, sy * 0.5, sz * 0.62), 2, ROCK, jitter=0.16, var=0.12,
          zclamp=0.0, rot=(0, 0, b.rng.random() * 3))
    if extra:
        b.ico((sx * 0.22, sy * 0.12, sz * 0.25), (sx * 0.3, sy * 0.32, sz * 0.4), 2, ROCK_W,
              jitter=0.18, var=0.12, zclamp=0.0, rot=(0, 0, 1.0))


def wall_run(b, axis, fixed, a0, a1, thick, openings, hfun, piece=0.6):
    """axis 'x' or 'y'. openings: list of (c, width, z0, z1)."""
    br = {a0, a1}
    for c, w, z0, z1 in openings:
        br.add(c - w / 2); br.add(c + w / 2)
    br = sorted(br)
    pieces = []
    for s, e in zip(br[:-1], br[1:]):
        n = max(1, round((e - s) / piece))
        for k in range(n):
            pieces.append((s + (e - s) * k / n, s + (e - s) * (k + 1) / n))
    for s, e in pieces:
        m = (s + e) / 2
        top = hfun(m)
        spans = [(0.0, top)]
        for c, w, z0, z1 in openings:
            if c - w / 2 - 1e-6 <= m <= c + w / 2 + 1e-6:
                spans = []
                if z0 > 0:
                    spans.append((0.0, z0))
                if top > z1 + 0.15:
                    spans.append((z1, top))
        for zb, zt in spans:
            ln = e - s
            if axis == 'x':
                cen, size = (m, fixed, (zb + zt) / 2), (ln, thick, zt - zb)
            else:
                cen, size = (fixed, m, (zb + zt) / 2), (thick, ln, zt - zb)
            f = b.box(cen, size, CONC, var=0.05)
            if zt == top:
                b.paint_where(f, lambda n: n.z > 0.9, CONC_D, 0.06)


def ruin_house(b):
    rng = b.rng
    H = 3.2
    def hf(seed, lo=2.0):
        r = random.Random(seed)
        def f(m):
            # tall near corners, jagged elsewhere
            return min(H, max(lo, H - r.random() * 1.2 + (0.0 if abs(m) < 3.4 else 1.0)))
        return f
    t = 0.3
    # front (+X) door, back (-X)
    wall_run(b, 'y', 4.5 - t / 2, -3.5, 3.5, t, [(0.0, 1.6, 0.0, 2.2)], hf(1))
    wall_run(b, 'y', -4.5 + t / 2, -3.5, 3.5, t, [], hf(2, 1.6))
    # sides with windows
    wall_run(b, 'x', 3.5 - t / 2, -4.2, 4.2, t, [(-1.5, 1.2, 1.0, 2.1)], hf(3))
    wall_run(b, 'x', -3.5 + t / 2, -4.2, 4.2, t, [(1.8, 1.2, 1.0, 2.1)], hf(4))
    # rubble piles inside, hugging walls (keeps 9x7 footprint, interior walkable)
    for (x, y) in [(-3.9, 2.8), (-3.8, -2.6), (2.5, 2.9), (0.5, -2.9)]:
        s = 0.25 + rng.random() * 0.2
        b.ico((x, y, s * 0.4), (s, s * 0.9, s * 0.7), 1, CONC_B, jitter=0.15, var=0.08, zclamp=0.0)


def ruin_wall(b):
    r = random.Random(7)
    def hf(m):
        base = 3.0 - (m + 3.0) / 6.0 * 1.4  # 3.0 -> 1.6
        return max(1.5, min(3.0, base + (r.random() - 0.5) * 0.6))
    wall_run(b, 'x', 0.0, -3.0, 3.0, 0.3, [], hf, piece=0.5)
    for (x, z) in [(-2.2, 0.8), (-0.6, 1.5), (1.1, 0.5), (0.4, 0.9)]:
        b.box((x, -0.16, z), (0.4, 0.04, 0.2), CONC_B, var=0.05)
    for x in (-1.5, 2.3):
        b.ico((x, -0.3, 0.12), (0.26, 0.16, 0.2), 1, CONC_B, jitter=0.15, zclamp=0.0)


def barricade(b):
    r = b.rng
    # sandbags (front, -Y)
    for row, (n, z, y) in enumerate([(7, 0.11, -0.2), (6, 0.31, -0.2), (3, 0.5, -0.2)]):
        L = 0.56
        total = n * L
        for i in range(n):
            x = -total / 2 + L * (i + 0.5) + (0 if row != 2 else 0)
            if row == 2:
                x = -1.2 + i * 0.58
            b.box((x, y + (r.random() - 0.5) * 0.04, z), (0.54, 0.36, 0.21),
                  KHAKI if (i + row) % 2 else KHAKI_D, rot=(0, 0, (r.random() - 0.5) * 0.12),
                  taper=(0.88, 0.85), var=0.05)
    # stakes and planks behind
    for x in (-1.85, -0.6, 0.6, 1.85):
        b.box((x, 0.12, 0.6), (0.11, 0.11, 1.2), WOOD_D, var=0.05)
    for z, tilt, col in [(0.55, 0.03, WOOD), (0.82, -0.04, WOOD_L), (1.08, 0.02, WOOD)]:
        b.box((0, 0.21, z), (3.96, 0.05, 0.2), col, rot=(0, tilt, 0), var=0.05)
    b.box((0.5, 0.25, 0.75), (2.6, 0.04, 0.18), WOOD_D, rot=(0, -0.32, 0), var=0.05)


def car_wreck(b):
    # flat tires (clamped)
    for x in (-1.45, 1.4):
        for y in (-0.76, 0.76):
            f = b.cyl((x, y - 0.11, 0.24), 0.32, 0.22, 10, TIRE, rot=(-math.pi / 2, 0, 0), var=0.03)
            for fa in f:
                for v in fa.verts:
                    if v.co.z < 0.02:
                        v.co.z = 0.02 + (v.co.z - 0.02) * 0.0
    # body
    body = b.box((0, 0, 0.62), (4.25, 1.76, 0.62), RUST, var=0.08)
    b.box((0.0, 0, 0.27), (3.9, 1.6, 0.12), RUST_D, var=0.03)  # sill
    # cabin tapered
    cab = b.box((-0.25, 0, 1.17), (2.3, 1.62, 0.46), RUST, taper=(0.72, 0.84), var=0.05)
    b.paint_where(cab, lambda n: abs(n.z) < 0.9, GLASS, 0.05)
    b.paint_where(cab, lambda n: n.z > 0.9, RUST_L, 0.05)
    # hood dent + rust patches
    b.box((1.55, 0.2, 0.935), (0.8, 0.7, 0.03), RUST_D, rot=(0, 0.04, 0.1), var=0.05)
    b.box((-1.7, -0.3, 0.935), (0.6, 0.5, 0.03), RUST_L, var=0.05)
    # door lines
    for x in (-0.3, 0.6):
        for y in (-0.885, 0.885):
            b.box((x, y, 0.62), (0.04, 0.02, 0.5), RUST_D, var=0.0)
    # bumpers
    b.box((2.17, 0, 0.42), (0.16, 1.7, 0.2), METAL, var=0.04)
    b.box((-2.17, 0, 0.42), (0.16, 1.7, 0.2), METAL, rot=(0.08, 0, 0), var=0.04)
    # headlights (broken)
    for y in (-0.6, 0.6):
        b.box((2.13, y, 0.72), (0.04, 0.3, 0.14), hx('d9d2a0') if y > 0 else GLASS, var=0.0)
        b.box((-2.13, y, 0.72), (0.04, 0.3, 0.12), hx('8a2a20'), var=0.0)


def crate(b):
    b.box((0, 0, 0.5), (0.94, 0.94, 0.94), WOOD_L, var=0.05)
    for z in (0.06, 0.94):
        b.box((0, 0, z), (1.0, 1.0, 0.12), WOOD_D, var=0.04)


def barrel(b):
    f = b.cyl((0, 0, 0), 0.29, 0.9, 12, BARREL, var=0.05)
    b.paint_where(f, lambda n: n.z > 0.9, METAL_D, 0.0)
    for z in (0.28, 0.6):
        b.cyl((0, 0, z), 0.30, 0.05, 12, METAL_D, var=0.03)


def fence(b):
    r = b.rng
    for x in (-1.94, 0.0, 1.94):
        b.box((x, 0, 0.6), (0.12, 0.12, 1.2), WOOD_D, var=0.04)
    for z in (0.35, 0.85):
        b.box((0, 0.085, z), (4.0, 0.05, 0.1), WOOD, var=0.04)
    xs = [-1.7, -1.28, -0.86, -0.44, 0.44, 0.86, 1.28, 1.7]
    for i, x in enumerate(xs):
        h = 1.0 + r.random() * 0.13
        tilt = 0.12 if i == 3 else (r.random() - 0.5) * 0.04
        b.box((x, 0.135, h / 2 + 0.03), (0.15, 0.04, h), WOOD_L if i % 2 else WOOD,
              rot=(0, tilt, 0), taper=(0.45, 1.0), var=0.05)


def watchtower(b):
    L = 1.35; T = 0.25
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((sx * L, sy * L, 3.0), (T, T, 6.0), WOOD_D, var=0.04)
    # platform slab top exactly 5.0
    b.box((0, 0, 4.9), (3.0, 3.0, 0.2), WOOD_L, var=0.03)
    for y in (-0.75, 0.75):
        b.box((0, y, 4.72), (3.0, 0.18, 0.16), WOOD_D, var=0.03)
    # plank seams on top (flush strips, same height top=5.0 -> painted via thin boxes under? keep color stripes)
    # braces
    for lv0, lv1 in ((0.4, 2.55), (2.55, 4.64)):
        for s in (-1, 1):
            for a, c in ((-1, 1), (1, -1)):
                b.box_between((a * L, s * L, lv0), (c * L, s * L, lv1), 0.12, 0.08, WOOD, var=0.05)
                b.box_between((s * L, a * L, lv0), (s * L, c * L, lv1), 0.08, 0.12, WOOD, var=0.05)
    # railings (top of rail = 6.0), -X side has ladder gap
    for z, hgt in ((5.95, 0.1), (5.5, 0.08)):
        b.box((0, -L, z), (2.7, 0.08, hgt), WOOD, var=0.04)
        b.box((0, L, z), (2.7, 0.08, hgt), WOOD, var=0.04)
        b.box((L, 0, z), (0.08, 2.7, hgt), WOOD, var=0.04)
        b.box((-L, -0.85, z), (0.08, 1.0, hgt), WOOD, var=0.04)
        b.box((-L, 0.85, z), (0.08, 1.0, hgt), WOOD, var=0.04)
    # ladder on -X face
    lx = -1.62
    for y in (-0.3, 0.3):
        b.box((lx, y, 3.0), (0.08, 0.08, 6.0), WOOD_D, var=0.03)
    z = 0.35
    while z < 4.75:
        b.box((lx, 0, z), (0.06, 0.6, 0.06), WOOD_L, var=0.03)
        z += 0.34


def arena_wall(b):
    r = b.rng
    for i in range(4):
        x = -3.0 + i * 2.0
        b.box((x, 0, 0.575), (1.98, 0.54, 1.15), STONE if i % 2 else hx('a8a398'), var=0.05)
        b.box((x, 0, 1.225), (2.0, 0.6, 0.15), STONE_D, var=0.04)
    # chipped chunks
    b.box((1.9, -0.28, 0.35), (0.5, 0.05, 0.3), STONE_D, var=0.03)
    b.box((-2.6, 0.28, 0.75), (0.4, 0.05, 0.25), STONE_D, var=0.03)


def cage(b):
    S = 1.93; TOP = 3.0; FL = 0.15
    b.box((0, 0, FL / 2), (4.0, 4.0, FL), hx('5a5a58'), var=0.03)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((sx * S, sy * S, (FL + TOP) / 2), (0.14, 0.14, TOP - FL), METAL_D, var=0.03)
    # top / bottom / mid frames
    for z, h in ((TOP - 0.06, 0.12), (FL + 0.06, 0.12), (1.55, 0.06)):
        for s in (-1, 1):
            b.box((0, s * S, z), (3.86, 0.1, h), METAL_D, var=0.03)
            if not (s == 1 and z == 1.55):
                b.box((s * S, 0, z), (0.1, 3.86, h), METAL_D, var=0.03)
    # +X mid rail split around door
    for y in (-1.25, 1.25):
        b.box((S, y, 1.55), (0.1, 1.36, 0.06), METAL_D, var=0.03)
    # roof frame
    for c in (-0.97, 0.0, 0.97):
        b.box((0, c, TOP - 0.05), (3.86, 0.08, 0.1), METAL_D, var=0.03)
        b.box((c, 0, TOP - 0.05), (0.08, 3.86, 0.1), METAL_D, var=0.03)
    pos = [-1.75 + 0.25 * i for i in range(15)]
    z0, z1 = FL + 0.12, TOP - 0.12
    for p in pos:
        b.cyl_between((p, -S, z0), (p, -S, z1), 0.025, 6, BAR, var=0.0)
        b.cyl_between((p, S, z0), (p, S, z1), 0.025, 6, BAR, var=0.0)
        b.cyl_between((-S, p, z0), (-S, p, z1), 0.025, 6, BAR, var=0.0)
        if abs(abs(p) - 0.5) < 0.01:
            continue
        if abs(p) < 0.5:  # door bars + above header
            b.cyl_between((S, p, z0), (S, p, 2.2), 0.025, 6, BAR, var=0.0)
            b.cyl_between((S, p, 2.3), (S, p, z1), 0.025, 6, BAR, var=0.0)
        else:
            b.cyl_between((S, p, z0), (S, p, z1), 0.025, 6, BAR, var=0.0)
    # door frame on +X
    for y in (-0.55, 0.55):
        b.box((S, y, (FL + TOP) / 2), (0.12, 0.1, TOP - FL), hx('2e3135'), var=0.0)
    b.box((S, 0, 2.25), (0.12, 1.2, 0.1), hx('2e3135'), var=0.0)
    b.box((S, 0, 1.2), (0.06, 1.0, 0.06), hx('2e3135'), var=0.0)
    b.box((S + 0.05, 0.38, 1.3), (0.06, 0.12, 0.16), hx('b08a2a'), var=0.0)  # lock


def sign(b):
    b.box((0, 0, 1.0), (0.1, 0.1, 2.0), WOOD_D, var=0.04)
    b.box((0.08, 0, 1.88), (0.05, 1.0, 0.56), WOOD_L, rot=(0.05, 0, 0), var=0.03)
    for a in (0.5, -0.5):
        b.box((0.11, 0, 1.88), (0.02, 0.85, 0.09), SIGN_R, rot=(a, 0, 0), var=0.0)


PROPS = [
    ("SM_Tree_Pine", tree_pine), ("SM_Tree_Round", tree_round), ("SM_Tree_Dead", tree_dead),
    ("SM_Bush", bush),
    ("SM_Rock_Large", lambda b: rock(b, (4.0, 3.2, 2.6))),
    ("SM_Rock_Medium", lambda b: rock(b, (1.8, 1.5, 1.2))),
    ("SM_Rock_Small", lambda b: rock(b, (0.7, 0.6, 0.45), extra=False)),
    ("SM_Ruin_House", ruin_house), ("SM_Ruin_Wall", ruin_wall), ("SM_Barricade", barricade),
    ("SM_CarWreck", car_wreck), ("SM_Crate", crate), ("SM_Barrel", barrel), ("SM_Fence", fence),
    ("SM_Watchtower", watchtower), ("SM_ArenaWall", arena_wall), ("SM_Cage", cage), ("SM_Sign", sign),
]
NO_CENTER = {"SM_Watchtower"}  # pivot = platform center (ladder sticks out on -X)


def make_material():
    mat = bpy.data.materials.get(MAT_NAME) or bpy.data.materials.new(MAT_NAME)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    try:
        nt = mat.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = "Col"
        nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.9
    except Exception as e:
        print("material nodes skipped:", e)
    return mat


def tri_count(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def helper_mesh(name, verts_fn, col):
    b = Builder(0)
    verts_fn(b, col)
    ob = b.finish(name, bpy.data.materials[MAT_NAME])
    return ob


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    mat = make_material()
    objs = []
    for i, (name, fn) in enumerate(PROPS):
        b = Builder(1000 + i)
        fn(b)
        objs.append(b.finish(name, mat, center_xy=name not in NO_CENTER))

    info = {}
    for ob in objs:
        d = ob.dimensions
        info[ob.name] = {"tris": tri_count(ob.data), "dims_m": [round(d.x, 3), round(d.y, 3), round(d.z, 3)]}
        print(f"{ob.name:16s} tris={info[ob.name]['tris']:5d} dims={info[ob.name]['dims_m']}")
    with open(os.path.join(OUT, "props_info.json"), "w") as fh:
        json.dump(info, fh, indent=2)

    # ---------- export (all at origin) ----------
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs:
        ob.location = (0, 0, 0); ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "L01_Props.fbx"), use_selection=True,
                             object_types={'MESH'}, apply_unit_scale=True, mesh_smooth_type='FACE',
                             colors_type='SRGB', add_leaf_bones=False)

    # ---------- preview layout ----------
    rows = [["SM_Tree_Pine", "SM_Tree_Round", "SM_Tree_Dead", "SM_Bush", "SM_Rock_Large", "SM_Rock_Medium", "SM_Rock_Small", "SM_Sign"],
            ["SM_Ruin_House", "SM_Ruin_Wall", "SM_Barricade", "SM_CarWreck", "SM_Crate", "SM_Barrel"],
            ["SM_Watchtower", "SM_Cage", "SM_ArenaWall", "SM_Fence"]]
    byname = {o.name: o for o in objs}
    gap = 2.0
    y = 0.0
    for row in rows:
        widths = [byname[n].dimensions.x for n in row]
        depth = max(byname[n].dimensions.y for n in row)
        x = -(sum(widths) + gap * (len(row) - 1)) / 2
        for n, w in zip(row, widths):
            byname[n].location = (x + w / 2, y, 0)
            x += w + gap
        y += depth + 3.0

    # ground + human ref
    def ground(b, col):
        b.box((0, 0, -0.05), (80, 60, 0.1), col, var=0.0)
    g = helper_mesh("PV_Ground", ground, hx('8f7d5a'))
    g.location = (0, y / 2 - 3, 0); g.location.z = -0.1 + 0.0
    def human(b, col):
        b.box((0, 0, 0.9), (0.45, 0.3, 1.8), col, var=0.0)
    hb = helper_mesh("PV_Human_1m8", human, hx('e0402a'))
    hs = byname["SM_Sign"]
    hb.location = (hs.location.x + 2.6, 0, 0)

    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.view_settings.view_transform = 'Standard'
    sh = scene.display.shading
    sh.light = 'STUDIO'
    try:
        sh.color_type = 'VERTEX'
    except Exception:
        sh.color_type = 'ATTRIBUTE'
    sh.show_shadows = True
    sh.shadow_intensity = 0.35
    sh.show_cavity = False
    sh.show_object_outline = True
    sh.object_outline_color = (0.1, 0.1, 0.1)
    scene.display.light_direction = (0.4, -0.5, 0.8)
    try:
        scene.world = scene.world or bpy.data.worlds.new("W")
    except Exception:
        pass
    scene.render.resolution_x, scene.render.resolution_y = 2400, 1500
    scene.render.film_transparent = False
    cam_d = bpy.data.cameras.new("Cam"); cam_d.type = 'ORTHO'
    cam = bpy.data.objects.new("Cam", cam_d); scene.collection.objects.link(cam)
    scene.camera = cam
    cam.rotation_euler = (math.radians(58), 0, math.radians(20))
    # fit ortho scale
    bpy.context.view_layer.update()
    R = cam.rotation_euler.to_matrix()
    inv = R.transposed()
    pts = []
    for ob in objs + [hb]:
        for c in ob.bound_box:
            pts.append(inv @ (ob.matrix_world @ Vector(c)))
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    aspect = scene.render.resolution_x / scene.render.resolution_y
    cam_d.ortho_scale = max(max(xs) - min(xs), (max(ys) - min(ys)) * aspect) * 1.06
    cam.location = R @ Vector((cx, cy, max(zs) + 50))
    cam_d.clip_end = 500
    scene.render.filepath = os.path.join(OUT, "L01_Props_preview.png")
    bpy.ops.render.render(write_still=True)

    # label positions
    from bpy_extras.object_utils import world_to_camera_view
    labels = {}
    for ob in objs + [hb]:
        p = ob.location + Vector((0, -ob.dimensions.y / 2 - 0.3, 0))
        v = world_to_camera_view(scene, cam, p)
        labels[ob.name] = [v.x * scene.render.resolution_x, (1 - v.y) * scene.render.resolution_y]
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "labels.json"), "w") as fh:
        json.dump(labels, fh)


if __name__ == "__main__":
    main()
