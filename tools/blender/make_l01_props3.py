"""L01 cartoon low-poly props, batch 3: ALIEN FOREST (Blender 5.2 / bpy).
Run: python make_l01_props3.py -- [out_dir]
Builds 21 static meshes with vertex colors ("Col", BYTE_COLOR/CORNER), "UVMap" (cube projection,
1 UV unit = 1 m), two materials (M_L01_VertexColor + M_L01_Glow for emissive faces), renders a
labelled preview with bloomed glow, exports L01_Props3.fbx and props3_info.json.
"""
import bpy, bmesh, math, random, json, sys, os, subprocess
from mathutils import Matrix, Vector, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "/mnt/user-data/outputs/l01"
os.makedirs(OUT, exist_ok=True)
MAT_NAME = "M_L01_VertexColor"
GLOW_NAME = "M_L01_Glow"
TAU = 2 * math.pi


# ---------------- palette (sRGB 0-1) ----------------
def hx(h):
    h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))

TRUNK = hx('3d2356'); TRUNK2 = hx('553075'); TRUNK3 = hx('2c1a40')
PURP = hx('8e3fc4'); PURP_D = hx('5a2486'); PURP_L = hx('b46ee0')
MAG = hx('d63c9e'); MAG_L = hx('f07cc4'); MAG_D = hx('9c2a78')
TEAL = hx('1fa39a'); TEAL_L = hx('52d6c4'); TEAL_D = hx('147372'); TEAL_P = hx('a6f2e2')
BLUE = hx('2f68c8'); BLUE_L = hx('4f8fe6')
ORANGE = hx('e2582a'); ORANGE_D = hx('b23c1c'); ORANGE_L = hx('f07a3a')
SPOT = hx('f6e8c8'); CREAM = hx('eadbb4'); CREAM_D = hx('cdb98e')
GREEN = hx('5fae3c'); GREEN_L = hx('86c94e'); GREEN_D = hx('3f7d2e')
ROCK = hx('4a3e5c'); ROCK_L = hx('6a5a80'); ROCK_D = hx('362c46')
RP = hx('7d6e94'); RP_L = hx('a092b6'); RP_D = hx('5e5175'); MOSS = hx('4fa896')
BONE = hx('eadfb4'); BONE_D = hx('c9b787'); BONE_C = hx('a6915f'); SOCKET = hx('3a2448')
HULL = hx('7f9a9c'); HULL_L = hx('a6c2c0'); HULL_D = hx('516c72'); HULL_T = hx('3f8a88'); SCORCH = hx('3a3540')
GLASS = hx('4fb8b0'); DIRT = hx('5a4a5e'); DIRT_D = hx('46394c')
MONO = hx('2e2a40'); MONO_L = hx('423c5a')
WOOD = hx('8a6a4a'); WOOD_L = hx('a07a52'); WOOD_D = hx('6e5038'); WOOD_DD = hx('4e3a2a'); ROOFW = hx('5e4a3c')
STONE = hx('8c8494'); STONE_L = hx('a29aa8'); STONE_D = hx('6f6878')
VINE = hx('8a3fb0'); VINE_D = hx('62288a')
TURB = hx('dcdcd4'); TURB_D = hx('b8bab4'); RUST = hx('a5552a'); RUST_D = hx('7a3a1c'); CONC = hx('a8a4a0')
WARN = hx('d8352a')
EGG_P = hx('7a3f9a'); EGG_G = hx('6fae3c'); EGG_G2 = hx('86c24a'); SLIME = hx('4f8a3a')
PINK = hx('ff6fb5'); PINK_L = hx('ffa3d1'); PINK_D = hx('d84a92')
# glow colors (bright, these drive emission)
G_CYAN = hx('5ff6ff'); G_CYAN_L = hx('aefcff'); G_CYAN_D = hx('2ec4e6')
G_MAG = hx('ff4fd8'); G_MAG_L = hx('ff9ae9'); G_MAG_D = hx('d630b4')
G_GREEN = hx('8cff5a'); G_GREEN_D = hx('4fd63a'); G_YG = hx('dcff4a'); G_YEL = hx('fff27a')
G_FAINT = hx('62c85a')


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
            if f is None:
                continue
            k = 1.0 + (self.rng.random() * 2 - 1) * var if var else 1.0
            c = (clamp01(col[0] * k), clamp01(col[1] * k), clamp01(col[2] * k), 1.0)
            for l in f.loops:
                l[self.cl] = c

    def glow(self, faces, col, var=0.0):
        self.paint(faces, col, var)
        for f in faces:
            if f is not None:
                f.material_index = 1

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

    def paint_where(self, faces, pred, col, var=0.0, glow=False):
        sel = []
        for f in faces:
            f.normal_update()
            if pred(f.normal):
                sel.append(f)
        (self.glow if glow else self.paint)(sel, col, var)
        return sel

    def mark(self):
        return len(self.bm.verts)

    def since(self, n0):
        self.bm.verts.ensure_lookup_table()
        return [self.bm.verts[i] for i in range(n0, len(self.bm.verts))]

    # -- primitives (same conventions as batches 1-2)
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

    def cyl(self, base, r1, h, segs, col, r2=None, rot=(0, 0, 0), var=0.04, scale=(1, 1, 1)):
        r2 = r1 if r2 is None else r2
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segs,
                                  radius1=r1, radius2=r2, depth=h)
        verts = r['verts']
        if r2 == 0:
            top = [v for v in verts if v.co.z > 0]
            if len(top) > 1:
                bmesh.ops.pointmerge(self.bm, verts=top, merge_co=Vector((0, 0, h / 2)))
                verts = [v for v in verts if v.is_valid]
        M = (Matrix.Translation(base) @ Euler(rot).to_matrix().to_4x4()
             @ Matrix.Diagonal(Vector((scale[0], scale[1], scale[2], 1)))
             @ Matrix.Translation((0, 0, h / 2)))
        return self._place(verts, M, col, var)

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

    def _face(self, vs):
        out = []
        for v in vs:
            if not out or out[-1] is not v:
                out.append(v)
        if len(out) > 1 and out[0] is out[-1]:
            out.pop()
        if len(set(out)) < 3:
            return None
        try:
            return self.bm.faces.new(out)
        except ValueError:
            return None

    def _bridge(self, A, C):
        fs = []
        if len(A) == 1 and len(C) == 1:
            return fs
        n = max(len(A), len(C))
        for k in range(n):
            k2 = (k + 1) % n
            if len(C) == 1:
                f = self._face([A[k], A[k2], C[0]])
            elif len(A) == 1:
                f = self._face([A[0], C[k2], C[k]])
            else:
                f = self._face([A[k], A[k2], C[k2], C[k]])
            fs.append(f)
        return fs

    def _paint_bands(self, bands, col, var, glow=False):
        fn = self.glow if glow else self.paint
        for i, fs in enumerate(bands):
            c = col(i) if callable(col) else (col[i % len(col)] if isinstance(col, list) else col)
            fn([f for f in fs if f], c, var)

    def tube(self, pts, radii, segs, col, var=0.04, up=None, cap0=True, cap1=True, phase=0.0,
             jit=0.0, glow=False):
        """Swept tube along polyline with parallel-transport frames. radii: float or (rN, rB).
        Returns (segment face lists [k-ordered], cap0 faces, cap1 faces)."""
        pts = [Vector(p) for p in pts]; n = len(pts)
        T = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
        up = Vector(up) if up is not None else (Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0)))
        N = (up - T[0] * up.dot(T[0])).normalized()
        rings = []
        for i in range(n):
            if i > 0:
                N = N - T[i] * N.dot(T[i])
                if N.length < 1e-6:
                    N = T[i].orthogonal()
                N.normalize()
            B = T[i].cross(N)
            r = radii[i]
            rx, ry = (r, r) if not isinstance(r, (tuple, list)) else r
            if rx < 1e-6 and ry < 1e-6:
                rings.append([self.bm.verts.new(pts[i])]); continue
            ring = []
            for k in range(segs):
                a = phase + TAU * k / segs
                j = 1 + (self.rng.random() - 0.5) * 2 * jit if jit else 1.0
                ring.append(self.bm.verts.new(pts[i] + (N * math.cos(a) * rx + B * math.sin(a) * ry) * j))
            rings.append(ring)
        segf = [self._bridge(rings[i], rings[i + 1]) for i in range(n - 1)]
        c0 = [self._face(rings[0][::-1])] if cap0 and len(rings[0]) > 2 else []
        c1 = [self._face(rings[-1])] if cap1 and len(rings[-1]) > 2 else []
        self._paint_bands(segf, col, var, glow)
        fn = self.glow if glow else self.paint
        c_first = col(0) if callable(col) else (col[0] if isinstance(col, list) else col)
        c_last = col(len(segf) - 1) if callable(col) else (col[(len(segf) - 1) % len(col)] if isinstance(col, list) else col)
        fn([f for f in c0 if f], c_first, var); fn([f for f in c1 if f], c_last, var)
        return segf, [f for f in c0 if f], [f for f in c1 if f]

    def lathe(self, M, prof, segs, col, var=0.04, phase=0.0, rjit=None, glow=False):
        """Surface of revolution of profile [(r, z)] around local Z, transformed by M. Returns bands."""
        rows = []
        for j, (r, z) in enumerate(prof):
            if r < 1e-6:
                rows.append([self.bm.verts.new(M @ Vector((0, 0, z)))]); continue
            row = []
            for k in range(segs):
                a = phase + TAU * k / segs
                rr = r * (rjit(j, k) if rjit else 1.0)
                row.append(self.bm.verts.new(M @ Vector((rr * math.cos(a), rr * math.sin(a), z))))
            rows.append(row)
        bands = [self._bridge(rows[j], rows[j + 1]) for j in range(len(rows) - 1)]
        if len(rows[0]) > 2:
            bands[0].append(self._face(rows[0][::-1]))
        if len(rows[-1]) > 2:
            bands[-1].append(self._face(rows[-1]))
        self._paint_bands(bands, col, var, glow)
        return bands

    def crystal(self, base, d, L, r, cols, sides=6, phase=0.0, glow=True, tipf=0.72):
        base = Vector(base); d = Vector(d).normalized()
        segf, c0, _ = self.tube([base, base + d * L * tipf, base + d * L], [r * 0.82, r, 0.0], sides,
                                cols[0], var=0.0, cap0=True, cap1=False, phase=phase)
        fn = self.glow if glow else self.paint
        for fs in segf:
            for k, f in enumerate(fs):
                if f:
                    fn([f], cols[k % len(cols)], 0.03)
        fn(c0, cols[-1], 0.0)

    # -- finish
    def finish(self, name, mats, center_xy=True, zshift=True, zclamp=True, height=None):
        bm = self.bm
        bm.verts.ensure_lookup_table()
        if zclamp:
            for v in bm.verts:
                if v.co.z < 0:
                    v.co.z = 0.0
        xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]; zs = [v.co.z for v in bm.verts]
        off = Vector(((min(xs) + max(xs)) / 2 if center_xy else 0,
                      (min(ys) + max(ys)) / 2 if center_xy else 0, min(zs) if zshift else 0))
        for v in bm.verts:
            v.co -= off
        if height:
            zm = max(v.co.z for v in bm.verts)
            for v in bm.verts:
                v.co.z *= height / zm
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        uv = bm.loops.layers.uv.new("UVMap")
        has_glow = False
        for f in bm.faces:
            f.smooth = False
            f.normal_update()
            has_glow |= f.material_index == 1
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                c = l.vert.co
                if ax == 0:
                    l[uv].uv = (c.y * (1 if n.x > 0 else -1), c.z)
                elif ax == 1:
                    l[uv].uv = (c.x * (-1 if n.y > 0 else 1), c.z)
                else:
                    l[uv].uv = (c.x, c.y * (1 if n.z > 0 else -1))
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(mats[0])
        if has_glow:
            me.materials.append(mats[1])
        ca = me.color_attributes.get("Col")
        assert ca is not None and ca.data_type == 'BYTE_COLOR' and ca.domain == 'CORNER', name
        me.color_attributes.active_color = ca
        me.color_attributes.render_color_index = me.color_attributes.find("Col")
        me.uv_layers.active = me.uv_layers["UVMap"]
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        ob["has_glow"] = has_glow
        return ob


def surf_rot(r, z_slope_dr):
    """tilt angle for a disc lying on a lathe surface with slope dz/dr"""
    return math.atan(-z_slope_dr)


# =================== PROPS ===================
def tree_spiral(b):
    r = b.rng
    N = 14
    lean = lambda t: 0.9 * t * t
    for s in (0, 1):
        pts, rad = [], []
        for i in range(N + 1):
            t = i / N; z = 6.4 * t; R = 0.34 + 0.1 * t; a = t * 3.0 * math.pi + s * math.pi
            pts.append((lean(t) + R * math.cos(a), R * math.sin(a), z - 0.15 * (i == 0)))
            rad.append(0.5 - 0.27 * t)
        b.tube(pts, rad, 7, lambda i, s=s: (TRUNK, TRUNK2)[(i + s) % 2], var=0.06)
    for k in range(5):  # root flares
        a = k * TAU / 5 + 0.3
        b.tube([(0.35 * math.cos(a), 0.35 * math.sin(a), 1.0), (0.9 * math.cos(a), 0.9 * math.sin(a), 0.35),
                (1.45 * math.cos(a), 1.45 * math.sin(a), -0.1)], [0.3, 0.2, 0.06], 5, TRUNK3, var=0.05)
    top = Vector((lean(1.0), 0, 6.2))
    blobs = [((0.25, 0.15, 7.75), (2.0, 1.9, 1.3), MAG),
             ((-1.9, 0.9, 7.0), (1.4, 1.3, 1.0), PURP),
             ((1.9, -1.2, 6.9), (1.45, 1.3, 1.0), PURP),
             ((-0.5, -1.8, 6.45), (1.15, 1.1, 0.85), MAG)]
    for (c, sc, col) in blobs:
        c = top + Vector((c[0], c[1], 0)) + Vector((0, 0, c[2] - 6.2))
        mid = top.lerp(c, 0.5) + Vector((0, 0, 0.35))
        b.tube([top - Vector((0, 0, 0.4)), mid, top.lerp(c, 0.85)], [0.24, 0.18, 0.12], 5, TRUNK2, var=0.05)
        fs = b.ico(c, sc, 2, col, jitter=0.08, var=0.07, rot=(0, 0, r.random()))
        for f in fs:
            f.normal_update()
            nz = f.normal.z
            if nz > 0.55:
                b.paint([f], MAG_L if col == MAG else PURP_L, 0.06)
            elif nz < -0.35:
                b.paint([f], PURP_D, 0.06)
            if r.random() < 0.1 and nz > -0.2:
                b.paint([f], hx('ffb0e0'), 0.03)   # pale spots
        # hanging glow bulbs
        for q in range(2 if sc[0] > 1.3 else 1):
            a = r.random() * TAU
            bx, by = c.x + math.cos(a) * sc[0] * 0.45, c.y + math.sin(a) * sc[1] * 0.45
            zb = c.z - sc[2] * 0.8
            L = r.uniform(0.7, 1.5)
            b.cyl((bx, by, zb - L), 0.035, L + 0.1, 4, TRUNK3, var=0.0)
            b.glow(b.ico((bx, by, zb - L - 0.12), (0.2, 0.2, 0.27), 1, G_CYAN, var=0.0), G_CYAN, 0.08)


def tree_umbrella(b):
    r = b.rng
    N = 14
    pts, rad = [], []
    for i in range(N + 1):
        t = i / N
        pts.append((-0.9 * math.sin(math.pi * t) + 1.8 * t * t, 0.4 * math.sin(2 * math.pi * t), 11.3 * t - 0.1 * (i == 0)))
        rad.append(0.75 if i == 0 else 0.45 - 0.25 * t)
    b.tube(pts, rad, 6, lambda i: (TEAL_D, hx('1c8a84'))[i % 2], var=0.05)
    for k in range(4):
        a = k * TAU / 4 + 0.6
        b.tube([(0.3 * math.cos(a), 0.3 * math.sin(a), 0.7), (1.0 * math.cos(a), 1.0 * math.sin(a), -0.1)],
               [0.22, 0.08], 4, TEAL_D, var=0.05)

    def canopy(c, R, rot, dots, thick=1.0):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((R / 3.5, R / 3.5, R / 3.5 * thick, 1))
        prof = [(0, 0.8), (1.3, 0.72), (2.5, 0.42), (3.5, -0.12), (3.2, -0.32), (2.0, -0.18), (0.6, -0.08), (0, -0.12)]
        jit = lambda j, k: (1.08 if k % 2 else 0.94) if j in (3, 4) else 1.0  # scalloped rim
        bands = b.lathe(M, prof, 18, [TEAL_L, TEAL, TEAL, TEAL_D, TEAL_P, TEAL_P, TEAL_P], var=0.06, rjit=jit)
        for f in bands[0] + bands[1]:   # light streaks on top
            if r.random() < 0.25:
                b.paint([f], hx('7ef0dc'), 0.03)
        for q in range(dots):
            rr = r.uniform(0.6, 3.0); a = r.random() * TAU
            zl = -0.18 - 0.07 * (1 - rr / 3) - 0.2
            p = M @ Vector((rr * math.cos(a), rr * math.sin(a), zl))
            b.glow(b.ico(p, (0.13 * R / 3.5 + 0.03,) * 3, 1, G_CYAN_L, var=0.0), G_CYAN_L if q % 3 else G_MAG_L, 0.05)
    canopy(Vector(pts[-1]) + Vector((0, 0, 0.1)), 3.5, (0.06, -0.1, 0), 12)
    # side shoot with small umbrella
    p0 = Vector(pts[7]); p2 = p0 + Vector((-1.6, 1.2, 2.2))
    b.tube([p0, p0.lerp(p2, 0.5) + Vector((-0.3, 0, 0.1)), p2], [0.2, 0.15, 0.12], 5, TEAL_D, var=0.05)
    canopy(p2 + Vector((0, 0, 0.05)), 1.4, (0.2, -0.25, 0), 4)


def tree_fan(b):
    r = b.rng
    n = 11
    for k in range(n):
        a = k * TAU / n + r.uniform(-0.2, 0.2)
        L = r.uniform(5.2, 7.0)
        phi0 = r.uniform(0.08, 0.55); kap = r.uniform(0.7, 1.4)
        Wm = r.uniform(0.5, 0.7)
        pts, rad = [], []
        p = Vector((0.15 * math.cos(a), 0.15 * math.sin(a), 0.1)); S = 8
        for i in range(S + 1):
            t = i / S
            pts.append(p.copy())
            w = 0.06 if i == 0 else (0.0 if i == S else Wm * math.sin(math.pi * t) ** 0.7)
            if 0 < i < S and i % 2 == 0:
                w *= 0.78   # serrated fern edge
            rad.append((w, 0.07 * (1 - t) + 0.02) if i < S else 0.0)
            phi = phi0 + kap * t * t
            p = p + Vector((math.sin(phi) * math.cos(a), math.sin(phi) * math.sin(a), math.cos(phi))) * (L / S)
        segf, _, _ = b.tube(pts, rad, 4, TEAL, var=0.0, up=(-math.sin(a), math.cos(a), 0))
        for i, fs in enumerate(segf):
            t = i / (len(segf) - 1)
            top = mix(TEAL_L, BLUE_L, t); bot = mix(TEAL_D, BLUE, t)
            for f in fs:
                if not f: continue
                f.normal_update()
                b.paint([f], top if f.normal.z > -0.05 else bot, 0.05)
    for k in range(2):   # fiddleheads (young curled fronds)
        a = k * math.pi + 0.8
        d = Vector((math.cos(a), math.sin(a), 0))
        pts = [Vector((0, 0, 0.1)) + d * 0.2]
        for i in range(1, 6):
            pts.append(pts[0] + d * 0.15 * i + Vector((0, 0, 0.55 * i)))
        c = pts[-1] + d * 0.45
        for i in range(1, 11):
            ang = math.pi + i * 0.55; rr = 0.45 * (1 - i / 13)
            pts.append(c + d * (rr * math.cos(ang)) + Vector((0, 0, rr * math.sin(-ang + 2 * math.pi) * -1)))
        rad = [0.12 * (1 - 0.6 * i / len(pts)) for i in range(len(pts))]
        b.tube(pts, rad, 5, lambda i: mix(TEAL, BLUE_L, i / 15), var=0.05)
    b.ico((0, 0, 0.0), (0.8, 0.8, 0.55), 1, TEAL_D, jitter=0.1, var=0.08, zclamp=0.0)


def mushroom_giant(b):
    r = b.rng
    pts = [(0, 0, -0.05), (0.1, 0.05, 0.8), (0.25, 0.0, 2.2), (0.15, -0.1, 3.6), (-0.05, -0.05, 5.0), (0.0, 0.0, 5.9)]
    b.tube(pts, [1.05, 0.72, 0.6, 0.58, 0.62, 0.66], 10, [CREAM_D, CREAM, CREAM, CREAM_D, CREAM], var=0.04)
    # skirt ring
    M = Matrix.Translation((-0.03, -0.05, 4.4))
    b.lathe(M, [(0.62, 0.25), (1.0, -0.15), (0.9, -0.3), (0.6, -0.1)], 12, [CREAM, CREAM_D, CREAM_D], var=0.04,
            rjit=lambda j, k: (1.0 if k % 2 else 0.88) if j in (1, 2) else 1.0)
    # cap
    Mc = Matrix.Translation((0, 0, 0)) @ Euler((0.05, -0.06, 0)).to_matrix().to_4x4()
    prof = [(0, 7.0), (1.3, 6.9), (2.3, 6.55), (2.9, 6.0), (3.0, 5.6), (2.75, 5.45), (1.8, 5.55), (0.7, 5.75), (0, 5.8)]
    bands = b.lathe(Mc, prof, 16, [ORANGE_L, ORANGE, ORANGE, ORANGE_D, ORANGE_D, G_CYAN, G_CYAN_D, G_CYAN_D],
                    var=0.05, rjit=lambda j, k: (1.04 if k % 2 else 0.97) if j in (3, 4) else 1.0)
    for j in (5, 6, 7):
        for k, f in enumerate(bands[j]):
            b.glow([f], G_CYAN if k % 2 else G_CYAN_D, 0.03)
    # gill fins (glowing)
    for k in range(12):
        a = k * TAU / 12 + 0.13
        p0 = Mc @ Vector((0.9 * math.cos(a), 0.9 * math.sin(a), 5.66))
        p1 = Mc @ Vector((2.6 * math.cos(a), 2.6 * math.sin(a), 5.48))
        fs = b.box((p0 + p1) / 2 - Vector((0, 0, 0.08)), ((p1 - p0).length, 0.08, 0.22), G_CYAN_L, rot=(0, 0, a), var=0.0)
        b.glow(fs, G_CYAN_L, 0.04)
    # pale spots on the cap
    spots = [(0.6, 0.3), (1.6, 1.2), (1.9, 3.0), (2.4, 4.4), (1.2, 5.3), (2.5, 2.1), (2.0, 5.9)]
    for (rr, a) in spots:
        # interpolate profile height
        pr = prof[:5]
        for (r0, z0), (r1, z1) in zip(pr[:-1], pr[1:]):
            if r0 <= rr <= r1:
                t = (rr - r0) / (r1 - r0); z = z0 + (z1 - z0) * t; sl = (z1 - z0) / (r1 - r0); break
        p = Mc @ Vector((rr * math.cos(a), rr * math.sin(a), z + 0.02))
        tilt = surf_rot(rr, sl)
        s = r.uniform(0.32, 0.5)
        b.ico(p, (s, s, 0.1), 1, SPOT, var=0.04, rot=(0, tilt, a))
    # root bumps
    for k in range(4):
        a = k * TAU / 4 + 0.4
        b.ico((1.0 * math.cos(a), 1.0 * math.sin(a), 0.0), (0.5, 0.35, 0.3), 1, CREAM_D, var=0.06, rot=(0, 0, a), zclamp=0.0)


def small_mushroom(b, pos, h, cr, capcol, stemcol, glowcol=None, lean=(0, 0)):
    pos = Vector(pos)
    top = pos + Vector((lean[0], lean[1], h))
    b.tube([pos - Vector((0, 0, 0.03)), top], [cr * 0.28, cr * 0.22], 6, stemcol, var=0.05)
    M = Matrix.Translation(top) @ Euler((lean[1] * -0.5, lean[0] * 0.5, 0)).to_matrix().to_4x4()
    prof = [(0, 0.45 * cr), (0.7 * cr, 0.33 * cr), (cr, 0.0), (0.55 * cr, -0.1 * cr), (0, -0.06 * cr)]
    if glowcol:
        bands = b.lathe(M, prof, 6, [mix(glowcol, (1, 1, 1), 0.35), glowcol, glowcol, glowcol], var=0.03, glow=True)
    else:
        bands = b.lathe(M, prof, 6, [mix(capcol, (1, 1, 1), 0.25), capcol, mix(capcol, (0, 0, 0), 0.3),
                                     mix(capcol, (0, 0, 0), 0.3)], var=0.05)
        for k, f in enumerate(bands[1]):
            if k % 2 == 0:
                b.paint([f], mix(capcol, (1, 1, 1), 0.4), 0.03)


def mushroom_cluster(b):
    r = b.rng
    spec = [((0, 0), 1.25, 0.6, PURP, None, (0.08, 0.02)),
            ((0.75, 0.35), 0.8, 0.42, TEAL, None, (0.12, 0.05)),
            ((-0.55, 0.45), 0.55, 0.3, None, G_CYAN, (-0.06, 0.05)),
            ((0.35, -0.6), 0.45, 0.28, MAG, None, (0.05, -0.08)),
            ((-0.6, -0.35), 0.95, 0.45, None, G_MAG, (-0.12, -0.06)),
            ((1.1, -0.25), 0.35, 0.2, None, G_CYAN, (0.04, 0.0))]
    for (xy, h, cr, cc, gc, ln) in spec:
        small_mushroom(b, (xy[0], xy[1], 0), h, cr, cc, CREAM if gc is None else hx('d8cde0'), gc, ln)


def crystal_cluster(b):
    r = b.rng
    b.ico((0, 0, 0), (1.6, 1.3, 0.55), 2, ROCK, jitter=0.15, var=0.1, zclamp=0.0)
    b.ico((1.1, 0.7, 0), (0.6, 0.5, 0.3), 1, ROCK_D, jitter=0.1, var=0.1, zclamp=0.0)
    MAGS = [G_MAG, G_MAG_L, G_MAG_D]; CYS = [G_CYAN, G_CYAN_L, G_CYAN_D]
    spec = [(0.0, 0.0, 3.5, 0.08, 0.0, MAGS), (0.5, 0.3, 2.4, 0.4, 0.6, CYS), (-0.6, 0.2, 2.6, 0.38, 2.5, MAGS),
            (0.3, -0.5, 1.8, 0.5, 5.2, MAGS), (-0.3, -0.4, 1.4, 0.55, 4.0, CYS), (0.9, -0.1, 1.1, 0.7, 6.0, CYS),
            (-1.0, -0.1, 0.9, 0.75, 3.3, MAGS), (0.1, 0.6, 1.2, 0.6, 1.6, MAGS), (-0.7, 0.6, 0.8, 0.9, 2.0, CYS)]
    b.ico((-1.0, -0.6, 0), (0.7, 0.6, 0.35), 2, ROCK_L, jitter=0.12, var=0.1, zclamp=0.0)
    for (x, y, L, tilt, az, cols) in spec:
        d = (math.sin(tilt) * math.cos(az), math.sin(tilt) * math.sin(az), math.cos(tilt))
        b.crystal((x, y, 0.15), d, L, 0.12 + 0.07 * L, cols, phase=r.random())


def crystal_spire(b):
    r = b.rng
    CYS = [G_CYAN, G_CYAN_L, G_CYAN_D, G_CYAN]
    pts = [(0, 0, 0.0), (0.05, 0, 1.4), (0.2, 0.05, 5.0), (0.45, 0.1, 7.1), (0.7, 0.1, 9.0)]
    segf, c0, _ = b.tube(pts, [1.0, 1.25, 1.12, 0.9, 0.0], 6, CYS[0], var=0.0, cap1=False, phase=0.3)
    for i, fs in enumerate(segf):
        for k, f in enumerate(fs):
            b.glow([f], CYS[(k + i) % 4], 0.03)
    b.glow(c0, G_CYAN_D, 0.0)
    for (az, tilt, L) in [(0.4, 0.55, 3.0), (2.2, 0.6, 2.2), (3.6, 0.5, 2.6), (5.0, 0.7, 1.6), (1.3, 0.75, 1.2)]:
        d = (math.sin(tilt) * math.cos(az), math.sin(tilt) * math.sin(az), math.cos(tilt))
        base = (0.8 * math.cos(az), 0.8 * math.sin(az), 0.2)
        b.crystal(base, d, L, 0.14 + 0.08 * L, [G_CYAN_L, G_CYAN, G_MAG] if L < 1.7 else CYS, phase=r.random())
    for k in range(4):
        a = k * TAU / 4 + 0.7
        b.ico((1.3 * math.cos(a), 1.3 * math.sin(a), 0.0), (1.2, 0.9, 0.75), 2 if k < 2 else 1,
              (ROCK, ROCK_D, ROCK_L, ROCK)[k], jitter=0.15, var=0.1, zclamp=0.0, rot=(0, 0, a))


def tentacle_plant(b):
    r = b.rng
    M = Matrix.Identity(4)
    b.lathe(M, [(0, 0), (0.38, 0.06), (0.52, 0.35), (0.42, 0.65), (0.2, 0.82), (0, 0.85)], 6,
            [PURP_D, GREEN, GREEN_L, PURP, PURP], var=0.06)
    n = 6
    for k in range(n):
        a = k * TAU / n + r.uniform(-0.2, 0.2)
        L = r.uniform(1.8, 2.3); phi0 = r.uniform(0.15, 0.45); curl = r.uniform(3.4, 4.4)
        p = Vector((0.18 * math.cos(a), 0.18 * math.sin(a), 0.72))
        pts = []; S = 6
        for i in range(S + 1):
            pts.append(p.copy())
            t = i / S
            phi = phi0 + curl * t ** 2.2
            step = L / S * (1 - 0.45 * t)
            p = p + Vector((math.sin(phi) * math.cos(a), math.sin(phi) * math.sin(a), math.cos(phi))) * step
        pts.append(p)
        rad = [0.1 - 0.065 * i / S for i in range(S)] + [0.075, 0.0]
        segf, _, _ = b.tube(pts, rad, 4, lambda i: mix(GREEN, PURP, min(1, i / 5)), var=0.05)
        b.glow(segf[-1] + segf[-2], G_YG, 0.04)


def spore_pod(b):
    r = b.rng
    b.lathe(Matrix.Identity(4), [(0, 0), (0.75, 0.04), (0.5, 0.28), (0, 0.34)], 6, [PURP_D, PURP, PURP_L], var=0.06)
    spec = [(0.0, 0.0, 2.0, 0.08, 0.0, 1.0), (0.3, 0.15, 1.4, 0.45, 0.6, 0.8), (-0.3, 0.2, 1.1, 0.5, 2.6, 0.75),
            (0.05, -0.32, 1.6, 0.35, 4.6, 0.9)]
    for (x, y, L, tilt, az, s) in spec:
        d = Vector((math.sin(tilt) * math.cos(az), math.sin(tilt) * math.sin(az), math.cos(tilt)))
        p0 = Vector((x, y, 0.2)); p2 = p0 + d * L
        p1 = p0.lerp(p2, 0.5) + Vector((0, 0, 0.05)) - d.cross(Vector((0, 0, 1))) * 0.1
        b.tube([p0, p1, p2], [0.08, 0.06, 0.05], 4, [GREEN_D, PURP], var=0.05)
        q = Vector((0, 0, 1)).rotation_difference(d)
        M = Matrix.Translation(p2 - d * 0.05) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((s, s, s, 1))
        bands = b.lathe(M, [(0, -0.05), (0.22, 0.04), (0.34, 0.3), (0.3, 0.55), (0.13, 0.72), (0, 0.75)], 6,
                        G_GREEN, var=0.0)
        for j, fs in enumerate(bands):
            for k, f in enumerate(fs):
                b.glow([f], (G_GREEN, G_GREEN_D)[k % 2] if j < 4 else hx('c8ff9a'), 0.03)


def flower_glow(b):
    r = b.rng
    stem = [(0, 0, -0.02), (0.04, 0.0, 0.3), (0.0, 0.03, 0.6), (0.07, 0.0, 0.84)]
    b.tube(stem, [0.035, 0.03, 0.028, 0.025], 4, GREEN, var=0.05)
    for (a, z, L) in [(0.3, 0.18, 0.34), (3.4, 0.33, 0.3)]:   # stem leaves
        d = Vector((math.cos(a), math.sin(a), 0))
        p0 = Vector((0.02, 0, z))
        pts = [p0, p0 + d * L * 0.4 + Vector((0, 0, 0.1)), p0 + d * L * 0.8 + Vector((0, 0, 0.12)), p0 + d * L + Vector((0, 0, 0.06))]
        b.tube(pts, [(0.02, 0.01), (0.07, 0.015), (0.05, 0.012), 0.0], 4, [GREEN_L, GREEN, GREEN_D],
               var=0.05, up=(-d.y, d.x, 0))
    head = Vector((0.08, 0.0, 0.86))
    R = Euler((0.0, 0.38, 0.0)).to_matrix()
    for k in range(5):
        a = k * TAU / 5
        pts, rad = [], []
        for i in range(5):
            t = i / 4
            pts.append(head + R @ Vector((0.42 * t * math.cos(a), 0.42 * t * math.sin(a), 0.03 + 0.14 * t * t)))
            rad.append(((0.06 + 0.15 * math.sin(math.pi * min(t * 1.25, 1)) if i < 4 else 0.0), 0.012) if i < 4 else 0.0)
        segf, _, _ = b.tube(pts, rad, 4, PINK, var=0.0, up=R @ Vector((-math.sin(a), math.cos(a), 0)), cap0=False)
        for i, fs in enumerate(segf):
            for f in fs:
                if not f: continue
                f.normal_update()
                up = (R @ Vector((0, 0, 1))).dot(f.normal) > 0
                b.paint([f], (PINK_L if i >= 2 else PINK) if up else PINK_D, 0.04)
    M = Matrix.Translation(head) @ R.to_4x4()
    b.lathe(M, [(0, 0.16), (0.07, 0.13), (0.11, 0.05), (0.06, -0.02), (0, -0.03)], 6,
            [G_YEL, G_YEL, hx('ffd24a'), hx('ffd24a')], var=0.03, glow=True)


def grass_tuft(b):
    r = b.rng
    n = 12
    for k in range(n):
        a = k * TAU / n + r.uniform(-0.25, 0.25)
        rr = r.uniform(0.0, 0.12)
        c = Vector((rr * math.cos(a), rr * math.sin(a), 0))
        h = r.uniform(0.35, 0.6)
        lean = r.uniform(0.08, 0.28)
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-d.y, d.x, 0))
        base = [c + side * 0.035, c - side * 0.035, c + d * 0.02]
        mid = [p + d * lean * 0.35 + Vector((0, 0, h * 0.55)) for p in
               [c + side * 0.022, c - side * 0.022, c + d * 0.012]]
        tip = c + d * lean + Vector((0, 0, h))
        V0 = [b.bm.verts.new(p) for p in base]
        V1 = [b.bm.verts.new(p) for p in mid]
        T = b.bm.verts.new(tip)
        low = [b._face([V0[i], V0[(i + 1) % 3], V1[(i + 1) % 3], V1[i]]) for i in range(3)]
        hi = [b._face([V1[i], V1[(i + 1) % 3], T]) for i in range(3)]
        b.paint([f for f in low if f], (TEAL, TEAL_L)[k % 2], 0.06)
        b.paint([f for f in hi if f], (PURP_L, MAG)[k % 2], 0.05)


def bone_ribs(b):
    r = b.rng
    # spine (vertebrae + dorsal spikes), along X at the top
    def zs(x):
        return 6.0 + 0.35 * math.cos(x / 7 * math.pi / 2) - (0.9 * ((-x - 4) / 3) ** 2 if x < -4 else 0)
    b.tube([(x, 0, zs(x)) for x in [-7 + 14 * i / 10 for i in range(11)]],
           [0.22 if i < 10 else 0.08 for i in range(11)], 6, BONE_D, var=0.05)
    for i in range(11):
        x = -6.3 + i * 1.26
        s = 0.6 + 0.35 * math.sin(math.pi * (i + 2) / 13)
        b.tube([(x - 0.3 * s, 0, zs(x)), (x + 0.3 * s, 0, zs(x))], [0.42 * s, 0.42 * s], 6, BONE, var=0.05)
        b.cyl((x, 0, zs(x) + 0.25 * s), 0.18 * s, 0.85 * s, 4, BONE_D, r2=0, rot=(0, -0.35, math.pi / 4), var=0.05)
    # ribs
    pairs = [(-4.6, 5.35, 3.7), (-2.75, 5.6, 3.95), (-0.9, 5.75, 4.1), (0.95, 5.8, 4.15), (2.8, 5.65, 4.0), (4.6, 5.4, 3.8)]
    for (x0, H, A) in pairs:
        for s in (-1, 1):
            pts, rad = [], []
            S = 7
            for i in range(S + 1):
                ph = (math.pi / 2) * i / S
                sp = math.sin(ph)
                y = s * (0.3 + A * sp ** 0.5) - s * 0.25 * max(0, (i - S + 1)) / 1
                z = H * math.cos(ph) ** 0.9
                x = x0 - 0.7 * sp
                pts.append((x, y, z if i < S else -0.1))
                rad.append(0.3 - 0.13 * i / S)
            pts[0] = (x0, s * 0.25, zs(x0) - 0.15)
            b.tube(pts, rad, 5, lambda i: (BONE, BONE_D, BONE)[i % 3] if i not in (2, 6) else BONE_C, var=0.05)
    # fallen skull beside the ribcage (+Y, outside the drive lane)
    sk = Vector((3.6, 6.3, 0))
    R = Euler((0.25, 0.15, 2.5)).to_matrix().to_4x4()
    n0 = b.mark()
    b.ico((0, 0, 0.9), (1.5, 1.15, 1.0), 2, BONE, jitter=0.06, var=0.05)
    b.box((1.5, 0, 0.6), (2.0, 1.25, 0.9), BONE_D, taper=(0.7, 0.6), rot=(0, math.pi / 2 + 0.1, 0), var=0.05)
    b.box((1.6, 0, 0.12), (2.2, 1.1, 0.25), BONE_C, var=0.05)                    # jaw
    for y in (-0.55, 0.55):
        b.ico((1.0, y, 1.15), (0.38, 0.3, 0.3), 1, SOCKET, var=0.0)               # sockets
        b.cyl((-0.6, y * 1.4, 1.4), 0.3, 1.6, 5, BONE_D, r2=0, rot=(math.copysign(0.9, y), -0.7, 0), var=0.05)
    for k in range(4):  # teeth
        b.cyl((2.0 + 0.0, -0.4 + k * 0.27, 0.22), 0.08, 0.35, 3, BONE, r2=0, var=0.0)
    bmesh.ops.transform(b.bm, matrix=Matrix.Translation(sk) @ R, verts=b.since(n0))


def ufo_wreck(b):
    r = b.rng
    n0 = b.mark()
    prof = [(0, 1.7), (2.8, 1.55), (5.5, 1.1), (8.0, 0.35), (9.0, 0.0), (8.7, -0.35), (6.5, -0.85), (3.0, -1.25), (0, -1.3)]
    bands = b.lathe(Matrix.Identity(4), prof, 24, HULL, var=0.0)
    for j, fs in enumerate(bands):
        for k, f in enumerate(fs):
            if not f: continue
            if j == 3:
                col = HULL_T if k % 2 else hx('358079')
            elif j >= 4:
                col = HULL_D if (k + j) % 2 else hx('48606a')
            else:
                col = HULL if (k + j) % 2 else HULL_L
            if r.random() < 0.12:
                col = SCORCH
            b.paint([f], col, 0.04)
    # rim lights (some dead)
    for k in range(18):
        a = k * TAU / 18
        p = (9.02 * math.cos(a), 9.02 * math.sin(a), 0.0)
        fs = b.ico(p, (0.36, 0.36, 0.3), 1, SCORCH, var=0.0)
        if k % 5 == 3 or k in (8, 9):
            b.paint(fs, hx('3d4450'), 0.05)
        else:
            b.glow(fs, G_CYAN if k % 3 else G_MAG, 0.05)
    # dome collar + broken glass shards
    b.cyl((0, 0, 1.35), 3.0, 0.4, 16, HULL_D, r2=2.8, var=0.04)
    for k in range(14):
        a = k * TAU / 14
        h = (0.4 + 2.2 * (0.5 + 0.5 * math.cos(a - 1.0)) ** 2) * r.uniform(0.6, 1.0)
        b.box((2.65 * math.cos(a), 2.65 * math.sin(a), 1.7 + h / 2), (0.14, 1.15, h), GLASS,
              rot=(0, 0.22 + r.uniform(-0.1, 0.15), a), taper=(0.6, 0.5 + r.random() * 0.4), var=0.08)
    b.glow(b.ico((0.2, 0.0, 2.0), (0.9, 0.9, 0.65), 2, G_CYAN, jitter=0.05, var=0.0), G_CYAN, 0.06)  # power core
    b.box((-1.2, 0.6, 2.0), (0.8, 0.9, 0.7), HULL_D, var=0.04)    # pilot seat
    # underside thrusters
    for k in range(8):
        a = k * TAU / 8 + 0.2
        fs = b.cyl((5.0 * math.cos(a), 5.0 * math.sin(a), -1.25), 0.75, 0.25, 8, HULL_D, var=0.03)
        if k % 2 == 0:
            b.paint_where(fs, lambda n: n.z < -0.5, G_CYAN, 0.0, glow=True)
    # torn hull plates bent up + bent antenna
    for k in range(5):
        a = 3.5 + k * 0.45 + r.uniform(-0.1, 0.1); rr = r.uniform(4.0, 6.5)
        b.box((rr * math.cos(a), rr * math.sin(a), 1.25 - (rr - 4) * 0.25), (1.6, 1.0, 0.1), (HULL_D, SCORCH)[k % 2],
              rot=(r.uniform(0.4, 0.9), 0.2, a), var=0.05)
    p0 = Vector((-3.2, 1.8, 1.35)); p1 = p0 + Vector((0.2, 0.1, 2.0)); p2 = p1 + Vector((1.2, 0.4, 0.4))
    b.tube([p0, p1, p2], [0.08, 0.07, 0.05], 4, HULL_L, var=0.0)
    b.glow(b.ico(p2, (0.18,) * 3, 1, G_MAG, var=0.0), G_MAG, 0.0)
    # tilt ~20 deg and sink the low (-Y) side into the ground
    T = Matrix.Translation((0, 0, 1.15)) @ Matrix.Rotation(math.radians(20), 4, 'X')
    bmesh.ops.transform(b.bm, matrix=T, verts=b.since(n0))
    # plowed dirt berm on the buried side + trench ridges
    for (x, y, sx, sy, sz) in [(-4.5, -8.6, 3.2, 1.6, 1.3), (0.5, -9.4, 3.6, 1.8, 1.6), (5.0, -8.4, 3.0, 1.5, 1.2),
                               (-1.5, -12.0, 2.6, 1.6, 0.8), (2.5, -13.0, 2.0, 1.4, 0.6)]:
        b.ico((x, y, -0.3), (sx, sy, sz), 2, DIRT, jitter=0.15, var=0.1, zclamp=-0.6, rot=(0, 0, r.uniform(-0.2, 0.2)))
    # scattered debris panels (partially buried) and a glowing fragment
    for k in range(9):
        a = r.uniform(0, TAU); rr = r.uniform(10.5, 14.0)
        sz = (r.uniform(1.0, 2.6), r.uniform(0.7, 1.6), 0.12)
        fs = b.box((rr * math.cos(a), rr * math.sin(a), 0.15), sz, (HULL, HULL_D, SCORCH, HULL_T)[k % 4],
                   rot=(r.uniform(-0.6, 0.6), r.uniform(-0.6, 0.6), a), var=0.05)
        if k in (2, 6):
            b.paint_where(fs, lambda n: n.z > 0.3, G_CYAN, 0.0, glow=True)
    b.cyl((9.5, 6.0, -0.3), 1.2, 1.0, 8, HULL_L, r2=0.9, rot=(0.5, 0.6, 0), var=0.05)   # broken thruster chunk


def monolith(b):
    r = b.rng
    zs_ = [0.0, 1.2, 2.5, 3.8, 5.0, 6.0, 6.55]
    hxf = lambda z: 0.78 - 0.035 * z
    hyf = lambda z: 0.52 - 0.025 * z
    cxf = lambda z: 0.4 * (z / 7) ** 2
    rings = []
    for z in zs_:
        jz = 0 if z == 0 else r.uniform(-0.04, 0.04)
        ring = [b.bm.verts.new((cxf(z) + sx * hxf(z) * (1 + r.uniform(-0.04, 0.04)), sy * hyf(z), z + jz))
                for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
        rings.append(ring)
    apex = b.bm.verts.new((cxf(7.0) + 0.05, 0.0, 7.0))
    bands = [b._bridge(rings[i], rings[i + 1]) for i in range(len(rings) - 1)] + [b._bridge(rings[-1], [apex])]
    bands[0].append(b._face(rings[0][::-1]))
    for i, fs in enumerate(bands):
        b.paint([f for f in fs if f], (MONO, MONO_L)[i % 2], 0.05)
    # glowing rune grooves on +-Y faces (strokes follow the bend)
    glyphs = [[(0, 0, 0.5, 0), (0, 0.2, 0.3, 0.8)], [(0, 0, 0.42, 1.57), (0.0, 0.0, 0.42, 0)],
              [(-0.1, 0, 0.35, 0.6), (0.1, 0, 0.35, -0.6)], [(0, 0, 0.45, 1.57), (0.0, 0.15, 0.3, 0)],
              [(0, 0, 0.4, 0.4)]]
    for s in (-1, 1):
        for gi, z in enumerate([1.0, 2.1, 3.2, 4.3, 5.35]):
            if s > 0 and gi == 4:
                continue
            for (dx, dz, L, ang) in glyphs[(gi + (s > 0)) % len(glyphs)]:
                zc = z + dz
                slope = (cxf(zc + 0.1) - cxf(zc - 0.1)) / 0.2
                cen = (cxf(zc) + dx, s * (hyf(zc) + 0.005), zc)
                b.glow(b.box(cen, (0.07, 0.05, L), G_CYAN, rot=(0, ang + math.atan(slope), 0), var=0.0), G_CYAN, 0.05)
    b.box((0.0, 0.0, 0.18), (2.0, 1.5, 0.36), ROCK_D, taper=(0.85, 0.85), rot=(0, 0, 0.1), var=0.06)


def alien_arch(b):
    r = b.rng
    S = 20
    pts, rad = [], []
    for i in range(S + 1):
        th = math.pi - math.pi * i / S
        x = 7.0 * math.cos(th)
        z = 7.6 * max(0.0, math.sin(th)) ** 0.28
        pts.append((x, 0.0, z - (0.25 if i in (0, S) else 0)))
        tt = math.sin(th)
        rad.append((1.6 + 0.25 * tt, 1.0 + 0.15 * tt))
    segf, c0, c1 = b.tube(pts, rad, 10, RP, var=0.0, up=(0, 1, 0), jit=0.07)
    for fs in segf + [c0, c1]:
        for f in fs:
            if not f: continue
            f.normal_update()
            zc = f.calc_center_median().z
            col = (RP, RP_L, RP_D)[int(zc / 1.3) % 3]
            if f.normal.z > 0.65:
                col = MOSS
            b.paint([f], col, 0.06)
    for (x, y, z, sx, sy, sz) in [(-7.3, 1.3, 0.0, 0.9, 1.0, 1.3), (7.3, -1.2, 0.0, 0.9, 1.1, 1.2),
                                  (-7.4, -1.5, 0.0, 0.8, 0.8, 0.9), (7.3, 1.5, 0.0, 0.8, 0.8, 1.0),
                                  (-2.5, 0.3, 8.0, 1.5, 1.2, 0.55), (2.0, -0.2, 8.0, 1.2, 1.0, 0.5)]:
        fs = b.ico((x, y, z), (sx, sy, sz), 2 if z == 0 else 1, RP_D, jitter=0.15, var=0.08, zclamp=0.0)
        b.paint_where(fs, lambda n: n.z > 0.6, MOSS, 0.06)
    for (x, y, z, d, L, cols) in [(-6.8, 1.6, 2.5, (-0.3, 0.8, 0.4), 1.4, [G_MAG, G_MAG_L, G_MAG_D]),
                                  (6.9, -1.6, 3.4, (0.4, -0.8, 0.3), 1.1, [G_CYAN, G_CYAN_L, G_CYAN_D]),
                                  (-1.0, 1.0, 8.0, (0.0, 0.9, 0.5), 0.9, [G_CYAN, G_CYAN_L, G_CYAN_D]),
                                  (-0.4, 1.0, 7.9, (0.4, 0.9, 0.4), 0.6, [G_MAG, G_MAG_L, G_MAG_D]),
                                  (4.6, 1.2, 7.0, (0.5, 0.7, 0.6), 1.0, [G_MAG, G_MAG_L, G_MAG_D]),
                                  (-4.8, -1.3, 6.6, (-0.4, -0.7, 0.6), 0.9, [G_CYAN, G_CYAN_L, G_CYAN_D])]:
        b.crystal((x, y, z), d, L, 0.12 + 0.1 * L, cols, phase=r.random())


def plank_wall(b, a0, a1, axis, fixed, z0, topf, openings, pw=0.72, th=0.2):
    r = b.rng
    n = int(math.ceil((a1 - a0) / pw))
    w = (a1 - a0) / n
    for i in range(n):
        s = a0 + w * (i + 0.5)
        top = topf(s)
        if top <= z0 + 0.15:
            continue
        spans = [(z0, top)]
        for (o0, o1, zl, zh) in openings:
            if o0 <= s <= o1:
                spans = [(z0, min(top, zl))] if zl > z0 + 0.05 else []
                if top > zh + 0.1:
                    spans.append((zh, top))
        for (za, zb) in spans:
            col = (WOOD, WOOD_L, WOOD_D)[r.randrange(3)]
            c = (s, fixed, (za + zb) / 2) if axis == 'x' else (fixed, s, (za + zb) / 2)
            sz = (w * 0.94, th, zb - za) if axis == 'x' else (th, w * 0.94, zb - za)
            b.box(c, sz, col, var=0.05, rot=(0, 0, r.uniform(-0.02, 0.02)))


def farmhouse_ruin(b):
    r = b.rng
    X, Y, EAVE, RIDGE = 5.0, 4.0, 3.4, 6.0
    # stone plinth (z 0..1)
    def stones(a0, a1, axis, fixed, skip=None):
        a = a0
        while a < a1 - 0.05:
            L = min(r.uniform(1.4, 2.2), a1 - a)
            if not (skip and skip[0] < a + L / 2 < skip[1]):
                c = (a + L / 2, fixed, 0.5) if axis == 'x' else (fixed, a + L / 2, 0.5)
                sz = (L - 0.06, 0.5, 1.0 + r.uniform(-0.08, 0.1)) if axis == 'x' else (0.5, L - 0.06, 1.0 + r.uniform(-0.08, 0.1))
                b.box(c, sz, (STONE, STONE_L, STONE_D)[r.randrange(3)], var=0.06)
            a += L
    stones(-X, X, 'x', -Y + 0.1, skip=(-0.7, 0.7)); stones(-X, X, 'x', Y - 0.1)
    stones(-Y + 0.35, Y - 0.35, 'y', -X + 0.1); stones(-Y + 0.35, Y - 0.35, 'y', X - 0.1)
    gable = lambda y: EAVE + (RIDGE - EAVE) * (1 - abs(y) / Y)
    plank_wall(b, -X, X, 'x', -Y + 0.1, 1.0, lambda s: EAVE - (max(0, s - 3.0) * 0.9 + r.uniform(0, 0.4) if s > 3 else 0),
               [(-0.65, 0.65, 0.0, 2.4), (-3.6, -2.4, 1.5, 2.6), (2.0, 3.0, 1.5, 2.6)])
    plank_wall(b, -X, X, 'x', Y - 0.1, 1.0, lambda s: EAVE - (max(0, s - 2.0) * 0.75 + r.uniform(0, 0.5) if s > 2 else 0),
               [(-1.2, 0.0, 1.5, 2.6)])
    plank_wall(b, -Y + 0.2, Y - 0.2, 'y', -X + 0.1, 1.0, gable, [(-0.6, 0.6, 1.5, 2.6)])
    plank_wall(b, -Y + 0.2, Y - 0.2, 'y', X - 0.1, 1.0, lambda s: min(gable(s), 1.4 + r.uniform(0, 1.6) - max(0, s) * 0.3), [])
    # door frame and a hanging broken door
    b.box((-0.78, -Y + 0.02, 1.2), (0.14, 0.3, 2.4), WOOD_DD, var=0.03)
    b.box((0.78, -Y + 0.02, 1.2), (0.14, 0.3, 2.4), WOOD_DD, var=0.03)
    b.box((-0.25, -Y - 0.5, 1.05), (1.0, 0.08, 2.0), WOOD_D, rot=(0.0, 0.12, 1.0), var=0.05)
    # roof: ridge beam, rafters, boards (broken hole on +Y side, collapsed +X/+Y corner)
    al = math.atan2(RIDGE + 0.05 - 3.3, 4.45)
    b.box((-0.4, 0, RIDGE), (10.0, 0.22, 0.22), WOOD_DD, var=0.03)
    for x in (-5.0, -2.5, 0.0, 2.5, 4.4):
        for s in (-1, 1):
            if s > 0 and x > 4:
                continue
            b.box_between((x, 0, RIDGE - 0.12), (x, s * 4.4, 3.2), 0.16, 0.2, WOOD_DD, var=0.03)
    nb = 6
    sl = math.hypot(4.45, RIDGE + 0.05 - 3.3)
    for s in (-1, 1):
        for k in range(nb):
            uc = (k + 0.5) / nb
            spans = [(-5.4, 5.4)]
            if s > 0:
                x1 = 5.4 if k == 0 else 2.6 + r.uniform(0, 1.0)
                if 1 <= k <= 4:
                    g0, g1 = -1.4 + r.uniform(0, 0.8), 1.4 + r.uniform(0, 0.9)
                    spans = [(-5.4, g0), (g1, x1)] if x1 > g1 + 0.3 else [(-5.4, g0)]
                else:
                    spans = [(-5.4, x1)]
            elif k == nb - 1:
                spans = [(-5.4, 1.4), (2.7, 5.4)]
            for (xa, xb) in spans:
                cy = s * 4.45 * uc; cz = RIDGE + 0.05 - (RIDGE + 0.05 - 3.3) * uc + 0.08
                col = ROOFW if r.random() > 0.25 else (MOSS if r.random() > 0.5 else WOOD_DD)
                b.box(((xa + xb) / 2, cy, cz), (xb - xa, sl / nb * 0.96, 0.09), col, rot=(-s * al, 0, 0), var=0.06)
    # chimney
    b.box((-3.2, 1.9, 3.2), (0.9, 0.9, 6.4), STONE, var=0.06)
    b.box((-3.2, 1.9, 6.4), (1.05, 1.05, 0.2), STONE_D, var=0.03)
    # fallen planks and rubble at the collapsed corner
    for k in range(5):
        b.box((5.6 + r.uniform(-0.3, 0.8), 2.5 + r.uniform(-1.5, 1.5), 0.08 + 0.1 * k), (2.6, 0.22, 0.08),
              (WOOD_D, ROOFW)[k % 2], rot=(0, r.uniform(-0.15, 0.15), r.uniform(0, math.pi)), var=0.05)
    for k in range(3):
        b.ico((5.8 + r.uniform(0, 0.6), -1.5 + k * 1.2, 0.0), (0.4, 0.35, 0.3), 1, STONE_D, var=0.06, zclamp=0.0)
    # purple alien vines crawling up the walls and over the roof
    vines = [('x', -4.25, -3.0), ('x', -4.25, 1.4), ('x', 4.25, -1.5), ('y', -5.25, 1.8)]
    for vi, (axis, fixed, a0) in enumerate(vines):
        sg = 1 if fixed > 0 else -1
        pts = []
        for i in range(11):
            z = i * 0.42
            a = a0 + 0.5 * math.sin(z * 1.7 + vi)
            if z <= EAVE:
                off = fixed if z < 1.0 else fixed - sg * 0.13
                pts.append((a, off, z) if axis == 'x' else (off, a, z))
            else:
                u = (z - EAVE) / 1.0
                if axis == 'x':
                    yy = sg * (4.45 - 1.5 * u)
                    pts.append((a, yy, 3.3 + (4.45 - abs(yy)) * 2.75 / 4.45 + 0.2))
                else:
                    pts.append((fixed + 0.15 + 0.4 * u, a, EAVE + 0.35 * u))
        segf, _, _ = b.tube(pts, [0.09] * len(pts), 4, lambda i: (VINE, VINE_D)[i % 2], var=0.05)
        for i in range(1, len(pts) - 1, 2):
            p = Vector(pts[i])
            b.cyl(p, 0.14, 0.4, 3, (PURP_L, MAG)[i % 2], r2=0, rot=(r.uniform(0.6, 1.4), 0, r.uniform(0, TAU)), var=0.05)
        for i in (3, 8):
            b.glow(b.ico(Vector(pts[i]) + Vector((0, 0, 0.1)), (0.14,) * 3, 1, G_MAG, var=0.0), G_MAG, 0.05)


def wind_turbine(b):
    r = b.rng
    b.cyl((0, 0, 0), 2.3, 0.4, 8, CONC, r2=2.0, var=0.05)
    n0 = b.mark()
    HUB = 16.4
    tw = [(0, 0, 0.3), (0, 0, 5.0), (0, 0, 10.0), (0, 0, 15.6)]
    segf, _, _ = b.tube(tw, [0.95, 0.8, 0.66, 0.52], 8, TURB, var=0.0)
    for i, fs in enumerate(segf):
        for f in fs:
            c = TURB if r.random() > 0.15 else TURB_D
            if i == 2 and r.random() < 0.35:
                c = RUST
            b.paint([f], c, 0.04)
    b.cyl((0, 0, 2.0), 0.85, 0.22, 8, RUST_D, var=0.04)   # rust band
    b.box((0, -0.86, 1.4), (0.8, 0.12, 2.0), hx('59606a'), var=0.0)   # door
    # nacelle (rotor faces +X)
    b.box((-0.2, 0, HUB), (4.2, 1.7, 1.7), TURB, taper=(1.0, 0.85), var=0.04)
    b.box((-0.2, 0, HUB + 0.86), (3.6, 1.3, 0.06), RUST, var=0.06)
    b.box((-2.2, 0, HUB + 0.3), (0.1, 1.2, 0.7), TURB_D, var=0.0)
    b.cyl((1.9, 0, HUB), 0.75, 1.3, 8, TURB_D, r2=0, rot=(0, math.pi / 2, 0), var=0.04)
    hub = Vector((2.2, 0, HUB))
    for k, ang in enumerate((90, 210, 330)):
        a = math.radians(ang + 12)
        d = Vector((0, math.cos(a), math.sin(a)))
        perp = Vector((1, 0, 0)).cross(d)
        up = perp + Vector((0.35, 0, 0))
        if k == 1:      # broken stub with jagged end
            pts = [hub + d * (0.4 + 4.4 * i / 4) for i in range(5)]
            rad = [(0.3, 0.16), (0.55, 0.14), (0.5, 0.12), (0.45, 0.11), (0.38, 0.1)]
            segf, _, c1 = b.tube(pts, rad, 4, TURB, var=0.04, up=up)
            b.paint(c1, WOOD_DD, 0.0)
            b.paint(segf[-1], RUST, 0.06)
            continue
        L = 7.6
        bend = (k == 2)
        pts = []
        p = hub + d * 0.4; dd = d.copy()
        for i in range(7):
            pts.append(p.copy())
            if bend and i == 3:
                dd = (dd + Vector((0.9, 0, -0.6))).normalized()
            p = p + dd * (L / 6)
        rad = [(0.3, 0.16), (0.62, 0.15), (0.58, 0.13), (0.48, 0.11), (0.38, 0.09), (0.26, 0.07), 0.0]
        segf, _, _ = b.tube(pts, rad, 4, TURB, var=0.04, up=up)
        b.paint(segf[-1], WARN, 0.04)
        for fs in segf[1:-1]:
            for f in fs:
                if r.random() < 0.15:
                    b.paint([f], RUST, 0.05)
    # tilt the whole tower slightly
    T = Matrix.Rotation(math.radians(3.5), 4, 'Y') @ Matrix.Rotation(math.radians(-2.0), 4, 'X')
    bmesh.ops.transform(b.bm, matrix=T, verts=b.since(n0))


def egg_sac(b):
    r = b.rng
    b.lathe(Matrix.Identity(4), [(0, 0.06), (1.2, 0.07), (1.8, 0.02), (0, 0.0)], 9, [SLIME, SLIME, SLIME], var=0.08,
            rjit=lambda j, k: 0.75 + 0.5 * ((k * 7) % 5) / 4 if j in (1, 2) else 1.0)
    spec = [(0, 0, 1.5, 0.08, 0), (0.85, 0.35, 1.15, 0.25, 0.4), (-0.7, 0.55, 1.25, 0.2, 2.4),
            (-0.2, -0.8, 1.0, 0.35, 4.3), (0.65, -0.6, 1.05, 0.3, 5.5)]
    for (x, y, h, tilt, az) in spec:
        rr = 0.37 * h
        M = (Matrix.Translation((x, y, 0.0)) @ Euler((math.sin(az) * tilt, -math.cos(az) * tilt * -1, 0)).to_matrix().to_4x4())
        prof = [(0, 0.0), (0.55 * rr, 0.04 * h), (0.95 * rr, 0.25 * h), (rr, 0.45 * h), (0.85 * rr, 0.72 * h),
                (0.5 * rr, 0.92 * h), (0, h)]
        bands = b.lathe(M, prof, 8, EGG_G, var=0.0, phase=az)
        for j, fs in enumerate(bands):
            for k, f in enumerate(fs):
                if j <= 1:
                    b.paint([f], EGG_P, 0.06)
                elif j >= 4:
                    b.glow([f], G_FAINT if k % 2 else hx('7ad86a'), 0.05)
                else:
                    b.paint([f], (EGG_G, EGG_P if j == 2 else EGG_G2)[k % 2], 0.05)


def toxic_pool_rim(b):
    r = b.rng
    n = 20
    rows = []
    for (rr, z) in [(2.9, 0.0), (3.2, 0.14), (3.55, 0.1), (3.8, 0.0)]:
        rows.append([b.bm.verts.new(((rr + r.uniform(-0.1, 0.1)) * math.cos(k * TAU / n),
                                     (rr + r.uniform(-0.1, 0.1)) * math.sin(k * TAU / n), z + (r.uniform(0, 0.06) if z else 0)))
                     for k in range(n)])
    bands = [b._bridge(rows[i], rows[i + 1]) for i in range(3)] + [b._bridge(rows[3], rows[0])]
    b.glow([f for f in bands[0] if f], G_GREEN, 0.06)
    b.paint([f for f in bands[1] if f], hx('5cc43a'), 0.06)
    b.paint([f for f in bands[2] + bands[3] if f], SLIME, 0.06)
    for k in range(14):
        a = k * TAU / 14 + r.uniform(-0.12, 0.12)
        rr = r.uniform(3.55, 3.75)
        h = r.uniform(0.3, 0.6)
        fs = b.ico((rr * math.cos(a), rr * math.sin(a), 0.0), (r.uniform(0.35, 0.6), r.uniform(0.3, 0.45), h), 1,
                   (ROCK, ROCK_L, ROCK_D)[k % 3], jitter=0.2, var=0.1, zclamp=0.0, rot=(r.uniform(-0.3, 0.3), 0, a))
        b.paint_where(fs, lambda nn: nn.z > 0.7, RP_L, 0.05)
    for k in range(3):
        a = k * TAU / 3 + 0.5
        b.ico((3.9 * math.cos(a), 3.9 * math.sin(a), 0.0), (0.75, 0.55, 0.55), 1, ROCK_L, jitter=0.15, var=0.08,
              zclamp=0.0, rot=(0, 0, a))
    for k in range(2):   # bubbling goo blisters
        a = k * 2.1 + 1.0
        b.glow(b.ico((3.15 * math.cos(a), 3.15 * math.sin(a), 0.1), (0.18, 0.18, 0.12), 1, G_GREEN, var=0.0, zclamp=0.0),
               hx('c8ff9a'), 0.03)


def stone_platform(b, top, H):
    r = b.rng
    hs = top / 2; ch = 0.18
    sq = [(hs, -hs + ch), (hs, hs - ch), (hs - ch, hs), (-hs + ch, hs), (-hs, hs - ch), (-hs, -hs + ch), (-hs + ch, -hs), (hs - ch, -hs)]
    levels = [(0.0, 1.55, 0.18), (0.32 * H, 1.32, 0.12), (0.62 * H, 1.12, 0.07), (H - 0.18, 1.0, 0.0), (H, 1.0, 0.0)]
    if H > 1.5:
        levels = [(0.0, 1.5, 0.18), (0.25 * H, 1.25, 0.12), (0.55 * H, 1.1, 0.08), (0.8 * H, 1.04, 0.05),
                  (H - 0.18, 1.0, 0.0), (H, 1.0, 0.0)]
    rings = []
    for (z, s, j) in levels:
        rings.append([b.bm.verts.new((x * s * (1 + r.uniform(-j, j)), y * s * (1 + r.uniform(-j, j)), z)) for (x, y) in sq])
    bands = [b._bridge(rings[i], rings[i + 1]) for i in range(len(rings) - 1)]
    bot = b._face(rings[0][::-1]); topf = b._face(rings[-1])
    for i, fs in enumerate(bands):
        b.paint([f for f in fs if f], (RP_D, RP, RP_L, RP, RP_L)[i % 5], 0.07)
    b.paint(bands[-1], MOSS, 0.05)
    b.paint([topf], hx('b2a6c4'), 0.0)
    b.paint([bot], RP_D, 0.0)
    for k in range(3):
        a = k * TAU / 3 + 0.4
        rr = hs * 1.55
        b.ico((rr * math.cos(a), rr * math.sin(a), 0.0), (0.5, 0.4, min(0.45, H * 0.35)), 1, (RP_D, RP, RP_L)[k],
              jitter=0.15, var=0.08, zclamp=0.0, rot=(0, 0, a))
    a = 2.6
    b.crystal((hs * 1.2 * math.cos(a), hs * 1.2 * math.sin(a), 0.05), (math.cos(a) * 0.6, math.sin(a) * 0.6, 0.8),
              0.55, 0.11, [G_CYAN, G_CYAN_L, G_CYAN_D])


PROPS = [
    ("SM_AlienTree_Spiral", tree_spiral, dict(height=9.0)),
    ("SM_AlienTree_Umbrella", tree_umbrella, dict(height=12.0)),
    ("SM_AlienTree_Fan", tree_fan, dict(height=6.0)),
    ("SM_MushroomGiant", mushroom_giant, dict(height=7.0)),
    ("SM_MushroomCluster", mushroom_cluster, {}),
    ("SM_CrystalCluster", crystal_cluster, {}),
    ("SM_CrystalSpire", crystal_spire, dict(height=9.0)),
    ("SM_AlienPlant_Tentacle", tentacle_plant, dict(height=2.5)),
    ("SM_SporePod", spore_pod, {}),
    ("SM_AlienFlowerGlow", flower_glow, dict(height=1.0)),
    ("SM_GrassAlienTuft", grass_tuft, dict(height=0.6)),
    ("SM_BoneRibs", bone_ribs, dict(center_xy=False)),
    ("SM_UFOWreck", ufo_wreck, dict(center_xy=False, zshift=False, zclamp=False)),
    ("SM_AlienMonolith", monolith, dict(height=7.0)),
    ("SM_AlienArch", alien_arch, dict(height=9.0, center_xy=False)),
    ("SM_FarmhouseRuin", farmhouse_ruin, {}),
    ("SM_WindTurbineBroken", wind_turbine, dict(height=24.0)),
    ("SM_EggSac", egg_sac, {}),
    ("SM_ToxicPoolRim", toxic_pool_rim, {}),
    ("SM_StonePlatform", lambda b: stone_platform(b, 2.5, 1.0), {}),
    ("SM_StonePlatformTall", lambda b: stone_platform(b, 2.0, 2.0), {}),
]


def make_materials():
    mat = bpy.data.materials.get(MAT_NAME) or bpy.data.materials.new(MAT_NAME)
    glow = bpy.data.materials.get(GLOW_NAME) or bpy.data.materials.new(GLOW_NAME)
    for m, emit in ((mat, False), (glow, True)):
        try:
            m.use_nodes = True
        except Exception:
            pass
        try:
            nt = m.node_tree
            bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
            vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = "Col"
            nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
            bsdf.inputs['Roughness'].default_value = 0.9
            if emit:
                nt.links.new(vc.outputs['Color'], bsdf.inputs['Emission Color'])
                bsdf.inputs['Emission Strength'].default_value = 5.0
        except Exception as e:
            print("material nodes skipped:", e)
    return mat, glow


def tri_count(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def check_clear(ob, x0, x1, y0, y1, z0, z1):
    """sample every triangle; return number of samples inside the box (should be 0)"""
    me = ob.data; bad = 0
    for p in me.polygons:
        vs = [Vector(me.vertices[i].co) for i in p.vertices]
        for t in range(1, len(vs) - 1):
            a, bb, c = vs[0], vs[t], vs[t + 1]
            for i in range(9):
                for j in range(9 - i):
                    q = a + (bb - a) * (i / 8) + (c - a) * (j / 8)
                    if x0 < q.x < x1 and y0 < q.y < y1 and z0 < q.z < z1:
                        bad += 1
    return bad


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    mats = make_materials()
    objs = []
    for i, (name, fn, kw) in enumerate(PROPS):
        b = Builder(3000 + i)
        fn(b)
        objs.append(b.finish(name, mats, **kw))

    info = {}
    for ob in objs:
        d = ob.dimensions
        zs = [v.co.z for v in ob.data.vertices]
        info[ob.name] = {"tris": tri_count(ob.data), "dims_m": [round(d.x, 2), round(d.y, 2), round(d.z, 2)],
                         "has_glow": bool(ob["has_glow"])}
        print(f"{ob.name:24s} tris={info[ob.name]['tris']:5d} dims={info[ob.name]['dims_m']} "
              f"minz={min(zs):.3f} maxz={max(zs):.3f} glow={ob['has_glow']} mats={[m.name for m in ob.data.materials]}")
    byname = {o.name: o for o in objs}
    print("CLEAR ribs (|y|<2.5, z 0.05..4):", check_clear(byname["SM_BoneRibs"], -7.5, 7.5, -2.5, 2.5, 0.05, 4.0))
    print("CLEAR arch (|x|<4, z 0.05..6):", check_clear(byname["SM_AlienArch"], -4, 4, -5, 5, 0.05, 6.0))
    for n in ("SM_StonePlatform", "SM_StonePlatformTall"):
        zs = sorted(v.co.z for v in byname[n].data.vertices)
        print(n, "top z", zs[-1], "verts at top", sum(1 for z in zs if abs(z - zs[-1]) < 1e-5))
    with open(os.path.join(OUT, "props3_info.json"), "w") as fh:
        json.dump(info, fh, indent=2)

    # ---------- export (all at origin) ----------
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs:
        ob.location = (0, 0, 0); ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "L01_Props3.fbx"), use_selection=True,
                             object_types={'MESH'}, apply_unit_scale=True, mesh_smooth_type='FACE',
                             colors_type='SRGB', add_leaf_bones=False)
    if "--noprev" in sys.argv:
        return
    render_preview(scene, objs, mats)


def bbox_local(o):
    cs = [Vector(c) for c in o.bound_box]
    return (Vector((min(c.x for c in cs), min(c.y for c in cs), min(c.z for c in cs))),
            Vector((max(c.x for c in cs), max(c.y for c in cs), max(c.z for c in cs))))


def render_panel(scene, allo, rows, W, Hh, path, elev=62, gap=3.0, rgap=5.0):
    """Lay out `rows` (names) on the ground, hide the rest, render lit / flat / mask passes.
    Returns label positions in pixels."""
    byname = {o.name: o for o in allo}
    used = {n for row in rows for n in row}
    for o in allo:
        o.hide_render = o.name not in used and o.name != "PV_Ground"
    y = 0.0
    for row in rows:
        depth = max(bbox_local(byname[n])[1].y - bbox_local(byname[n])[0].y for n in row)
        yc = y - depth / 2
        widths = [bbox_local(byname[n])[1].x - bbox_local(byname[n])[0].x for n in row]
        x = -(sum(widths) + gap * (len(row) - 1)) / 2
        for n, w in zip(row, widths):
            lo, hi = bbox_local(byname[n])
            byname[n].location = (x - lo.x, yc - (lo.y + hi.y) / 2, 0)
            x += w + gap
        y -= depth + rgap
    byname["PV_Ground"].location = (0, y / 2, -0.12)
    sh = scene.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'VERTEX'
    sh.show_shadows = True; sh.shadow_intensity = 0.35
    sh.show_cavity = False
    sh.show_object_outline = True; sh.object_outline_color = (0.08, 0.06, 0.1)
    scene.display.light_direction = (0.4, -0.5, 0.8)
    scene.render.resolution_x, scene.render.resolution_y = W, Hh
    cam = scene.camera; cam_d = cam.data
    cam.rotation_euler = (math.radians(elev), 0, math.radians(16))
    bpy.context.view_layer.update()
    R = cam.rotation_euler.to_matrix(); inv = R.transposed()
    pts = []
    for n in used:
        o = byname[n]
        for c in o.bound_box:
            pts.append(inv @ (o.matrix_world @ Vector(c)))
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    cam_d.ortho_scale = max(max(xs) - min(xs), (max(ys) - min(ys)) * W / Hh) * 1.08
    cam.location = R @ Vector((cx, cy - 0.04 * cam_d.ortho_scale / (W / Hh), max(zs) + 80))
    bpy.context.view_layer.update()
    mats = [bpy.data.materials[MAT_NAME], bpy.data.materials[GLOW_NAME]]
    scene.render.filepath = path + "_lit.png"; bpy.ops.render.render(write_still=True)
    sh.light = 'FLAT'; sh.show_shadows = False; sh.show_object_outline = False
    scene.render.filepath = path + "_flat.png"; bpy.ops.render.render(write_still=True)
    keep = [tuple(m.diffuse_color) for m in mats]
    mats[0].diffuse_color = (0, 0, 0, 1); mats[1].diffuse_color = (1, 1, 1, 1)
    sh.color_type = 'MATERIAL'
    scene.render.filepath = path + "_mask.png"; bpy.ops.render.render(write_still=True)
    for m, k in zip(mats, keep):
        m.diffuse_color = k
    from bpy_extras.object_utils import world_to_camera_view
    labels = {}
    for n in used:
        o = byname[n]
        lo, hi = bbox_local(o)
        p = o.location + Vector(((lo.x + hi.x) / 2, lo.y - 0.2, 0))
        v = world_to_camera_view(scene, cam, p)
        labels[n] = [v.x * W, (1 - v.y) * Hh]
    return labels


def render_preview(scene, objs, mats):
    def helper(name, fn, col):
        b = Builder(0); fn(b, col); return b.finish(name, mats)
    hum = lambda b, c: b.box((0, 0, 0.9), (0.45, 0.3, 1.8), c, var=0.0)
    hb = helper("PV_Human_1m8", hum, hx('e0402a'))
    hb2 = helper("PV_Human_1m8_b", hum, hx('e0402a'))
    cb = helper("PV_Car_4m5", lambda b, c: b.box((0, 0, 0.75), (4.5, 1.9, 1.5), c, var=0.0), hx('3a78c8'))
    gm = Builder(0); gm.box((0, 0, -0.05), (500, 400, 0.1), hx('4a4260'), var=0.0)
    g = gm.finish("PV_Ground", mats)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.view_settings.view_transform = 'Standard'
    cam_d = bpy.data.cameras.new("Cam"); cam_d.type = 'ORTHO'; cam_d.clip_end = 1000
    cam = bpy.data.objects.new("Cam", cam_d); scene.collection.objects.link(cam)
    scene.camera = cam
    allo = objs + [hb, hb2, cb, g]
    tmp = "/home/claude/l01/props3"
    panelA = [["SM_WindTurbineBroken", "SM_UFOWreck", "SM_AlienArch", "SM_BoneRibs", "PV_Car_4m5"],
              ["SM_AlienTree_Umbrella", "SM_AlienTree_Spiral", "SM_MushroomGiant", "SM_CrystalSpire",
               "SM_FarmhouseRuin", "SM_AlienTree_Fan", "SM_AlienMonolith", "PV_Human_1m8"]]
    panelB = [["SM_ToxicPoolRim", "SM_CrystalCluster", "SM_EggSac", "SM_MushroomCluster", "SM_SporePod"],
              ["SM_AlienPlant_Tentacle", "SM_AlienFlowerGlow", "SM_GrassAlienTuft", "SM_StonePlatform",
               "SM_StonePlatformTall", "PV_Human_1m8_b"]]
    la = render_panel(scene, allo, panelA, 2600, 1500, tmp + "/pA", elev=64, gap=4.0, rgap=16.0)
    lb = render_panel(scene, allo, panelB, 2600, 1000, tmp + "/pB", elev=64, gap=1.6, rgap=3.5)
    png = os.path.join(OUT, "L01_Props3_preview.png")
    code = r"""
import json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
tmp, out, LA, LB = sys.argv[1], sys.argv[2], json.loads(sys.argv[3]), json.loads(sys.argv[4])
try: f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
except Exception: f = ImageFont.load_default()
names = {'PV_Human_1m8': 'Human 1.8m', 'PV_Human_1m8_b': 'Human 1.8m', 'PV_Car_4m5': 'Car 4.5m'}
def panel(pre, labels, title):
    lit = np.asarray(Image.open(pre + '_lit.png').convert('RGB')).astype(float) / 255
    flat = np.asarray(Image.open(pre + '_flat.png').convert('RGB')).astype(float) / 255
    m = np.asarray(Image.open(pre + '_mask.png').convert('L')).astype(float) / 255
    m = np.clip((m - 0.2) / 0.6, 0, 1)[..., None]
    glow = np.clip(flat * 1.15 + 0.08, 0, 1)
    base = lit * (1 - m) + glow * m
    src = Image.fromarray((glow * m * 255).astype('uint8'))
    b1 = np.asarray(src.filter(ImageFilter.GaussianBlur(9))).astype(float) / 255
    b2 = np.asarray(src.filter(ImageFilter.GaussianBlur(26))).astype(float) / 255
    res = 1 - (1 - base) * (1 - np.clip(b1 * 0.9 + b2 * 0.6, 0, 1))
    im = Image.fromarray((np.clip(res, 0, 1) * 255).astype('uint8'))
    d = ImageDraw.Draw(im)
    for n, (x, y) in labels.items():
        t = names.get(n, n.replace('SM_', ''))
        w = d.textlength(t, font=f); d.rectangle([x-w/2-4, y+4, x+w/2+4, y+32], fill=(20, 16, 28))
        d.text((x-w/2, y+6), t, fill=(255, 255, 255), font=f)
    d.text((20, 14), title, fill=(230, 220, 255), font=f)
    return im
A = panel(tmp + '/pA', LA, 'L01 Props batch 3 - Alien Forest (large props)')
B = panel(tmp + '/pB', LB, 'small props (zoomed)')
out_im = Image.new('RGB', (A.width, A.height + B.height + 6), (12, 10, 18))
out_im.paste(A, (0, 0)); out_im.paste(B, (0, A.height + 6))
out_im.save(out)
"""
    subprocess.run(["python3", "-c", code, tmp, png, json.dumps(la), json.dumps(lb)], check=True)


if __name__ == "__main__":
    main()
