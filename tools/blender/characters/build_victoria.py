"""Monta CHR-002 Victoria: partes do Tripo + correções (pescoço único, calça na altura certa)."""
import bpy, bmesh, sys, json
args = sys.argv[sys.argv.index("--") + 1:]
cfgp, out = args[0], args[1]
cfg = json.load(open(cfgp))
SRC, H = cfg["src"], cfg["height_m"]
bpy.ops.wm.read_factory_settings(use_empty=True)
objs = {}
for name, p in cfg["parts"].items():
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=SRC + p["file"])
    new = [o for o in bpy.data.objects if o not in before]
    mesh = [o for o in new if o.type == "MESH"][0]
    mw = mesh.matrix_world.copy(); mesh.parent = None; mesh.matrix_world = mw
    for o in new:
        if o is not mesh: bpy.data.objects.remove(o)
    s = p["scale"] * H
    mesh.scale = (s, s, s * p.get("zstretch", 1.0))
    mesh.location = (0, p.get("dy", 0.0), p["z0"] * H)
    mesh.name = f"Part_{name}"
    objs[name] = mesh
bpy.ops.object.select_all(action="DESELECT")
for o in objs.values(): o.select_set(True)
bpy.context.view_layer.objects.active = objs["jacket"]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Pescoço único: remove o "toco" de pescoço do top (fica o pescoço da cabeça, mesma cor do rosto)
cut = cfg["jacket_neck_cut"]
j = objs["jacket"]; bm = bmesh.new(); bm.from_mesh(j.data)
dead = [v for v in bm.verts if v.co.z > cut["z"] and abs(v.co.x) < cut["max_abs_x"]]
bmesh.ops.delete(bm, geom=dead, context="VERTS"); bm.to_mesh(j.data); bm.free()
print("JACKET_NECK_REMOVED", len(dead))
js = cfg.get("jacket_neck_stretch")  # estica o pescoço do corpo pra cima até entrar na cabeça
if js:
    n = 0
    for v in j.data.vertices:
        r = (v.co.x ** 2 + (v.co.y - js["yc"]) ** 2) ** 0.5
        if v.co.z > js["z0"] and r < js["r_max"]:
            t = min(1.0, (v.co.z - js["z0"]) / 0.02)  # transição suave na base
            v.co.z = js["z0"] + (v.co.z - js["z0"]) * (1 + (js["k"] - 1) * t)
            w = js.get("widen", 1.0); tz = min(1.0, max(0.0, (v.co.z - js["z0"]) / 0.03))
            f = 1 + (w - 1) * tz
            tf = js.get("top_flare")  # alarga só o topo do pescoço pra fechar por dentro da mandíbula
            if tf:
                u = min(1.0, max(0.0, (v.co.z - tf["z_a"]) / (tf["z_b"] - tf["z_a"]))); u = u * u * (3 - 2 * u)
                f *= 1 + (tf["scale"] - 1) * u
            v.co.x *= f; v.co.y = js["yc"] + (v.co.y - js["yc"]) * f; n += 1
    print("JACKET_NECK_STRETCH", n)

# Corta a "tampa" da base do pescoço da cabeça (fica escondida dentro do top)
hc = cfg.get("head_bottom_cut")
if hc:
    h = objs["head"]; mw = h.matrix_world; mi_h = mw.inverted(); bm = bmesh.new(); bm.from_mesh(h.data)
    dead = [v for v in bm.verts if (mw @ v.co).z < hc and (mw @ v.co).y > cfg.get("head_bottom_cut_min_y", -9)]
    bmesh.ops.delete(bm, geom=dead, context="VERTS"); bm.to_mesh(h.data); bm.free()
    print("HEAD_BOTTOM_REMOVED", len(dead))
    nf = cfg.get("neck_flare")  # engrossa o pescoço (só a parte perto do eixo, sem pegar o cabelo)
    if nf:
        n = 0
        import numpy as np
        img = [nd.image for m in h.data.materials for nd in m.node_tree.nodes if nd.type == "TEX_IMAGE" and nd.image][0]
        W, Hh = img.size; px = np.empty(W * Hh * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(Hh, W, 4)
        uvl = h.data.uv_layers.active.data; skin = {}
        for lp in h.data.loops:
            u, vv = uvl[lp.index].uv; c = px[min(int(vv * Hh), Hh - 1) % Hh, min(int(u * W), W - 1) % W]
            skin.setdefault(lp.vertex_index, []).append(c[0] > 0.35 and c[0] - c[2] > 0.12)
        skin = {k: sum(v) > len(v) / 2 for k, v in skin.items()}
        for v in h.data.vertices:
            w = mw @ v.co
            dx, dyy = w.x, w.y - nf["yc"]
            r = (dx * dx + dyy * dyy) ** 0.5
            if w.z < nf["z_top"] and r < nf["r_max"] and skin.get(v.index, False):
                t = max(0.0, min(1.0, (nf["z_top"] - w.z) / (nf["z_top"] - nf["z_bot"])))
                t = t * t * (3 - 2 * t)
                fr = max(0.0, min(1.0, (nf["r_max"] - r) / 0.015))
                k = 1 + (nf["scale"] - 1) * t * fr
                w.x = dx * k; w.y = nf["yc"] + dyy * k; v.co = mi_h @ w; n += 1
        print("NECK_FLARE", n)
    tk = cfg.get("head_front_tuck")  # recolhe a "aba" da frente do pescoço pra dentro do top
    if tk:
        mi = mw.inverted(); n = 0
        for v in h.data.vertices:
            w = mw @ v.co
            yc = tk.get("yc", 0.0)
            if w.z < tk["z_top"] and w.y < yc:
                t = max(0.0, min(1.0, (tk["z_top"] - w.z) / (tk["z_top"] - tk["z_bot"])))
                w.y = yc + (w.y - yc) * (1 - t * (1 - tk["factor"])); v.co = mi @ w; n += 1
        print("HEAD_FRONT_TUCK", n)

# Alternativa: usa o pescoço do corpo (top) e apaga o pescoço da cabeça abaixo da mandíbula
hn = cfg.get("head_neck_remove")
if hn:
    import numpy as np
    h = objs["head"]; mw = h.matrix_world
    img = [nd.image for m in h.data.materials for nd in m.node_tree.nodes if nd.type == "TEX_IMAGE" and nd.image][0]
    W, Hh = img.size; px = np.empty(W * Hh * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(Hh, W, 4)
    uvl = h.data.uv_layers.active.data; sk = {}
    for lp in h.data.loops:
        u, vv = uvl[lp.index].uv; c = px[min(int(vv * Hh), Hh - 1) % Hh, min(int(u * W), W - 1) % W]
        sk.setdefault(lp.vertex_index, []).append(c[0] > 0.35 and c[0] - c[2] > 0.12)
    bm = bmesh.new(); bm.from_mesh(h.data); bm.verts.ensure_lookup_table(); dead = []
    for v in bm.verts:
        w = mw @ v.co; r = (w.x ** 2 + (w.y - hn["yc"]) ** 2) ** 0.5
        l = sk.get(v.index, [False])
        if w.z < hn["z"] and r < hn["r_max"] and sum(l) > len(l) / 2: dead.append(v)
    tp = hn.get("taper")  # afina a borda de baixo do pescoço da cabeça pra ela entrar no pescoço do corpo
    if tp:
        mi = mw.inverted(); nt = 0
        for v in bm.verts:
            if v in dead: continue
            w = mw @ v.co; r = (w.x ** 2 + (w.y - hn["yc"]) ** 2) ** 0.5
            l = sk.get(v.index, [False])
            if hn["z"] <= w.z < hn["z"] + tp["h"] and r < hn["r_max"] and sum(l) > len(l) / 2:
                u = (w.z - hn["z"]) / tp["h"]; u = u * u * (3 - 2 * u)
                f = tp["f"] + (1 - tp["f"]) * u
                w.x *= f; w.y = hn["yc"] + (w.y - hn["yc"]) * f; v.co = mi @ w; nt += 1
        print("HEAD_NECK_TAPER", nt)
    before = {frozenset((e.verts[0].index, e.verts[1].index)) for e in bm.edges if e.is_boundary}
    bmesh.ops.delete(bm, geom=dead, context="VERTS")
    print("HEAD_NECK_REMOVED", len(dead))
    sk2 = hn.get("skirt")  # "saia": estende a borda do buraco pra baixo e pra dentro do pescoço do corpo
    if sk2:
        from mathutils import Vector
        bm.verts.index_update()
        # índices mudaram: refaz a comparação por posição
        newb = [e for e in bm.edges if e.is_boundary]
        ring_edges = []
        for e in newb:
            ok = True
            for v in e.verts:
                w = mw @ v.co; r = (w.x ** 2 + (w.y - hn["yc"]) ** 2) ** 0.5
                if not (hn["z"] - 0.002 < w.z < hn["z"] + sk2["band"] and r < hn["r_max"] + 0.01): ok = False
            if ok: ring_edges.append(e)
        res = bmesh.ops.extrude_edge_only(bm, edges=ring_edges)
        nv = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
        mi = mw.inverted()
        for v in nv:
            w = mw @ v.co; dx, dy = w.x, w.y - hn["yc"]
            w.x = dx * sk2["shrink"]; w.y = hn["yc"] + dy * sk2["shrink"]; w.z -= sk2["drop"]
            v.co = mi @ w
        print("SKIRT edges", len(ring_edges), "verts", len(nv))
    bm.to_mesh(h.data); bm.free()

# Funde o pescoço do corpo no pescoço da cabeça: o topo do pescoço do corpo assume o formato
# do pescoço da cabeça (raio medido por raycast) e some por dentro dele, sem degrau.
nb = cfg.get("neck_blend")
if nb:
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    h = objs["head"]; j = objs["jacket"]; yc = nb["yc"]
    hb = bmesh.new(); hb.from_mesh(h.data); hb.transform(h.matrix_world); tree = BVHTree.FromBMesh(hb)
    bm = bmesh.new(); bm.from_mesh(j.data); dead = []; n = 0
    for v in bm.verts:
        r = (v.co.x ** 2 + (v.co.y - yc) ** 2) ** 0.5
        if r > nb["r_max"] or v.co.z < nb["z_a"]: continue
        if v.co.z > nb["z_del"]: dead.append(v); continue
        d = Vector((v.co.x, v.co.y - yc, 0.0))
        if d.length < 1e-6: continue
        d.normalize(); zs = max(v.co.z, nb["z_sample"])
        hit = tree.ray_cast(Vector((0.0, yc, zs)), d, nb.get("ray_max", 0.068))
        if hit[0] is None: continue
        R = (Vector((hit[0].x, hit[0].y - yc, 0))).length * nb["inset"]
        u = min(1.0, max(0.0, (v.co.z - nb["z_a"]) / (nb["z_b"] - nb["z_a"]))); u = u * u * (3 - 2 * u)
        rn = r + (R - r) * u
        v.co.x = d.x * rn; v.co.y = yc + d.y * rn; n += 1
    bmesh.ops.delete(bm, geom=dead, context="VERTS"); bm.to_mesh(j.data); bm.free(); hb.free()
    print("NECK_BLEND", n, "del", len(dead))

# Fecha a borda do buraco da cabeça em cima do pescoço do corpo (some a fresta vista de baixo)
sh = cfg.get("seal_hole")
if sh:
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    h = objs["head"]; j = objs["jacket"]; yc = sh["yc"]; mw = h.matrix_world; mi = mw.inverted()
    jb = bmesh.new(); jb.from_mesh(j.data); tree = BVHTree.FromBMesh(jb)
    bm = bmesh.new(); bm.from_mesh(h.data); bm.verts.ensure_lookup_table()
    ring = set()
    for e in bm.edges:
        if e.is_boundary:
            for v in e.verts:
                w = mw @ v.co; r = (w.x ** 2 + (w.y - yc) ** 2) ** 0.5
                if sh["z_lo"] < w.z < sh["z_hi"] and r < sh["r_max"]: ring.add(v)
    targets = {}
    for v in ring: targets[v] = 1.0
    for v in list(ring):
        for e in v.link_edges:
            o = e.other_vert(v)
            if o not in targets: targets[o] = sh["neighbor"]
    n = 0
    for v, wgt in targets.items():
        w = mw @ v.co; d = Vector((w.x, w.y - yc, 0)); r = d.length
        if r < 1e-6: continue
        d.normalize()
        hit = tree.ray_cast(Vector((0, yc, w.z - sh["drop"] * wgt)), d, 0.09)
        if hit[0] is None: continue
        R = Vector((hit[0].x, hit[0].y - yc, 0)).length * sh["inset"]
        if R >= r: continue
        rn = r + (R - r) * wgt
        w = Vector((d.x * rn, yc + d.y * rn, w.z - sh["drop"] * wgt)); v.co = mi @ w; n += 1
    bm.to_mesh(h.data); bm.free(); jb.free()
    print("SEAL_HOLE ring", len(ring), "moved", n)

# Tubo de transição gerado: liga o pescoço do corpo ao pescoço da cabeça sem degrau
nt = cfg.get("neck_tube")
if nt:
    import math
    from mathutils.bvhtree import BVHTree
    from mathutils.kdtree import KDTree
    from mathutils import Vector
    h = objs["head"]; j = objs["jacket"]; yc = nt["yc"]
    jb = bmesh.new(); jb.from_mesh(j.data); jb.faces.ensure_lookup_table(); jtree = BVHTree.FromBMesh(jb)
    jbuv = jb.loops.layers.uv.active
    def jb_uv(l): return l[jbuv].uv.copy()
    uvl = j.data.uv_layers.active.data
    kd = KDTree(len(j.data.loops)); 
    for lp in j.data.loops: kd.insert(j.data.vertices[lp.vertex_index].co, lp.index)
    kd.balance()
    mat_idx = {}
    for p in j.data.polygons:
        for li in p.loop_indices: mat_idx[li] = p.material_index
    hb = bmesh.new(); hb.from_mesh(h.data); hb.transform(h.matrix_world); htree = BVHTree.FromBMesh(hb)
    N, K = nt["n"], nt["k"]
    import numpy as np
    himg = [nd.image for m in h.data.materials for nd in m.node_tree.nodes if nd.type == "TEX_IMAGE" and nd.image][0]
    HW, HH = himg.size; hpx = np.empty(HW * HH * 4, dtype=np.float32); himg.pixels.foreach_get(hpx); hpx = hpx.reshape(HH, HW, 4)
    hb.faces.ensure_lookup_table(); huv = hb.loops.layers.uv.active
    def is_skin(fi):
        u, v = hb.faces[fi].loops[0][huv].uv; c = hpx[int(v * HH) % HH, int(u * HW) % HW]
        return c[0] > 0.35 and c[0] - c[2] > 0.12
    def ray(tree, z, d, skin=False):
        o = Vector((0, yc, z)); left = nt["ray_max"]
        while left > 0:
            hit = tree.ray_cast(o, d, left)
            if hit[0] is None: return None
            if not skin or is_skin(hit[2]): return Vector((hit[0].x, hit[0].y - yc, 0)).length
            left -= (hit[0] - o).length + 1e-4; o = hit[0] + d * 1e-4
        return None
    rb, rt = [], []
    for i in range(N):
        a = 2 * math.pi * i / N; d = Vector((math.cos(a), math.sin(a), 0))
        rb.append(ray(jtree, nt["zb"], d)); rt.append(ray(htree, nt.get("zt_sample", nt["zt"]), d, True))
    for arr in (rb, rt):  # preenche falhas com vizinhos
        for i in range(N):
            if arr[i] is None:
                k = 1
                while arr[(i - k) % N] is None and arr[(i + k) % N] is None and k < N: k += 1
                arr[i] = arr[(i - k) % N] or arr[(i + k) % N]
    # apaga o topo do pescoço do corpo (fica escondido/substituído pelo tubo)
    bm = bmesh.new(); bm.from_mesh(j.data)
    dead = [v for v in bm.verts if v.co.z > nt["zb_del"] and (v.co.x ** 2 + (v.co.y - yc) ** 2) ** 0.5 < nt["r_max"]]
    bmesh.ops.delete(bm, geom=dead, context="VERTS")
    uvlay = bm.loops.layers.uv.active
    if nt.get("uv_fixed"):
        loc, nrm, fi, dist = jtree.find_nearest(Vector(nt["uv_fixed"]))
        jf = jb.faces[fi]; fixed_uv = jf.loops[0][jbuv].uv.copy(); fixed_mat = jf.material_index
        print("FIXED_UV", tuple(round(x, 4) for x in fixed_uv))
    rings = []
    for kk in range(K + 1):
        t = kk / K; u = t * t * (3 - 2 * t)
        z = nt["zb"] - nt["ext"] + (nt["zt"] - nt["zb"] + 2 * nt["ext"]) * t
        row = []
        for i in range(N):
            a = 2 * math.pi * i / N
            r = (rb[i] + (rt[i] - rb[i]) * u) * nt["inset"]
            cr = nt.get("cross")  # cruza a superfície da cabeça: cobre a borda dela e some por dentro
            if cr:
                if z >= cr["z0"]:
                    q = min(1.0, (z - cr["z0"]) / (cr["z1"] - cr["z0"]))
                    r *= cr["out"] + (cr["in"] - cr["out"]) * q
                else:
                    q = max(0.0, 1 - (cr["z0"] - z) / 0.01)
                    r *= 1 + (cr["out"] - 1) * q
            row.append(bm.verts.new((math.cos(a) * r, yc + math.sin(a) * r, z)))
        rings.append(row)
    nf = 0
    for kk in range(K):
        for i in range(N):
            a, b = rings[kk][i], rings[kk][(i + 1) % N]
            c, d = rings[kk + 1][(i + 1) % N], rings[kk + 1][i]
            f = bm.faces.new((a, b, c, d)); nf += 1; f.smooth = True
            if nt.get("uv_fixed"):
                for lp in f.loops:
                    ang = math.atan2(lp.vert.co.y - yc, lp.vert.co.x)
                    lp[uvlay].uv = (fixed_uv[0] + 0.003 * math.cos(ang), fixed_uv[1] + 0.003 * math.sin(ang))
                f.material_index = fixed_mat; continue
            for lp in f.loops:
                p = lp.vert.co.copy(); p.z = min(p.z, nt["uv_zmax"])  # UV do pescoço do corpo original
                loc, nrm, fi, dist = jtree.find_nearest(p)
                jf = jb.faces[fi] if fi is not None else None
                if jf is None:
                    co, li, dist = kd.find(lp.vert.co); lp[uvlay].uv = uvl[li].uv; continue
                from mathutils.geometry import barycentric_transform
                vs = [l.vert.co for l in jf.loops][:3]; uvs = [jb_uv(l) for l in jf.loops][:3]
                uvp = barycentric_transform(loc, vs[0], vs[1], vs[2], uvs[0].to_3d(), uvs[1].to_3d(), uvs[2].to_3d())
                lp[uvlay].uv = uvp.xy; f.material_index = jf.material_index
    bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces][-nf:])
    bm.to_mesh(j.data); bm.free(); jb.free(); hb.free()
    print("NECK_TUBE faces", nf, "body_del", len(dead), "rb", round(min(rb),3), round(max(rb),3), "rt", round(min(rt),3), round(max(rt),3))

# Conforma cabeça e corpo numa mesma superfície na faixa da emenda (sem vinco)
nc = cfg.get("neck_conform")
if nc:
    import math, numpy as np
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    h = objs["head"]; j = objs["jacket"]; yc = nc["yc"]
    hb = bmesh.new(); hb.from_mesh(h.data); hb.transform(h.matrix_world); hb.faces.ensure_lookup_table()
    ht = BVHTree.FromBMesh(hb); huv = hb.loops.layers.uv.active
    himg = [nd.image for m in h.data.materials for nd in m.node_tree.nodes if nd.type == "TEX_IMAGE" and nd.image][0]
    HW, HH = himg.size; hpx = np.empty(HW * HH * 4, dtype=np.float32); himg.pixels.foreach_get(hpx); hpx = hpx.reshape(HH, HW, 4)
    def skin_c(c): return c[0] > 0.35 and c[0] - c[2] > 0.12
    def is_skin(fi):
        u, v = hb.faces[fi].loops[0][huv].uv; return skin_c(hpx[int(v * HH) % HH, int(u * HW) % HW])
    jb = bmesh.new(); jb.from_mesh(j.data); jt = BVHTree.FromBMesh(jb)
    def ray(tree, z, d, skin):
        o = Vector((0, yc, z)); left = 0.08
        while left > 0:
            hit = tree.ray_cast(o, d, left)
            if hit[0] is None: return None
            if not skin or is_skin(hit[2]): return Vector((hit[0].x, hit[0].y - yc, 0)).length
            left -= (hit[0] - o).length + 1e-4; o = hit[0] + d * 1e-4
        return None
    N = nc["n"]; rb = []; rt = []
    for i in range(N):
        a = 2 * math.pi * i / N; d = Vector((math.cos(a), math.sin(a), 0))
        rb.append(ray(jt, nc["zb"], d, False)); rt.append(ray(ht, nc["zt"], d, True))
    for arr in (rb, rt):
        for i in range(N):
            if arr[i] is None:
                k = 1
                while arr[(i - k) % N] is None and arr[(i + k) % N] is None and k < N: k += 1
                arr[i] = arr[(i - k) % N] or arr[(i + k) % N]
    # suaviza o perfil angular
    def smooth(a):
        return [(a[(i - 1) % N] + 2 * a[i] + a[(i + 1) % N]) / 4 for i in range(N)]
    rb = smooth(smooth(rb)); rt = smooth(smooth(rt))
    def target(x, y, z):
        ang = math.atan2(y - yc, x) % (2 * math.pi); f = ang / (2 * math.pi) * N
        i0 = int(f) % N; i1 = (i0 + 1) % N; w = f - int(f)
        b = rb[i0] * (1 - w) + rb[i1] * w; t = rt[i0] * (1 - w) + rt[i1] * w
        u = min(1.0, max(0.0, (z - nc["zb"]) / (nc["zt"] - nc["zb"]))); u = u * u * (3 - 2 * u)
        return b + (t - b) * u
    def conform(obj, off, skin_check):
        mw = obj.matrix_world; mi = mw.inverted(); me = obj.data; n = 0
        skin = None
        if skin_check:
            uvl = me.uv_layers.active.data; skin = {}
            for lp in me.loops:
                u, v = uvl[lp.index].uv; skin.setdefault(lp.vertex_index, []).append(skin_c(hpx[int(v * HH) % HH, int(u * W_) % W_]) if False else skin_c(hpx[int(v * HH) % HH, int(u * HW) % HW]))
        for v in me.vertices:
            w = mw @ v.co
            if not (nc["zb"] - nc["feather"] < w.z < nc["zt"] + nc["feather"]): continue
            r = (w.x ** 2 + (w.y - yc) ** 2) ** 0.5
            if r > nc["r_max"] or r < 1e-6: continue
            if skin is not None:
                l = skin.get(v.index, [False])
                if sum(l) <= len(l) / 2: continue
            R = target(w.x, w.y, min(max(w.z, nc["zb"]), nc["zt"])) + off
            # fora da faixa: mistura de volta pro original
            if w.z < nc["zb"]: q = 1 - (nc["zb"] - w.z) / nc["feather"]
            elif w.z > nc["zt"]: q = 1 - (w.z - nc["zt"]) / nc["feather"]
            else: q = 1.0
            q = q * q * (3 - 2 * q)
            rn = r + (R - r) * q; k = rn / r
            w.x *= k; w.y = yc + (w.y - yc) * k; v.co = mi @ w; n += 1
        return n
    nh = conform(h, nc["head_off"], nc.get("head_skin_check", True)) if nc.get("move_head", True) else 0
    nj = conform(j, nc["body_off"], False)
    hb.free(); jb.free()
    print("NECK_CONFORM head", nh, "body", nj)

# Alarga o topo do pescoço do corpo em direção à mandíbula (encaixe mais natural com a cabeça)
nf2 = cfg.get("neck_top_flare")
if nf2:
    j = objs["jacket"]; n = 0
    for v in j.data.vertices:
        c = v.co
        if c.z > nf2["z_a"] and (c.x ** 2 + (c.y - nf2["yc"]) ** 2) ** 0.5 < nf2["r_max"]:
            u = min(1.0, (c.z - nf2["z_a"]) / (nf2["z_b"] - nf2["z_a"])); u = u * u * (3 - 2 * u)
            c.x *= 1 + (nf2["sx"] - 1) * u
            c.y = nf2["yc"] + (c.y - nf2["yc"]) * (1 + (nf2["sy"] - 1) * u); n += 1
    print("NECK_TOP_FLARE", n)

# Enfia a barra do top por baixo do cinto/calça
tk2 = cfg.get("top_tuck")
if tk2:
    import numpy as np
    j = objs["jacket"]; me = j.data
    img = [nd.image for m in me.materials for nd in m.node_tree.nodes if nd.type == "TEX_IMAGE" and nd.image][0]
    W, Hh = img.size; px = np.empty(W * Hh * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(Hh, W, 4)
    uvl = me.uv_layers.active.data; cloth = {}
    for lp in me.loops:
        u, v = uvl[lp.index].uv; c = px[int(v * Hh) % Hh, int(u * W) % W]
        cloth.setdefault(lp.vertex_index, []).append(not (c[0] > 0.35 and c[0] - c[2] > 0.12))
    n = 0
    for v in me.vertices:
        c = v.co; l = cloth.get(v.index, [False])
        if sum(l) <= len(l) / 2 or abs(c.x) > tk2["x_max"] or c.z > tk2["z_top"]: continue
        u = min(1.0, (tk2["z_top"] - c.z) / tk2["ramp"]); u = u * u * (3 - 2 * u)
        f = 1 + (tk2["f"] - 1) * u
        c.x *= f; c.y = tk2["yc"] + (c.y - tk2["yc"]) * f; n += 1
    print("TOP_TUCK", n)

# "Manta" preta por baixo do cabelo e do top: cópia encolhida, virada pra fora, cor preta.
ul = cfg.get("underlayer")
if ul:
    import numpy as np
    from mathutils import Vector
    for part, opt in ul.items():
        o = objs[part]; me = o.data
        img = [nd.image for m in me.materials for nd in m.node_tree.nodes if nd.type == "TEX_IMAGE" and nd.image][0]
        W, Hh = img.size; px = np.empty(W * Hh * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(Hh, W, 4)
        bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table(); uvl = bm.loops.layers.uv.active
        mw = o.matrix_world; mi = mw.inverted()
        sel = []
        for f in bm.faces:
            u, v = f.loops[0][uvl].uv; c = px[int(v * Hh) % Hh, int(u * W) % W]
            if c[:3].mean() < opt["lum_max"] and not (c[0] > 0.35 and c[0] - c[2] > 0.12):
                cz = (mw @ f.calc_center_median()).z
                cx = abs((mw @ f.calc_center_median()).x)
                if opt.get("z_min", -9) < cz < opt.get("z_max", 9) and cx < opt.get("x_max", 9): sel.append(f)
        mat = bpy.data.materials.new(part + "_underlayer_black"); mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF"); bsdf.inputs["Base Color"].default_value = opt.get("color", (0.01, 0.01, 0.012, 1)); bsdf.inputs["Roughness"].default_value = 0.8
        me.materials.append(mat); mi_idx = len(me.materials) - 1
        res = bmesh.ops.duplicate(bm, geom=sel); nf = [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)]
        nv = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
        for v in nv:
            w = mw @ v.co
            cen = Vector(opt["center"]) if opt["mode"] == "point" else Vector((0, opt["center"][1], w.z))
            d = w - cen
            if d.length > 1e-6: w = w - d.normalized() * opt["offset"]
            v.co = mi @ w
        for f in nf:
            f.material_index = mi_idx
            c = mw @ f.calc_center_median()
            cen = Vector(opt["center"]) if opt["mode"] == "point" else Vector((0, opt["center"][1], c.z))
            if (mw.to_3x3() @ f.normal).dot(c - cen) < 0: f.normal_flip()
        bm.to_mesh(me); bm.free()
        print("UNDERLAYER", part, len(nf))

# Troca de texturas corrigidas (tom de pele etc.)
for part, path in cfg.get("tex_override", {}).items():
    for m in objs[part].data.materials:
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image and n.label != "keep" and "basecolor" in n.image.name:
                n.image = bpy.data.images.load(path); n.image.name = part + "_basecolor_fix"
                print("TEX_OVERRIDE", part, path)

if "--nojoin" not in args:
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs.values(): o.select_set(True)
    bpy.context.view_layer.objects.active = objs["jacket"]
    bpy.ops.object.join()
    hero = bpy.context.view_layer.objects.active
    hero.name = hero.data.name = cfg["object_name"]
    coll = bpy.data.collections.new("EXPORT"); bpy.context.scene.collection.children.link(coll)
    for c in hero.users_collection: c.objects.unlink(hero)
    coll.objects.link(hero)
bpy.context.scene.unit_settings.system = "METRIC"
if "--pack" in args: bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out)
