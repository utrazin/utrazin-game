# make_car.py - SM_Car_AlienBuggy (chassis body only, no wheels)
#               + SM_Car_AlienBuggy_SteeringWheel (volante separado: o jogo gira ele com o input)
# Run: /home/claude/bpy52/bin/python make_car.py -- [out_dir]
import sys, math, random
import bpy, bmesh
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "/mnt/user-data/outputs/car"
FBX = OUT + "/SM_Car_AlienBuggy.fbx"
FBX_WHEEL = OUT + "/SM_Car_AlienBuggy_SteeringWheel.fbx"
PNG = OUT + "/SM_Car_AlienBuggy_preview.png"

# ---------------- palette (sRGB) ----------------
C = dict(
    ORANGE=(0.90, 0.46, 0.14), SAND=(0.90, 0.72, 0.44), SAND_D=(0.72, 0.55, 0.32),
    DARK=(0.17, 0.17, 0.19), METAL=(0.38, 0.39, 0.41), STEEL=(0.58, 0.58, 0.60),
    RUST=(0.52, 0.22, 0.09), PURPLE=(0.50, 0.22, 0.78), PURPLE_D=(0.28, 0.12, 0.46),
    RUBBER=(0.08, 0.08, 0.09), LEATHER=(0.42, 0.24, 0.14), BLACK=(0.04, 0.04, 0.05),
    G_HEAD=(1.00, 0.93, 0.55), G_CELL=(0.45, 1.00, 0.30), G_NITRO=(0.20, 0.75, 1.00),
)
NAMES = list(C.keys())
GLOW = {"G_HEAD", "G_CELL", "G_NITRO"}

bm = bmesh.new()
CID = bm.faces.layers.int.new("cid")


def tag(faces, col):
    i = NAMES.index(col)
    for f in faces:
        f[CID] = i
        f.material_index = 1 if col in GLOW else 0


def bevel_part(verts, faces, col, off):
    if off <= 0:
        return
    edges = list({e for v in verts for e in v.link_edges})
    res = bmesh.ops.bevel(bm, geom=list(verts) + edges, offset=off, offset_type='OFFSET',
                          segments=1, profile=0.5, affect='EDGES', clamp_overlap=True)
    tag(res["faces"], col)


def faces_of(verts):
    return list({f for v in verts for f in v.link_faces})


def box(lo, hi, col, bev=0.0, rot=None):
    lo, hi = Vector(lo), Vector(hi)
    c = (lo + hi) / 2
    s = hi - lo
    M = Matrix.Translation(c) @ (rot.to_4x4() if rot else Matrix()) @ Matrix.Diagonal((s.x, s.y, s.z, 1))
    v = bmesh.ops.create_cube(bm, size=1.0, matrix=M)["verts"]
    tag(faces_of(v), col)
    bevel_part(v, None, col, min(bev, min(s) * 0.45))
    return v


def hull(points, col, bev=0.0):
    vs = [bm.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    junk = [g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)]
    if junk:
        bmesh.ops.delete(bm, geom=junk, context='VERTS')
    vs = [v for v in vs if v.is_valid]
    tag(faces_of(vs), col)
    bevel_part(vs, None, col, bev)
    return vs


def align(p0, p1):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    q = d.normalized().to_track_quat('Z', 'Y')
    return Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4(), d.length


def cyl(p0, p1, r, col, seg=12, r2=None):
    M, L = align(p0, p1)
    v = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                              radius1=r, radius2=(r if r2 is None else r2), depth=L, matrix=M)["verts"]
    tag(faces_of(v), col)
    return v


def sphere(c, r, col, u=8, vv=6):
    v = bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=vv, radius=r,
                                  matrix=Matrix.Translation(Vector(c)))["verts"]
    tag(faces_of(v), col)
    return v


def torus(c, axis, R, r, col, nu=20, nv=8):
    M, _ = align(Vector(c) - Vector(axis) * 0.01, Vector(c) + Vector(axis) * 0.01)
    rows = []
    for i in range(nu):
        a = 2 * math.pi * i / nu
        row = []
        for j in range(nv):
            b = 2 * math.pi * j / nv
            rr = R + r * math.cos(b)
            row.append(bm.verts.new(M @ Vector((rr * math.cos(a), rr * math.sin(a), r * math.sin(b)))))
        rows.append(row)
    fs = []
    for i in range(nu):
        for j in range(nv):
            a, b = rows[i][j], rows[(i + 1) % nu][j]
            cc, d = rows[(i + 1) % nu][(j + 1) % nv], rows[i][(j + 1) % nv]
            fs.append(bm.faces.new((a, b, cc, d)))
    tag(fs, col)


def tube_path(pts, r, col, seg=10, joints=True, jcol=None):
    for a, b in zip(pts[:-1], pts[1:]):
        cyl(a, b, r, col, seg)
    if joints:
        for p in pts[1:-1]:
            sphere(p, r * 1.05, jcol or col)


def arch(xa, ys, r_in, r_out, a0, a1, col, n=12, zc=0.45, trim=None):
    """fender arch around wheel axle xa, y range ys, angles in degrees (0 = +X)."""
    st = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        ca, sa = math.cos(a), math.sin(a)
        q = []
        for (r, y) in ((r_in, ys[0]), (r_in, ys[1]), (r_out, ys[1]), (r_out, ys[0])):
            q.append(bm.verts.new((xa + r * ca, y, zc + r * sa)))
        st.append(q)
    fs = []
    for i in range(n):
        for k in range(4):
            fs.append(bm.faces.new((st[i][k], st[i][(k + 1) % 4], st[i + 1][(k + 1) % 4], st[i + 1][k])))
    fs.append(bm.faces.new(st[0][::-1]))
    fs.append(bm.faces.new(st[-1]))
    tag(fs, col)


def rivets(x0, x1, y, z0, z1, col="METAL", side=1, s=0.025):
    for x in (x0, x1):
        for z in (z0, z1):
            box((x - s, y - 0.004 * side if side > 0 else y - s * 0.6, z - s),
                (x + s, y + s * 0.6 if side > 0 else y + 0.004, z + s), col)


# =====================================================================
#                          BUILD THE BUGGY
# =====================================================================
FA, RA = 1.45, -1.35

# ---- frame / skid ----
box((-1.95, -0.62, 0.35), (1.97, 0.62, 0.52), "DARK", 0.04)
for y in (-0.45, 0.45):  # frame rails
    box((-1.9, y - 0.06, 0.38), (1.92, y + 0.06, 0.56), "METAL", 0.02)

# ---- cabin tub ----
box((-0.80, -0.96, 0.50), (0.90, 0.96, 0.64), "DARK", 0.03)            # floor
for s in (-1, 1):
    y0, y1 = sorted((s * 0.80, s * 0.98))
    box((-0.80, y0, 0.50), (0.90, y1, 1.04), "ORANGE", 0.04)           # side walls
    yr0, yr1 = sorted((s * 0.78, s * 1.00))
    box((-0.82 + 0.03, yr0, 1.02), (0.92 - 0.03, yr1, 1.09), "METAL", 0.02)  # top rail
    # sand lower stripe
    ys0, ys1 = sorted((s * 0.975, s * 0.99))
    box((-0.78, ys0, 0.54), (0.88, ys1, 0.66), "SAND", 0.0)
    # purple alien armor plate + rivets
    yp0, yp1 = sorted((s * 0.97, s * 1.005))
    hull([(-0.55, yp0, 0.70), (-0.55, yp1, 0.70), (0.55, yp0, 0.70), (0.55, yp1, 0.70),
          (-0.45, yp0, 0.95), (-0.45, yp1, 0.95), (0.42, yp0, 0.95), (0.42, yp1, 0.95)],
         "PURPLE_D", 0.01)
    yg0, yg1 = sorted((s * 1.0, s * 1.02))
    box((-0.38, yg0, 0.80), (0.30, yg1, 0.84), "PURPLE", 0.0)           # alien vein strip
    box((0.30, yg0, 0.76), (0.40, yg1, 0.88), "PURPLE", 0.0)
    for x in (-0.48, 0.47):
        for z in (0.74, 0.91):
            yy0, yy1 = sorted((s * 1.0, s * 1.025))
            box((x - 0.022, yy0, z - 0.022), (x + 0.022, yy1, z + 0.022), "STEEL")
    # rust patch
    yq0, yq1 = sorted((s * 0.978, s * 0.986))
    box((0.58, yq0, 0.70), (0.80, yq1, 0.86), "RUST")
box((-0.80, -0.96, 0.50), (-0.66, 0.96, 1.10), "ORANGE", 0.04)          # rear wall
box((0.72, -0.96, 0.50), (0.90, 0.96, 1.08), "DARK", 0.03)              # firewall
hull([(0.60, -0.80, 1.04), (0.60, 0.80, 1.04), (0.80, -0.80, 1.04), (0.80, 0.80, 1.04),
      (0.66, -0.78, 1.16), (0.66, 0.78, 1.16), (0.80, -0.78, 1.18), (0.80, 0.78, 1.18)],
     "DARK", 0.02)                                                       # dash
box((0.64, -0.12, 1.10), (0.68, 0.12, 1.16), "PURPLE", 0.0)            # alien dash screen
for y in (-0.35, 0.35):
    cyl((0.655, y, 1.11), (0.645, y, 1.15), 0.05, "STEEL", 10)          # gauges

# ---- driver seat ----
box((-0.52, -0.26, 0.62), (-0.08, 0.26, 0.76), "LEATHER", 0.04)
hull([(-0.62, -0.26, 0.70), (-0.62, 0.26, 0.70), (-0.48, -0.26, 0.70), (-0.48, 0.26, 0.70),
      (-0.72, -0.24, 1.38), (-0.72, 0.24, 1.38), (-0.60, -0.24, 1.38), (-0.60, 0.24, 1.38)],
     "LEATHER", 0.04)
for s in (-1, 1):  # bolsters
    y0, y1 = sorted((s * 0.22, s * 0.31))
    box((-0.52, y0, 0.70), (-0.12, y1, 0.86), "LEATHER", 0.03)
    hull([(-0.64, y0, 0.74), (-0.64, y1, 0.74), (-0.50, y0, 0.74), (-0.50, y1, 0.74),
          (-0.72, y0, 1.20), (-0.72, y1, 1.20), (-0.62, y0, 1.22), (-0.62, y1, 1.22)], "LEATHER", 0.02)
box((-0.76, -0.16, 1.40), (-0.62, 0.16, 1.58), "LEATHER", 0.04)        # headrest
box((-0.70, -0.04, 1.32), (-0.66, 0.04, 1.42), "METAL")
box((-0.62, -0.07, 0.86), (-0.58, 0.07, 1.34), "SAND_D")              # harness strap
# ---- steering ----
# Volante no lugar das mãos da animação Mixamo "Driving" (motorista no banco central).
# Centro e eixo também estão em AJRVehiclePawn (SteeringWheelMesh): mudou aqui, mude lá.
WHEEL_C = Vector((0.08, 0, 1.165))                 # centro (m, espaço do chassi sem escala)
wax = Vector((-0.938, 0, 0.346)).normalized()      # eixo, apontando para o motorista (inclinado 20,25 graus)
WHEEL_R = 0.24
cyl(WHEEL_C - wax * 0.66, WHEEL_C - wax * 0.03, 0.03, "METAL", 8)   # coluna (fica no chassi)


def build_steering_wheel():
    """Volante em bmesh próprio, com origem no centro e eixo local +X = para longe do motorista."""
    global bm, CID
    main = (bm, CID)
    bm = bmesh.new()
    CID = bm.faces.layers.int.new("cid")
    torus(WHEEL_C, wax, WHEEL_R, 0.03, "BLACK", 24, 6)
    cyl(WHEEL_C - wax * 0.02, WHEEL_C + wax * 0.03, 0.055, "PURPLE", 10)
    u = wax.orthogonal().normalized()
    v = wax.cross(u)
    for ang in (90, 210, 330):
        a = math.radians(ang)
        d = u * math.cos(a) + v * math.sin(a)
        cyl(WHEEL_C, WHEEL_C + d * (WHEEL_R - 0.01), 0.016, "METAL", 6)
    # marca no topo (mostra o giro)
    top = Vector((0.346, 0, 0.938))
    sphere(WHEEL_C + top * WHEEL_R, 0.04, "PURPLE", 8, 6)
    xl = -wax
    yl = Vector((0, 1, 0))
    zl = xl.cross(yl)
    rot = Matrix((xl, yl, zl)).transposed().to_4x4()
    bmesh.ops.transform(bm, matrix=(Matrix.Translation(WHEEL_C) @ rot).inverted(), verts=bm.verts)
    out = (bm, CID)
    bm, CID = main
    return out, Matrix.Translation(WHEEL_C) @ rot


(WBM, WCID), WHEEL_MATRIX = build_steering_wheel()
cyl((0.62, 0.40, 0.64), (0.40, 0.40, 0.68), 0.03, "METAL", 6)           # shifter
cyl((0.30, 0.40, 0.66), (0.30, 0.40, 0.92), 0.02, "METAL", 6)
sphere((0.30, 0.40, 0.94), 0.04, "PURPLE", 8, 6)

# cargo next to seat: ammo crate and jerry can
box((-0.62, -0.78, 0.64), (-0.16, -0.40, 0.92), "SAND_D", 0.03)
box((-0.64, -0.80, 0.80), (-0.14, -0.38, 0.83), "DARK")
box((-0.55, 0.42, 0.64), (-0.25, 0.74, 1.02), "RUST", 0.04)
cyl((-0.40, 0.58, 1.02), (-0.40, 0.58, 1.08), 0.04, "DARK", 8)

# ---- nose + hood ----
hull([(0.88, -0.66, 0.50), (0.88, 0.66, 0.50), (1.98, -0.60, 0.50), (1.98, 0.60, 0.50),
      (0.88, -0.66, 1.12), (0.88, 0.66, 1.12), (1.98, -0.58, 0.90), (1.98, 0.58, 0.90)],
     "ORANGE", 0.05)
hz = lambda x: 1.12 + (0.90 - 1.12) * (x - 0.88) / 1.10
# hood centre panel + rust
hull([(0.95, -0.40, hz(0.95) - 0.02), (0.95, 0.40, hz(0.95) - 0.02),
      (1.88, -0.36, hz(1.88) - 0.02), (1.88, 0.36, hz(1.88) - 0.02),
      (0.95, -0.40, hz(0.95) + 0.025), (0.95, 0.40, hz(0.95) + 0.025),
      (1.88, -0.36, hz(1.88) + 0.025), (1.88, 0.36, hz(1.88) + 0.025)], "SAND", 0.015)
hull([(1.70, 0.38, hz(1.70) + 0.0), (1.70, 0.60, hz(1.70) + 0.0), (1.92, 0.38, hz(1.92) + 0.0),
      (1.92, 0.58, hz(1.92) + 0.0), (1.70, 0.38, hz(1.70) + 0.012), (1.70, 0.60, hz(1.70) + 0.012),
      (1.92, 0.38, hz(1.92) + 0.012), (1.92, 0.58, hz(1.92) + 0.012)], "RUST")
hull([(1.00, -0.64, hz(1.00) - 0.03), (1.00, -0.46, hz(1.00) - 0.03), (1.25, -0.64, hz(1.25) - 0.03),
      (1.25, -0.46, hz(1.25) - 0.03), (1.00, -0.64, hz(1.00) + 0.012), (1.00, -0.46, hz(1.00) + 0.012),
      (1.25, -0.64, hz(1.25) + 0.012), (1.25, -0.46, hz(1.25) + 0.012)], "RUST")
for s in (-1, 1):  # hood latch straps
    y0, y1 = sorted((s * 0.50, s * 0.56))
    box((1.80, y0, 0.70), (1.84, y1, hz(1.82) + 0.035), "DARK")

# ---- alien power cell on hood ----
zc = hz(1.38) + 0.17
box((1.08, -0.20, hz(1.08) - 0.02), (1.68, 0.20, zc - 0.04), "PURPLE_D", 0.04)   # cradle
cyl((1.10, 0, zc), (1.66, 0, zc), 0.14, "G_CELL", 14)
for x in (1.12, 1.38, 1.64):
    cyl((x - 0.03, 0, zc), (x + 0.03, 0, zc), 0.17, "PURPLE", 14)
for x, d in ((1.06, -1), (1.70, 1)):
    cyl((x - 0.04 * d, 0, zc), (x + 0.04 * d, 0, zc), 0.12, "METAL", 12, r2=0.07)
for s in (-1, 1):  # alien fins
    hull([(1.20, s * 0.17, zc - 0.05), (1.56, s * 0.17, zc - 0.05), (1.20, s * 0.20, zc - 0.05),
          (1.56, s * 0.20, zc - 0.05), (1.30, s * 0.26, zc + 0.20), (1.38, s * 0.26, zc + 0.22),
          (1.30, s * 0.23, zc + 0.20), (1.38, s * 0.23, zc + 0.22)], "PURPLE", 0.0)
    tube_path([(1.02, s * 0.10, zc), (0.95, s * 0.22, zc - 0.02), (0.84, s * 0.30, 1.13)],
              0.025, "PURPLE_D", 8)

# ---- headlights ----
for s in (-1, 1):
    y = s * 0.44
    hzz = hz(1.86) + 0.12
    cyl((1.72, y, hzz), (1.94, y, hzz), 0.15, "DARK", 14)
    cyl((1.92, y, hzz), (1.965, y, hzz), 0.125, "G_HEAD", 14)
    box((1.76, y - 0.04, hz(1.78) - 0.02), (1.84, y + 0.04, hzz), "DARK")
    hull([(1.80, y - 0.14, hzz + 0.10), (1.98, y - 0.14, hzz + 0.13), (1.80, y + 0.14, hzz + 0.10),
          (1.98, y + 0.14, hzz + 0.13), (1.80, y - 0.14, hzz + 0.13), (1.98, y - 0.14, hzz + 0.155),
          (1.80, y + 0.14, hzz + 0.13), (1.98, y + 0.14, hzz + 0.155)], "ORANGE")   # visor

# ---- ram plate with spikes ----
pts = []
for (z, w, xf) in ((0.40, 0.72, 2.06), (0.52, 0.94, 2.055), (0.90, 0.94, 2.025), (1.02, 0.70, 2.01)):
    for y in (-w, w):
        pts += [(xf - 0.07, y, z), (xf + 0.04, y, z)]
hull(pts, "DARK", 0.025)
for (z0, z1) in ((0.56, 0.63), (0.80, 0.87)):  # sand strips
    xfz = 2.06 - 0.035 * (z0 - 0.4) / 0.6
    box((xfz + 0.03, -0.90, z0), (xfz + 0.05, 0.90, z1), "SAND", 0.0)
spikes = [(y, 0.72) for y in (-0.68, -0.23, 0.23, 0.68)] + [(y, 0.50) for y in (-0.45, 0.0, 0.45)] + \
         [(y, 0.94) for y in (-0.45, 0.0, 0.45)]
for (y, z) in spikes:
    cyl((2.04, y, z), (2.20, y, z), 0.055, "STEEL", 8, r2=0.004)
    cyl((2.04, y, z), (2.10, y, z), 0.075, "RUST", 8)
for s in (-1, 1):  # bull bar uprights to hood
    cyl((1.98, s * 0.66, 1.0), (1.90, s * 0.62, 0.62), 0.04, "METAL", 8)
cyl((1.99, -0.70, 1.03), (1.99, 0.70, 1.03), 0.045, "METAL", 10)

# ---- fenders ----
for s in (-1, 1):
    ys = sorted((s * 0.62, s * 1.04))
    arch(FA, ys, 0.585, 0.665, 22, 162, "ORANGE", 12)
    arch(FA, sorted((s * 1.01, s * 1.045)), 0.60, 0.69, 26, 158, "DARK", 12)  # rubber lip
    arch(RA, ys, 0.585, 0.665, 18, 158, "ORANGE", 12)
    arch(RA, sorted((s * 1.01, s * 1.045)), 0.60, 0.69, 22, 154, "DARK", 12)
    # rust on fenders
    a0, a1 = math.radians(70), math.radians(110)
    yy = sorted((s * 0.70, s * 0.95))
    for xa in (FA, RA):
        hull([(xa + 0.668 * math.cos(a0), yy[0], 0.45 + 0.668 * math.sin(a0)),
              (xa + 0.668 * math.cos(a0), yy[1], 0.45 + 0.668 * math.sin(a0)),
              (xa + 0.668 * math.cos(a1), yy[0], 0.45 + 0.668 * math.sin(a1)),
              (xa + 0.668 * math.cos(a1), yy[1], 0.45 + 0.668 * math.sin(a1)),
              (xa + 0.68 * math.cos(a0), yy[0], 0.45 + 0.68 * math.sin(a0)),
              (xa + 0.68 * math.cos(a0), yy[1], 0.45 + 0.68 * math.sin(a0)),
              (xa + 0.68 * math.cos(a1), yy[0], 0.45 + 0.68 * math.sin(a1)),
              (xa + 0.68 * math.cos(a1), yy[1], 0.45 + 0.68 * math.sin(a1))],
             "RUST" if xa == FA else "SAND")

# ---- rear bed ----
box((-1.92, -0.64, 0.50), (-0.66, 0.64, 0.84), "DARK", 0.03)
for s in (-1, 1):
    y0, y1 = sorted((s * 0.56, s * 0.66))
    box((-1.92, y0, 0.80), (-0.66, y1, 1.02), "ORANGE", 0.03)
box((-1.95, -0.66, 0.80), (-1.86, 0.66, 1.00), "ORANGE", 0.03)

# ---- nitro tanks ----
for y in (-0.30, 0.30):
    z = 1.01
    cyl((-0.88, y, z), (-1.78, y, z), 0.17, "PURPLE", 14)
    cyl((-0.88, y, z), (-0.80, y, z), 0.17, "STEEL", 14, r2=0.09)
    cyl((-1.78, y, z), (-1.84, y, z), 0.17, "STEEL", 14, r2=0.10)
    for x in (-1.05, -1.60):
        cyl((x + 0.035, y, z), (x - 0.035, y, z), 0.185, "DARK", 14)
    box((-1.35, y - 0.09, z + 0.15), (-1.20, y + 0.09, z + 0.20), "SAND", 0.01)   # label
    cyl((-1.84, y, z), (-1.98, y, z), 0.06, "METAL", 10)
    cyl((-1.96, y, z), (-2.10, y, z), 0.065, "DARK", 12, r2=0.115)                # flared nozzle
    cyl((-2.06, y, z), (-2.12, y, z), 0.10, "G_NITRO", 12)
    cyl((-0.86, y, z + 0.12), (-0.86, y, z + 0.22), 0.035, "STEEL", 8)           # valve
    sphere((-0.86, y, z + 0.24), 0.045, "PURPLE_D", 8, 6)
cyl((-0.90, -0.30, 1.20), (-0.90, 0.30, 1.20), 0.025, "METAL", 8)               # cross pipe

# ---- rear bumper + tow ----
box((-2.03, -0.90, 0.42), (-1.91, 0.90, 0.68), "DARK", 0.03)
box((-2.04, -0.88, 0.60), (-2.02, 0.88, 0.64), "SAND", 0.0)
box((-2.10, -0.06, 0.46), (-2.02, 0.06, 0.56), "METAL", 0.01)

# ---- mud flaps ----
for s in (-1, 1):
    y0, y1 = sorted((s * 0.72, s * 1.03))
    box((-1.905, y0, 0.37), (-1.875, y1, 0.92), "RUBBER", 0.008)
    yb0, yb1 = sorted((s * 0.80, s * 0.95))
    box((-1.912, yb0, 0.46), (-1.900, yb1, 0.56), "SAND", 0.0)
    box((0.880, y0, 0.40), (0.905, y1, 0.86), "RUBBER", 0.008)
    box((0.874, yb0, 0.48), (0.882, yb1, 0.56), "PURPLE", 0.0)

# ---- side exhausts ----
for s in (-1, 1):
    y = s * 0.975
    cyl((0.95, s * 0.62, 0.78), (0.80, y, 0.62), 0.05, "METAL", 10)
    cyl((0.80, y, 0.62), (-0.64, y, 0.62), 0.06, "METAL", 10)
    sphere((-0.66, y, 0.62), 0.063, "METAL", 10, 6)
    cyl((-0.66, y, 0.62), (-0.66, y, 1.42), 0.06, "STEEL", 10)
    cyl((-0.66, y, 1.40), (-0.71, y, 1.60), 0.06, "RUST", 10, r2=0.075)
    cyl((-0.705, y, 1.58), (-0.715, y, 1.605), 0.055, "BLACK", 10)
    cyl((-0.66, y, 1.06), (-0.66, y, 1.14), 0.072, "DARK", 10)
    hull([(-0.30, y, 0.56), (0.55, y, 0.56), (-0.30, y + s * 0.04, 0.60), (0.55, y + s * 0.04, 0.60),
          (-0.30, y, 0.69), (0.55, y, 0.69), (-0.30, y + s * 0.04, 0.665), (0.55, y + s * 0.04, 0.665)],
         "RUST")
    for zz in (0.95, 1.25):
        box((-0.70, y - 0.06, zz - 0.02), (-0.62, y + 0.06, zz + 0.02), "DARK")

# ---- roll cage ----
R_T = 0.05
CAGE = "DARK"
J = "PURPLE"
ZT = 1.84
for s in (-1, 1):
    tube_path([(-0.72, s * 0.88, 1.05), (-0.72, s * 0.70, ZT)], R_T, CAGE, 10)
    tube_path([(0.84, s * 0.88, 1.10), (0.14, s * 0.70, ZT)], R_T, CAGE, 10)
    cyl((0.14, s * 0.70, ZT), (-0.72, s * 0.70, ZT), R_T, CAGE, 10)
    cyl((-0.72, s * 0.70, ZT), (-1.84, s * 0.50, 0.98), R_T, CAGE, 10)       # rear braces
    cyl((-0.72, s * 0.86, 1.20), (0.70, s * 0.86, 1.20), 0.042, CAGE, 10)    # door bar
    cyl((-0.72, s * 0.86, 1.20), (0.20, s * 0.84, 1.60), 0.035, CAGE, 8)     # diagonal
    for p in ((-0.72, s * 0.70, ZT), (0.14, s * 0.70, ZT)):
        sphere(p, 0.075, J, 10, 6)
    for p in ((-0.72, s * 0.88, 1.05), (0.84, s * 0.88, 1.10), (-1.84, s * 0.50, 0.98)):
        cyl((p[0], p[1], p[2] - 0.05), (p[0], p[1], p[2] + 0.04), 0.075, "METAL", 10)
cyl((-0.72, -0.70, ZT), (-0.72, 0.70, ZT), R_T, CAGE, 10)
cyl((0.14, -0.70, ZT), (0.14, 0.70, ZT), R_T, CAGE, 10)
cyl((-0.72, -0.70, ZT), (0.14, 0.70, ZT), 0.035, CAGE, 8)
cyl((-0.72, -0.82, 1.40), (-0.72, 0.82, 1.40), 0.04, CAGE, 10)              # harness bar
# light bar
box((0.20, -0.56, ZT - 0.17), (0.30, 0.56, ZT - 0.05), "DARK", 0.02)
for s in (-1, 1):
    box((0.16, s * 0.45 - 0.02, ZT - 0.09), (0.24, s * 0.45 + 0.02, ZT + 0.0), "METAL")
for y in (-0.39, -0.13, 0.13, 0.39):
    cyl((0.30, y, ZT - 0.11), (0.33, y, ZT - 0.11), 0.055, "G_HEAD", 10)
# alien antenna
cyl((-0.74, -0.60, ZT + 0.02), (-0.95, -0.60, ZT - 0.02), 0.022, "PURPLE_D", 6)

# ---- spare tire on rear mount ----
for s in (-1, 1):
    cyl((-1.76, s * 0.53, 1.04), (-1.92, s * 0.05, 1.40), 0.04, "METAL", 8)
cyl((-1.76, -0.53, 1.04), (-1.76, 0.53, 1.04), 0.04, "METAL", 8)
cyl((-1.88, 0, 1.44), (-1.97, 0, 1.44), 0.09, "METAL", 10)
TC = Vector((-2.045, 0, 1.44))
torus(TC, (1, 0, 0), 0.25, 0.115, "RUBBER", 20, 8)
cyl((-1.97, 0, 1.44), (-2.11, 0, 1.44), 0.16, "SAND_D", 12)
cyl((-2.11, 0, 1.44), (-2.155, 0, 1.44), 0.07, "PURPLE", 10)
for i in range(12):  # tread blocks
    a = 2 * math.pi * (i + 0.5) / 12
    c = TC + Vector((0, math.cos(a), math.sin(a))) * 0.355
    rot = Matrix.Rotation(a, 3, 'X')
    M = Matrix.Translation(c) @ rot.to_4x4() @ Matrix.Diagonal((0.17, 0.05, 0.09, 1))
    v = bmesh.ops.create_cube(bm, size=1.0, matrix=M)["verts"]
    tag(faces_of(v), "RUBBER")

# =====================================================================
#                      FINALIZE MESH + ATTRIBUTES
# =====================================================================
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
cids = [f[CID] for f in bm.faces]

# clean scene
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new("SM_Car_AlienBuggy")
bm.to_mesh(me)
bm.free()
ob = bpy.data.objects.new("SM_Car_AlienBuggy", me)
bpy.context.scene.collection.objects.link(ob)

for p in me.polygons:
    p.use_smooth = False

# vertex colors
rnd = random.Random(7)
ca = me.color_attributes.new("Col", 'BYTE_COLOR', 'CORNER')
me.color_attributes.active_color = ca
me.color_attributes.render_color_index = me.color_attributes.find("Col")
me.color_attributes.active_color_index = me.color_attributes.find("Col")
for p in me.polygons:
    name = NAMES[cids[p.index]]
    base = C[name]
    k = 1.0 if name in GLOW else 1.0 + rnd.uniform(-0.06, 0.06)
    col = tuple(min(1.0, max(0.0, c * k)) for c in base) + (1.0,)
    for li in p.loop_indices:
        ca.data[li].color_srgb = col

# UV: cube projection
uv = me.uv_layers.new(name="UVMap")
S = 0.5
for p in me.polygons:
    n = p.normal
    ax = max(range(3), key=lambda i: abs(n[i]))
    for li in p.loop_indices:
        co = me.vertices[me.loops[li].vertex_index].co
        if ax == 0:
            u, v = co.y * S, co.z * S
        elif ax == 1:
            u, v = co.x * S, co.z * S
        else:
            u, v = co.x * S, co.y * S
        uv.data[li].uv = (u, v)

# materials
def make_mat(name, glow):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    if glow:
        nt.links.new(attr.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 6.0
    return m

me.materials.append(make_mat("M_Car_Body", False))
me.materials.append(make_mat("M_L01_Glow", True))

# ---- volante: objeto separado, mesmos materiais e cores ----
bmesh.ops.remove_doubles(WBM, verts=WBM.verts, dist=1e-6)
bmesh.ops.recalc_face_normals(WBM, faces=WBM.faces)
wcids = [f[WCID] for f in WBM.faces]
wme = bpy.data.meshes.new("SM_Car_AlienBuggy_SteeringWheel")
WBM.to_mesh(wme)
WBM.free()
wob = bpy.data.objects.new("SM_Car_AlienBuggy_SteeringWheel", wme)
bpy.context.scene.collection.objects.link(wob)
wca = wme.color_attributes.new("Col", 'BYTE_COLOR', 'CORNER')
wme.color_attributes.active_color = wca
for p in wme.polygons:
    p.use_smooth = False
    col = C[NAMES[wcids[p.index]]] + (1.0,)
    for li in p.loop_indices:
        wca.data[li].color_srgb = col
wuv = wme.uv_layers.new(name="UVMap")
for p in wme.polygons:
    for li in p.loop_indices:
        co = wme.vertices[wme.loops[li].vertex_index].co
        wuv.data[li].uv = (co.y * S, co.z * S)
wme.materials.append(me.materials[0])
wme.materials.append(me.materials[1])
wob.matrix_world = WHEEL_MATRIX        # só para o preview; exporta na origem

tris = sum(len(p.vertices) - 2 for p in me.polygons)
print("TRIS", tris, "DIMS", tuple(round(d, 3) for d in ob.dimensions))
bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
print("BBOX min", [round(min(v[i] for v in bb), 3) for i in range(3)],
      "max", [round(max(v[i] for v in bb), 3) for i in range(3)])

# =====================================================================
#                            PREVIEW
# =====================================================================
scn = bpy.context.scene
wheels = []
for x in (FA, RA):
    for y in (-0.92, 0.92):
        wm = bpy.data.meshes.new("w")
        wb = bmesh.new()
        bmesh.ops.create_cone(wb, cap_ends=True, segments=24, radius1=0.45, radius2=0.45, depth=0.35,
                              matrix=Matrix.Translation((x, y, 0.45)) @ Matrix.Rotation(math.pi / 2, 4, 'X'))
        wb.to_mesh(wm)
        wb.free()
        wc = wm.color_attributes.new("Col", 'BYTE_COLOR', 'CORNER')
        for d in wc.data:
            d.color_srgb = (0.06, 0.06, 0.07, 1)
        wo = bpy.data.objects.new("wheel", wm)
        scn.collection.objects.link(wo)
        wheels.append(wo)
gm = bpy.data.meshes.new("ground")
gb = bmesh.new()
bmesh.ops.create_grid(gb, x_segments=1, y_segments=1, size=6)
gb.to_mesh(gm)
gb.free()
gc = gm.color_attributes.new("Col", 'BYTE_COLOR', 'CORNER')
for d in gc.data:
    d.color_srgb = (0.55, 0.50, 0.42, 1)
go = bpy.data.objects.new("ground", gm)
scn.collection.objects.link(go)

scn.render.engine = 'BLENDER_WORKBENCH'
sh = scn.display.shading
sh.light = 'STUDIO'
sh.color_type = 'VERTEX'
sh.show_object_outline = True
sh.object_outline_color = (0, 0, 0)
sh.show_cavity = True
sh.cavity_type = 'WORLD'
sh.show_shadows = True
sh.background_type = 'VIEWPORT'
sh.background_color = (0.62, 0.70, 0.78)
scn.render.resolution_x, scn.render.resolution_y = 900, 640
scn.render.film_transparent = False
scn.view_settings.view_transform = 'Standard'

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scn.collection.objects.link(cam)
scn.camera = cam
views = [
    ("q", (7.5, -6.2, 4.4), None),
    ("s", (0.0, -10.0, 1.1), None),
    ("t", (0.0, 0.0, 10.0), None),
    ("r", (-7.0, 5.0, 3.8), None),
]
import os
paths = []
for name, loc, _ in views:
    cam.location = loc
    target = Vector((0, 0, 1.0 if name != "t" else 0))
    if name in ("s", "t"):
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = 5.2
    else:
        cam.data.type = 'PERSP'
        cam.data.lens = 50
    d = target - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    if name == "t":
        cam.rotation_euler = (0, 0, 0)
    pth = "/home/claude/car/_v_%s.png" % name
    scn.render.filepath = pth
    bpy.ops.render.render(write_still=True)
    paths.append(pth)

# remove preview helpers before export
for o in wheels + [go, cam]:
    bpy.data.objects.remove(o, do_unlink=True)

# volante: exporta sozinho, com a origem no centro dele
wob.matrix_world = Matrix()
for o in bpy.context.scene.objects:
    o.select_set(o == wob)
bpy.context.view_layer.objects.active = wob
bpy.ops.export_scene.fbx(filepath=FBX_WHEEL, use_selection=True, object_types={'MESH'}, apply_unit_scale=True,
                         mesh_smooth_type='FACE', colors_type='SRGB', add_leaf_bones=False)
print("EXPORTED", FBX_WHEEL)
bpy.data.objects.remove(wob, do_unlink=True)

# =====================================================================
#                              EXPORT
# =====================================================================
for o in bpy.context.scene.objects:
    o.select_set(o == ob)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.export_scene.fbx(filepath=FBX, object_types={'MESH'}, apply_unit_scale=True,
                         mesh_smooth_type='FACE', colors_type='SRGB', add_leaf_bones=False)
print("EXPORTED", FBX)
with open("/home/claude/car/_views.txt", "w") as f:
    f.write("\n".join(paths))
