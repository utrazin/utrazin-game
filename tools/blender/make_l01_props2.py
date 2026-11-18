"""L01 cartoon low-poly props, batch 2 (Blender 5.2 / bpy).
Run: python make_l01_props2.py -- [out_dir]
Builds 11 static meshes (ramps, guard rail, rock wall, barrel, roadblock, container,
bus wreck, spike strip, bridge, billboard) with vertex colors ("Col"), a "UVMap"
(cube projection, 1 UV unit = 1 m), one shared material, renders a labelled preview,
exports L01_Props2.fbx and props2_info.json.
"""
import bpy, bmesh, math, random, json, sys, os, subprocess
from mathutils import Matrix, Vector, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "/mnt/user-data/outputs/l01"
os.makedirs(OUT, exist_ok=True)
MAT_NAME = "M_L01_VertexColor"


# ---------------- palette (sRGB 0-1) ----------------
def hx(h):
    h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
WOOD = hx('9a6a3c'); WOOD_L = hx('b58450'); WOOD_D = hx('6d4726'); WOOD_DD = hx('4e321d')
METAL = hx('6f7275'); METAL_D = hx('3a3d42'); METAL_L = hx('9a9da0')
RAIL = hx('8c9093'); RUSTY = hx('8a5a3c')
RUST = hx('a5552a'); RUST_D = hx('7a3a1c'); RUST_L = hx('c06a34')
CONT = hx('b4482a'); CONT_D = hx('86321c'); CONT_L = hx('c85a33')
ROCKW = hx('8a7c6b'); ROCKW_L = hx('a09381'); ROCKW_D = hx('6f6355'); CRACK = hx('3f372f')
BARREL = hx('c0352a'); BARREL_D = hx('8e2219'); YEL = hx('f2c230'); BLK = hx('1e1e1e'); WHITE = hx('f2f0ea')
CONC = hx('b2afa6'); CONC_D = hx('8a877f'); RED = hx('cc2e26')
BUS = hx('d6a83c'); BUS_F = hx('b8913f'); BURN = hx('2a2522'); BURN_B = hx('5a3a22'); GLASS = hx('1f2328')
SPIKE = hx('4a4d52'); SPIKE_L = hx('8d9196')
BOARD = hx('e8e2d0'); POST = hx('5a5d61')


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

    def paint_where(self, faces, pred, col, var=0.0):
        sel = []
        for f in faces:
            f.normal_update()
            if pred(f.normal):
                sel.append(f)
        self.paint(sel, col, var)
        return sel

    # -- primitives (same conventions as batch 1)
    def box(self, center, size, col, rot=(0, 0, 0), var=0.04, taper=None):
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        if taper:
            for v in r['verts']:
                if v.co.z > 0:
                    v.co.x *= taper[0]; v.co.y *= taper[1]
        M = (Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4()
             @ Matrix.Diagonal(Vector((size[0], size[1], size[2], 1))))
        return self._place(r['verts'], M, col, var)

    def cyl(self, base, r1, h, segs, col, r2=None, rot=(0, 0, 0), var=0.04, scale=(1, 1, 1)):
        r2 = r1 if r2 is None else r2
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segs,
                                  radius1=r1, radius2=r2, depth=h)
        verts = r['verts']
        if r2 == 0:  # merge apex
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
        return self.bm.faces.new(out)

    def prism(self, poly, off, col, var=0.04):
        """Closed prism from a planar convex polygon (list of xyz) extruded by vector off."""
        off = Vector(off)
        A = [self.bm.verts.new(Vector(p)) for p in poly]
        B = [self.bm.verts.new(Vector(p) + off) for p in poly]
        n = len(poly)
        fs = [self._face(A[::-1]), self._face(B)]
        for i in range(n):
            j = (i + 1) % n
            fs.append(self._face([A[i], A[j], B[j], B[i]]))
        fs = [f for f in fs if f]
        self.paint(fs, col, var)
        return fs

    def profile_solid(self, xs, zb, zt, y0, y1):
        """Solid swept along X: at each x a rectangle y0..y1, zb(x)..zt(x).
        Collapsed rings (zt==zb) become a shared edge (wedge tip). Returns face dict."""
        rings = []
        for x in xs:
            b0 = self.bm.verts.new((x, y0, zb(x))); b1 = self.bm.verts.new((x, y1, zb(x)))
            if zt(x) - zb(x) < 1e-6:
                t0, t1 = b0, b1
            else:
                t0 = self.bm.verts.new((x, y0, zt(x))); t1 = self.bm.verts.new((x, y1, zt(x)))
            rings.append((b0, b1, t1, t0))
        F = {'top': [], 'bottom': [], 'side0': [], 'side1': [], 'end0': [], 'end1': []}
        for i in range(len(rings) - 1):
            a, c = rings[i], rings[i + 1]
            for key, q in (('bottom', (a[0], c[0], c[1], a[1])), ('side1', (a[1], c[1], c[2], a[2])),
                           ('top', (a[2], c[2], c[3], a[3])), ('side0', (a[3], c[3], c[0], a[0]))):
                f = self._face(q)
                if f:
                    F[key].append(f)
        for key, r in (('end0', rings[0]), ('end1', rings[-1])):
            f = self._face(list(r))
            if f:
                F[key].append(f)
        return F

    # -- finish
    def finish(self, name, mat, center_xy=True):
        bm = self.bm
        bm.verts.ensure_lookup_table()
        xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]; zs = [v.co.z for v in bm.verts]
        off = Vector(((min(xs) + max(xs)) / 2 if center_xy else 0,
                      (min(ys) + max(ys)) / 2 if center_xy else 0, min(zs)))
        for v in bm.verts:
            v.co -= off
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        # UV: cube projection in meters
        uv = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            f.smooth = False
            f.normal_update()
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
        me.materials.append(mat)
        ca = me.color_attributes.get("Col")
        assert ca is not None and ca.data_type == 'BYTE_COLOR' and ca.domain == 'CORNER', name
        me.color_attributes.active_color = ca
        me.color_attributes.render_color_index = me.color_attributes.find("Col")
        me.uv_layers.active = me.uv_layers["UVMap"]
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


# =================== PROPS ===================
def wood_ramp(b, L, W, zfun, n_seg, lip=0.15):
    """Generic plank ramp: smooth surface zfun(x) for x in [-L/2, L/2], closed body,
    metal side lips only at the outer edges."""
    xs = [-L / 2 + L * i / n_seg for i in range(n_seg + 1)]
    hw = W / 2 - 0.03                       # body half width (lips cover the outer 3 cm)
    F = b.profile_solid(xs, lambda x: 0.0, zfun, -hw, hw)
    for i, f in enumerate(F['top']):        # planks across the driving direction
        b.paint([f], (WOOD_L, WOOD, hx('a87646'))[i % 3], 0.05)
    b.paint(F['side0'] + F['side1'], WOOD_D, 0.06)
    b.paint(F['end0'] + F['end1'], WOOD_DD, 0.04)
    b.paint(F['bottom'], WOOD_DD, 0.0)
    # dark nail/support stripes on the sides (paint every 3rd side quad darker)
    for k, f in enumerate(F['side0'] + F['side1']):
        if k % 4 == 0:
            b.paint([f], WOOD_DD, 0.04)
    # metal side lips: 0.12 wide, from 5 cm below surface to `lip` above it, at y edges only
    for s in (-1, 1):
        y0, y1 = (W / 2 - 0.12, W / 2) if s > 0 else (-W / 2, -W / 2 + 0.12)
        G = b.profile_solid(xs, lambda x: max(0.0, zfun(x) - 0.05), lambda x: zfun(x) + lip, y0, y1)
        allf = sum(G.values(), [])
        b.paint(allf, RAIL, 0.05)
        b.paint(G['top'], METAL_L, 0.03)
        for k, f in enumerate(G['side0'] + G['side1']):
            if k % 5 == 2:
                b.paint([f], RUSTY, 0.05)


def ramp(b):
    L, H = 7.0, 1.8
    def z(x):  # smooth, steeper at the end: slope 0.09 at start -> 0.42 at the lip
        t = (x + L / 2) / L
        return H * (0.35 * t + 0.65 * t * t)
    wood_ramp(b, L, 5.0, z, 20)


def ramp_landing(b):
    L, H = 9.0, 1.2
    def z(x):  # gentle descent, flattening out to the ground at +X
        u = 1.0 - (x + L / 2) / L
        return H * (0.45 * u + 0.55 * u * u)
    wood_ramp(b, L, 5.5, z, 20)


def guard_rail(b):
    r = b.rng
    # posts (back), spacer blocks, W-beam (front, -Y). total depth 0.4 (y -0.2..0.2)
    for x in (-4.0, -2.0, 0.0, 2.0, 4.0):
        x = max(-3.94, min(3.94, x))
        b.box((x, 0.1, 0.45), (0.12, 0.2, 0.9), METAL_D, var=0.05)
        b.box((x, -0.05, 0.65), (0.1, 0.1, 0.3), METAL, var=0.05)
    # W-beam centre line zigzag in YZ (front peaks at y=-0.2)
    zig = [(-0.11, 0.8), (-0.19, 0.725), (-0.11, 0.65), (-0.19, 0.575), (-0.11, 0.5)]
    t = 0.012
    xs = [-4.0, -2.0, 0.0, 2.0, 4.0]
    for i in range(len(xs) - 1):
        for (y0, z0), (y1, z1) in zip(zig[:-1], zig[1:]):
            poly = [(xs[i], y0, z0), (xs[i], y1, z1), (xs[i], y1 + t, z1), (xs[i], y0 + t, z0)]
            col = RAIL if r.random() > 0.25 else RUSTY
            fs = b.prism(poly, (xs[i + 1] - xs[i], 0, 0), col, var=0.07)
    # bolt heads on the beam at each post
    for x in (-3.94, -2.0, 0.0, 2.0, 3.94):
        b.box((x, -0.2, 0.65), (0.06, 0.03, 0.06), METAL_D, var=0.0)


def rock_wall(b):
    r = b.rng
    Lx, Ty, H = 12.0, 3.0, 8.0
    res = bmesh.ops.create_cube(b.bm, size=1.0)
    verts = res['verts']
    bmesh.ops.subdivide_edges(b.bm, edges=list({e for v in verts for e in v.link_edges}),
                              cuts=4, use_grid_fill=True)
    verts = list({v for v in b.bm.verts})
    for v in verts:
        x, y, z = v.co
        X, Y, Z = x * Lx, y * Ty, (z + 0.5) * H
        top = z > 0.499; bot = z < -0.499
        endx = abs(x) > 0.499
        if not bot:
            Y += (r.random() - 0.5) * 0.9 * (1 if abs(y) > 0.499 else 0.4)
            if not top:
                Z += (r.random() - 0.5) * 1.0
            if not endx:
                X += (r.random() - 0.5) * 0.9
        else:
            Y += (r.random() - 0.5) * 0.3
            if not endx:
                X += (r.random() - 0.5) * 0.5
        if top:
            Z = H - r.random() * 1.6
            Y *= 0.75                      # narrower crest
        elif not bot:
            Y *= 1.0 - 0.18 * (Z / H)      # slight inward lean
        v.co = Vector((X, Y, max(0.0, Z)))
    bmesh.ops.triangulate(b.bm, faces=list({f for v in verts for f in v.link_faces}))
    body = list({f for v in verts for f in v.link_faces})
    for f in body:
        f.normal_update()
        zc = f.calc_center_median().z
        band = int(zc / 1.6) % 3
        col = (ROCKW, ROCKW_L, ROCKW_D)[band]
        rr = r.random()
        if rr < 0.16:
            col = CRACK
        elif f.normal.z > 0.6:
            col = ROCKW_L
        b.paint([f], col, 0.08)
    # chunky boulders protruding (keep inside x +-6, y within ~ +-2)
    for (x, y, z, sx, sy, sz) in [(-4.0, -1.2, 1.3, 2.2, 0.7, 1.6), (1.5, -1.25, 0.9, 2.4, 0.6, 1.3),
                                  (4.3, 1.2, 1.6, 1.6, 0.6, 1.9), (-1.5, 1.2, 1.2, 2.0, 0.6, 1.5),
                                  (-2.8, -0.2, 6.6, 1.9, 0.9, 1.3), (2.8, 0.1, 6.3, 2.2, 0.9, 1.4),
                                  (0.0, -0.95, 4.2, 1.6, 0.55, 1.2)]:
        fs = b.ico((x, y, z), (sx, sy, sz), 2, ROCKW_L if r.random() > 0.5 else ROCKW, jitter=0.15,
                   var=0.1, zclamp=0.0, rot=(0, 0, r.random()))
        for f in fs:
            if r.random() < 0.15:
                b.paint([f], CRACK, 0.05)
    # clip x to +-6 so segments tile
    zmax = max(v.co.z for v in b.bm.verts)
    for v in b.bm.verts:
        v.co.x = max(-6.0, min(6.0, v.co.x))
        v.co.z *= H / zmax           # exactly 8 m tall
    ys = [v.co.y for v in b.bm.verts]
    yc, ysz = (max(ys) + min(ys)) / 2, max(ys) - min(ys)
    for v in b.bm.verts:             # keep it ~3.4 m thick overall (3 m core + chunks)
        v.co.y = (v.co.y - yc) * 3.4 / ysz


def explosive_barrel(b):
    f = b.cyl((0, 0, 0), 0.3, 0.9, 12, BARREL, var=0.05)
    b.paint_where(f, lambda n: n.z > 0.9, BARREL_D, 0.0)
    b.paint_where(f, lambda n: n.z < -0.9, BLK, 0.0)
    for z in (0.17, 0.71):  # ribs
        b.cyl((0, 0, z), 0.305, 0.04, 12, BARREL_D, var=0.03)
    band = b.cyl((0, 0, 0.36), 0.307, 0.2, 12, YEL, var=0.0)
    sides = []
    for fa in band:
        fa.normal_update()
        if abs(fa.normal.z) < 0.5:
            sides.append(fa)
    sides.sort(key=lambda fa: math.atan2(fa.calc_center_median().y, fa.calc_center_median().x))
    for i, fa in enumerate(sides):
        b.paint([fa], YEL if i % 2 else BLK, 0.0)
    # bung + flame-ish white mark on both -Y and +Y faces
    for s in (-1, 1):
        y = s * 0.298
        flame = [(0.0, 0.8), (0.065, 0.67), (0.0, 0.6), (-0.065, 0.67)]  # white diamond-flame
        poly = [(x, y, z) for x, z in flame]
        b.prism(poly, (0, s * 0.012, 0), WHITE, var=0.0)


def roadblock(b):
    L = 3.0
    def w(z):  # half width of the upper slope
        return 0.21 + (0.1 - 0.21) * (z - 0.32) / (0.8 - 0.32)
    lower = [(-0.3, 0.0), (0.3, 0.0), (0.3, 0.08), (w(0.4), 0.4), (-w(0.4), 0.4), (-0.3, 0.08)]
    b.prism([(-L / 2, y, z) for y, z in lower], (L, 0, 0), CONC, var=0.05)
    # red/white stripes on the top half 0.4..0.8
    n = 6
    for i in range(n):
        x0 = -L / 2 + L * i / n
        poly = [(x0, -w(0.4), 0.4), (x0, w(0.4), 0.4), (x0, 0.1, 0.8), (x0, -0.1, 0.8)]
        b.prism(poly, (L / n, 0, 0), RED if i % 2 == 0 else WHITE, var=0.03)
    # forklift slot marks on base (dark, flush)
    for x in (-0.8, 0.8):
        for s in (-1, 1):
            b.box((x, s * 0.302, 0.05), (0.35, 0.006, 0.06), CONC_D, var=0.0)


def container(b):
    r = b.rng
    Lx, Wy, H = 6.0, 2.4, 2.6
    b.box((0, 0, H / 2), (Lx - 0.12, Wy - 0.12, H - 0.1), CONT, var=0.05)
    # frame: corner posts + top/bottom rails
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((sx * (Lx / 2 - 0.08), sy * (Wy / 2 - 0.08), H / 2), (0.16, 0.16, H), CONT_D, var=0.03)
    for z in (0.08, H - 0.08):
        for sy in (-1, 1):
            b.box((0, sy * (Wy / 2 - 0.08), z), (Lx - 0.3, 0.16, 0.16), CONT_D, var=0.03)
        for sx in (-1, 1):
            b.box((sx * (Lx / 2 - 0.08), 0, z), (0.16, Wy - 0.3, 0.16), CONT_D, var=0.03)
    # corrugation ridges (trapezoid prisms, vertical) on long sides and -X end
    zr0, zr1 = 0.16, H - 0.16
    def ridge_y(x, sy):
        y = sy * (Wy / 2 - 0.06)
        d = sy * 0.05
        poly = [(x - 0.17, y, zr0), (x + 0.17, y, zr0), (x + 0.1, y + d, zr0), (x - 0.1, y + d, zr0)]
        col = CONT if r.random() > 0.2 else (RUST_D if r.random() > 0.5 else CONT_L)
        b.prism(poly, (0, 0, zr1 - zr0), col, var=0.05)
    n = 8
    for i in range(n):
        x = -Lx / 2 + 0.45 + (Lx - 0.9) * i / (n - 1)
        ridge_y(x, 1); ridge_y(x, -1)
    for y in (-0.7, 0.0, 0.7):
        xq = -(Lx / 2 - 0.06)
        poly = [(xq, y - 0.17, zr0), (xq, y + 0.17, zr0), (xq - 0.05, y + 0.1, zr0), (xq - 0.05, y - 0.1, zr0)]
        b.prism(poly, (0, 0, zr1 - zr0), CONT, var=0.05)
    # doors on +X end
    xd = Lx / 2 - 0.05
    for s in (-1, 1):
        b.box((xd, s * 0.55, H / 2), (0.04, 1.06, H - 0.36), CONT_L, var=0.04)
        for yy in (s * 0.3, s * 0.8):  # lock bars
            b.box((xd + 0.03, yy, H / 2), (0.03, 0.04, H - 0.4), METAL_D, var=0.0)
        b.box((xd + 0.04, s * 0.3, 1.2), (0.04, 0.1, 0.2), METAL, var=0.0)  # handle
    b.box((xd + 0.0, 0, H / 2), (0.05, 0.03, H - 0.36), CONT_D, var=0.0)  # door seam
    # rust patches on the roof (paint, no extra geometry)
    for f in b.bm.faces:
        f.normal_update()
        if f.normal.z > 0.9 and r.random() < 0.35:
            b.paint([f], RUST_D, 0.06)


def bus_wreck(b):
    r = b.rng
    Lx, Wy, H = 10.0, 2.5, 3.0
    hw = Wy / 2 - 0.04
    xb0, xb1 = -5.0, 3.7      # passenger body
    xh1 = 5.0                 # hood end
    zc, zw0, zw1, zr = 0.45, 1.55, 2.45, 2.75
    # chassis / undercarriage (dark, no wheels)
    b.box((0, 0, zc / 2), (Lx - 0.6, Wy - 0.6, zc), BURN, var=0.05)
    def bus_col():
        p = r.random()
        return BURN if p < 0.18 else (BURN_B if p < 0.3 else (BUS_F if p < 0.55 else BUS))
    # lower body in panels along X
    n = 8
    for i in range(n):
        x0 = xb0 + (xb1 - xb0) * i / n; x1 = xb0 + (xb1 - xb0) * (i + 1) / n
        f = b.box(((x0 + x1) / 2, 0, (zc + zw0) / 2), (x1 - x0, 2 * hw, zw0 - zc), bus_col(), var=0.05)
    # window band: dark inset core + pillars
    b.box(((xb0 + xb1) / 2, 0, (zw0 + zw1) / 2), (xb1 - xb0 - 0.1, 2 * hw - 0.1, zw1 - zw0), GLASS, var=0.04)
    nw = 9
    for i in range(nw + 1):
        x = xb0 + 0.12 + (xb1 - xb0 - 0.24) * i / nw
        for s in (-1, 1):
            b.box((x, s * (hw - 0.04), (zw0 + zw1) / 2), (0.18, 0.08, zw1 - zw0), bus_col(), var=0.05)
    # end pillars across the front/back (windshield and rear window stay dark)
    for x in (xb0 + 0.04, xb1 - 0.04):
        for y in (-hw + 0.1, hw - 0.1):
            b.box((x, y, (zw0 + zw1) / 2), (0.08, 0.2, zw1 - zw0), bus_col(), var=0.05)
        b.box((x, 0, (zw0 + zw1) / 2), (0.08, 0.12, zw1 - zw0), BUS_F, var=0.05)
    # upper band + roof (slightly crumpled)
    for i in range(4):
        x0 = xb0 + (xb1 - xb0) * i / 4; x1 = xb0 + (xb1 - xb0) * (i + 1) / 4
        b.box(((x0 + x1) / 2, 0, (zw1 + zr) / 2), (x1 - x0, 2 * hw, zr - zw1), bus_col(), var=0.05)
        b.box(((x0 + x1) / 2, 0, (zr + H) / 2 - 0.02 * (i == 2)), (x1 - x0, 2 * hw - 0.1, H - zr),
              BURN if i in (1, 2) else BUS_F, taper=(1.0, 0.82), var=0.06)
    # hood
    b.box(((xb1 + xh1) / 2, 0, (zc + 1.5) / 2), (xh1 - xb1, 2 * hw - 0.3, 1.5 - zc), BUS, taper=(0.92, 0.9), var=0.05)
    hood = b.box(((xb1 + xh1) / 2, 0, 1.5), (xh1 - xb1 - 0.1, 2 * hw - 0.55, 0.06), BURN, var=0.05)
    b.box((xh1 - 0.05, 0, 0.6), (0.14, Wy - 0.2, 0.22), METAL_D, var=0.03)   # bumper
    b.box((xb0 - 0.0 + 0.05, 0, 0.6), (0.14, Wy - 0.2, 0.22), METAL_D, var=0.03)
    for y in (-0.8, 0.8):
        b.box((xh1 - 0.08, y, 1.05), (0.06, 0.25, 0.18), GLASS, var=0.0)  # dead headlights
    # black rub rails along sides
    for z in (0.75, 1.15):
        for s in (-1, 1):
            b.box(((xb0 + xb1) / 2, s * (Wy / 2 - 0.025), z), (xb1 - xb0 - 0.1, 0.05, 0.06), BLK, var=0.0)
    # door outline on +Y? (school bus door on right side = -Y when driving +X)
    b.box((xb1 - 0.55, -(hw + 0.006), (zc + zw1) / 2 + 0.1), (0.7, 0.012, zw1 - zc - 0.2), GLASS, var=0.0)
    # burned soot patches on sides and roof
    for _ in range(8):
        s = r.choice((-1, 1))
        b.box((r.uniform(-4.5, 3.2), s * (hw + 0.006), r.uniform(0.7, 2.4)), (r.uniform(0.6, 1.4), 0.012, r.uniform(0.4, 0.9)),
              BURN, var=0.08)


def spike_strip(b):
    r = b.rng
    n = 8
    L = 4.0
    for i in range(n):
        x0 = -L / 2 + L * i / n
        b.box((x0 + L / n / 2, 0, 0.025), (L / n - 0.02, 0.5, 0.05), SPIKE if i % 2 else METAL_D, var=0.05)
        b.box((x0 + L / n / 2, 0, 0.055), (L / n - 0.08, 0.08, 0.01), SPIKE_L, var=0.0)  # hinge spine
    for i in range(16):
        x = -L / 2 + 0.125 + i * 0.25
        for y in (-0.15, 0.15):
            b.cyl((x, y + (0.05 if i % 2 else -0.05) * 0, 0.05), 0.035, 0.1, 4, SPIKE_L, r2=0,
                  rot=(0, 0, math.pi / 4), var=0.05)


def bridge_planks(b):
    r = b.rng
    Lx, Wy = 14.0, 6.0
    # two beams underneath (z 0..0.2)
    for y in (-1.8, 1.8):
        b.box((0, y, 0.1), (Lx - 0.2, 0.45, 0.2), WOOD_DD, var=0.04)
    # deck planks across Y, flat top at z=0.6 (0.2..0.6)
    n = 28
    for i in range(n):
        x0 = -Lx / 2 + Lx * i / n
        col = (WOOD_L, WOOD, hx('a87646'), WOOD_L)[r.randrange(4)]
        b.box((x0 + Lx / n / 2, 0, 0.4), (Lx / n, Wy - 0.6, 0.4), col, var=0.04)
    # side curbs 0.3 tall on the deck edges
    for s in (-1, 1):
        b.box((0, s * (Wy / 2 - 0.15), 0.45), (Lx, 0.3, 0.9 - 0.0), WOOD_D, var=0.05)
        for x in (-6.5, -3.25, 0.0, 3.25, 6.5):  # metal straps
            b.box((x, s * (Wy / 2 - 0.15), 0.75), (0.1, 0.3, 0.3), METAL_D, var=0.0)


def zombie_billboard(b):
    BW, BH, Z0 = 4.0, 2.5, 2.0
    for x in (-1.4, 1.4):
        b.box((x, 0.12, 2.3), (0.16, 0.16, 4.6), POST, var=0.05)
        b.box((x, 0.12, 0.05), (0.4, 0.4, 0.1), CONC_D, var=0.0)
    b.box((0, 0, Z0 + BH / 2), (BW, 0.08, BH), BOARD, var=0.03)
    b.box((0, 0.0, Z0 + BH + 0.03), (BW + 0.1, 0.12, 0.06), METAL_D, var=0.0)
    b.box((0, 0.0, Z0 - 0.03), (BW + 0.1, 0.12, 0.06), METAL_D, var=0.0)
    yf = -0.045   # front face decals (-Y)
    # hazard stripes band at bottom
    n = 8
    for i in range(n):
        x = -BW / 2 + BW * (i + 0.5) / n
        b.box((x, yf, Z0 + 0.2), (BW / n, 0.012, 0.3), RED if i % 2 == 0 else BLK, var=0.0)
    b.box((0, yf, Z0 + BH - 0.15), (BW, 0.012, 0.18), RED, var=0.0)
    # skull: cranium (octagon) + jaw + eyes + nose + crossbones
    cx, cz = 0.0, Z0 + 1.45
    oct_ = [(cx + 0.55 * math.cos(a), yf - 0.01, cz + 0.5 * math.sin(a)) for a in
            [math.pi / 8 + k * math.pi / 4 for k in range(8)]]
    b.prism(oct_[::-1], (0, 0.015, 0), RED, var=0.0)
    b.box((cx, yf - 0.012, cz - 0.55), (0.6, 0.02, 0.3), RED, var=0.0)
    for x in (-0.22, 0.22):
        b.box((x, yf - 0.018, cz + 0.02), (0.2, 0.012, 0.22), BLK, rot=(0, math.pi / 4, 0), var=0.0)
    b.box((cx, yf - 0.018, cz - 0.25), (0.1, 0.012, 0.12), BLK, var=0.0)
    for a in (0.55, -0.55):
        b.box((cx, yf - 0.005, cz - 0.15), (1.9, 0.01, 0.16), RED, rot=(0, a, 0), var=0.0)


PROPS = [
    ("SM_Ramp", ramp), ("SM_RampLanding", ramp_landing), ("SM_GuardRail", guard_rail),
    ("SM_RockWall", rock_wall), ("SM_ExplosiveBarrel", explosive_barrel), ("SM_Roadblock", roadblock),
    ("SM_Container", container), ("SM_BusWreck", bus_wreck), ("SM_SpikeStrip", spike_strip),
    ("SM_BridgePlanks", bridge_planks), ("SM_ZombieBillboard", zombie_billboard),
]
# pivot conventions: ramps/bridge/rockwall centred on base footprint (default)


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
    return b.finish(name, bpy.data.materials[MAT_NAME])


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    mat = make_material()
    objs = []
    for i, (name, fn) in enumerate(PROPS):
        b = Builder(2000 + i)
        fn(b)
        objs.append(b.finish(name, mat))

    info = {}
    for ob in objs:
        d = ob.dimensions
        info[ob.name] = {"tris": tri_count(ob.data), "dims_m": [round(d.x, 3), round(d.y, 3), round(d.z, 3)]}
        print(f"{ob.name:20s} tris={info[ob.name]['tris']:5d} dims={info[ob.name]['dims_m']}")
    with open(os.path.join(OUT, "props2_info.json"), "w") as fh:
        json.dump(info, fh, indent=2)

    # ---------- export (all at origin) ----------
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs:
        ob.location = (0, 0, 0); ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "L01_Props2.fbx"), use_selection=True,
                             object_types={'MESH'}, apply_unit_scale=True, mesh_smooth_type='FACE',
                             colors_type='SRGB', add_leaf_bones=False)

    # ---------- preview layout ----------
    def human(b, col):
        b.box((0, 0, 0.9), (0.45, 0.3, 1.8), col, var=0.0)
    def carbox(b, col):
        b.box((0, 0, 0.75), (4.5, 1.9, 1.5), col, var=0.0)
    hb = helper_mesh("PV_Human_1m8", human, hx('e0402a'))
    cb = helper_mesh("PV_Car_4m5", carbox, hx('3a78c8'))
    rows = [["SM_RockWall", "SM_BridgePlanks", "SM_BusWreck"],
            ["SM_Ramp", "SM_RampLanding", "SM_Container", "SM_ZombieBillboard"],
            ["SM_GuardRail", "SM_Roadblock", "SM_SpikeStrip", "SM_ExplosiveBarrel", "PV_Human_1m8", "PV_Car_4m5"]]
    byname = {o.name: o for o in objs + [hb, cb]}
    gap = 2.5
    y = 0.0
    for row in rows:
        widths = [byname[n].dimensions.x for n in row]
        depth = max(byname[n].dimensions.y for n in row)
        x = -(sum(widths) + gap * (len(row) - 1)) / 2
        for n, w in zip(row, widths):
            byname[n].location = (x + w / 2, y, 0)
            x += w + gap
        y -= depth + 4.0   # rows come towards the camera (-Y)

    def ground(b, col):
        b.box((0, 0, -0.05), (140, 110, 0.1), col, var=0.0)
    g = helper_mesh("PV_Ground", ground, hx('9a8a68'))
    g.location = (0, y / 2, -0.1)

    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.view_settings.view_transform = 'Standard'
    sh = scene.display.shading
    sh.light = 'STUDIO'
    try:
        sh.color_type = 'VERTEX'
    except Exception:
        sh.color_type = 'ATTRIBUTE'
    sh.show_shadows = True
    sh.shadow_intensity = 0.3
    sh.show_cavity = False
    sh.show_object_outline = True
    sh.object_outline_color = (0.1, 0.1, 0.1)
    scene.display.light_direction = (0.4, -0.5, 0.8)
    scene.render.resolution_x, scene.render.resolution_y = 2400, 1500
    cam_d = bpy.data.cameras.new("Cam"); cam_d.type = 'ORTHO'
    cam = bpy.data.objects.new("Cam", cam_d); scene.collection.objects.link(cam)
    scene.camera = cam
    cam.rotation_euler = (math.radians(58), 0, math.radians(20))
    bpy.context.view_layer.update()
    R = cam.rotation_euler.to_matrix(); inv = R.transposed()
    pts = []
    for ob in objs + [hb, cb]:
        for c in ob.bound_box:
            pts.append(inv @ (ob.matrix_world @ Vector(c)))
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    aspect = scene.render.resolution_x / scene.render.resolution_y
    cam_d.ortho_scale = max(max(xs) - min(xs), (max(ys) - min(ys)) * aspect) * 1.08
    cam.location = R @ Vector((cx, cy - 0.5, max(zs) + 50))
    cam_d.clip_end = 500
    png = os.path.join(OUT, "L01_Props2_preview.png")
    scene.render.filepath = png
    bpy.ops.render.render(write_still=True)

    from bpy_extras.object_utils import world_to_camera_view
    labels = {}
    for ob in objs + [hb, cb]:
        p = ob.location + Vector((0, -ob.dimensions.y / 2 - 0.3, 0))
        v = world_to_camera_view(scene, cam, p)
        labels[ob.name] = [v.x * scene.render.resolution_x, (1 - v.y) * scene.render.resolution_y]
    # labels drawn with system python3 + PIL (bpy python has no PIL)
    code = r'''
import json, sys
from PIL import Image, ImageDraw, ImageFont
p, labels = sys.argv[1], json.loads(sys.argv[2])
im = Image.open(p).convert('RGB'); d = ImageDraw.Draw(im)
try: f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
except Exception: f = ImageFont.load_default()
names = {'PV_Human_1m8': 'Human 1.8m', 'PV_Car_4m5': 'Car 4.5m'}
for n, (x, y) in labels.items():
    t = names.get(n, n.replace('SM_', ''))
    w = d.textlength(t, font=f); d.rectangle([x-w/2-4, y+4, x+w/2+4, y+32], fill=(20, 20, 20))
    d.text((x-w/2, y+6), t, fill=(255, 255, 255), font=f)
im.save(p)
'''
    try:
        subprocess.run(["python3", "-c", code, png, json.dumps(labels)], check=True)
    except Exception as e:
        print("labeling skipped:", e)


if __name__ == "__main__":
    main()
