"""Ícones do HUD v2 (roda de itens, cartão da arma, cura): renders 3/4 dos modelos do jogo, fundo transparente.

Fontes: assets/raw/tripo/ARM_*.glb e ITM_*.glb (modelos do usuário), assets/work/weapons/SM_AlienPistol.fbx.
Mão ("Nada"), bandagem, raio da Fúria e cadeado são modelados aqui mesmo (formas simples de "argila").
Saída: assets/work/ui/v2/icons_raw/<Nome>.png (512 px). O contorno escuro e a sombra entram em
tools/pipeline/make_hud_v2.py.

Uso (Blender 5.x, Cycles na CPU):
  blender -b --python tools/blender/render_hud_icons.py -- [pasta_saida] [resolucao] [amostras] [Nome1,Nome2]
"""
import math
import os
import sys

import bpy  # noqa: I001 (bpy antes de bmesh/mathutils no módulo pip)
import bmesh
import mathutils

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
U = REPO + "/"

def setup_scene(res=512, samples=48):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    try:
        sc.cycles.use_denoising = True
    except Exception: pass
    sc.render.resolution_x = res; sc.render.resolution_y = res
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    w = bpy.data.worlds.new('W'); sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.55, 0.55, 0.75, 1); bg.inputs[1].default_value = 0.65
def load(path):
    if path.endswith('.glb'): bpy.ops.import_scene.gltf(filepath=path)
    else: bpy.ops.import_scene.fbx(filepath=path)
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in objs:
        for s in o.material_slots:
            m = s.material
            if m and m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type == 'BSDF_PRINCIPLED':
                        n.inputs['Roughness'].default_value = 0.55
                        if 'Metallic' in n.inputs:
                            if not n.inputs['Metallic'].is_linked: n.inputs['Metallic'].default_value = min(n.inputs['Metallic'].default_value, 0.3)
    return objs
def bbox(objs):
    mn = mathutils.Vector((1e9,) * 3); mx = -mn
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            mn = mathutils.Vector(map(min, mn, w)); mx = mathutils.Vector(map(max, mx, w))
    return mn, mx
def pivot(objs, rot_deg):
    """Gira o conjunto em torno do centro (graus XYZ)."""
    e = bpy.data.objects.new('Pivot', None); bpy.context.scene.collection.objects.link(e)
    mn, mx = bbox(objs); e.location = (mn + mx) / 2
    for o in objs:
        if o.parent is None:
            mw = o.matrix_world.copy(); o.parent = e; o.matrix_world = mw
    bpy.context.view_layer.update()
    e.rotation_euler = [math.radians(v) for v in rot_deg]
    bpy.context.view_layer.update()
def camera_fit(objs, margin=1.12):
    mn, mx = bbox(objs); c = (mn + mx) / 2; size = mx - mn
    cam = bpy.data.cameras.new('C'); cam.type = 'ORTHO'
    co = bpy.data.objects.new('C', cam); bpy.context.scene.collection.objects.link(co)
    co.location = (c.x, c.y - 10, c.z); co.rotation_euler = (math.radians(90), 0, 0)
    cam.ortho_scale = max(size.x, size.z) * margin
    cam.clip_end = 100
    bpy.context.scene.camera = co
    # luzes: principal de cima/esquerda, recorte atrás à direita, preenchimento frio
    def light(name, typ, energy, loc, rot, color=(1, 1, 1), size=2.0):
        l = bpy.data.lights.new(name, typ); l.energy = energy; l.color = color
        if typ == 'AREA': l.size = size
        o = bpy.data.objects.new(name, l); bpy.context.scene.collection.objects.link(o)
        o.location = c + mathutils.Vector(loc); o.rotation_euler = [math.radians(v) for v in rot]
    light('Key', 'AREA', 260, (-3, -4, 4), (50, 0, -35), (1, 0.96, 0.9), 3)
    light('Rim', 'AREA', 280, (3, 3, 2.5), (-60, 0, 140), (0.6, 0.9, 1.0), 2)
    light('Fill', 'AREA', 80, (3, -4, -1), (100, 0, 35), (0.8, 0.7, 1.0), 4)
    return co
def render(out):
    bpy.context.scene.render.filepath = out
    bpy.ops.render.render(write_still=True)

OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else os.path.join(REPO, 'assets', 'work', 'ui', 'v2', 'icons_raw')
RES = int(sys.argv[sys.argv.index('--') + 2]) if '--' in sys.argv else 512
SAMPLES = int(sys.argv[sys.argv.index('--') + 3]) if '--' in sys.argv else 64
ONLY = sys.argv[sys.argv.index('--') + 4].split(',') if '--' in sys.argv and len(sys.argv) > sys.argv.index('--') + 4 else None
os.makedirs(OUT, exist_ok=True)

def mat(name, color, rough=0.5, emit=None, emit_str=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1); p.inputs['Roughness'].default_value = rough
    if emit:
        p.inputs['Emission Color'].default_value = (*emit, 1); p.inputs['Emission Strength'].default_value = emit_str
    return m

def bevel_mod(o, w=0.02, seg=4):
    b = o.modifiers.new('B', 'BEVEL'); b.width = w; b.segments = seg; b.limit_method = 'ANGLE'
    o.modifiers.new('S', 'WEIGHTED_NORMAL')

def smooth(o):
    for p in o.data.polygons: p.use_smooth = True

def capsule(a, b, r, m):
    a = mathutils.Vector(a); b = mathutils.Vector(b)
    d = b - a; L = d.length
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=L, vertices=32, location=(a + b) / 2)
    c = bpy.context.object
    c.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    objs = [c]
    for p in (a, b):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=p, segments=32, ring_count=16)
        objs.append(bpy.context.object)
    for o in objs:
        smooth(o); o.data.materials.append(m)
    return objs

def make_hand():
    skin = mat('Skin', (0.80, 0.45, 0.30), 0.6)
    objs = []
    # palma (cubo arredondado)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    p = bpy.context.object; p.scale = (0.9, 0.32, 0.95); bpy.ops.object.transform_apply(scale=True)
    bv = p.modifiers.new('B', 'BEVEL'); bv.width = 0.14; bv.segments = 8
    sub = p.modifiers.new('Sub', 'SUBSURF'); sub.levels = 2; sub.render_levels = 2
    smooth(p); p.data.materials.append(skin); objs.append(p)
    # dedos (indicador..mindinho), abertos em leque
    fingers = [(-0.33, 1.05, -10), (-0.11, 1.18, -3), (0.11, 1.12, 4), (0.32, 0.92, 12)]
    for x, L, tilt in fingers:
        t = math.radians(tilt)
        base = (x, 0, 0.42); tip = (x + math.sin(t) * L, 0, 0.42 + math.cos(t) * L)
        objs += capsule(base, tip, 0.13, skin)
    # polegar
    objs += capsule((-0.42, 0, -0.1), (-0.95, 0, 0.35), 0.15, skin)
    return objs

def make_bandage():
    cream = mat('Band', (0.95, 0.92, 0.85), 0.75)
    stripe = mat('Stripe', (0.85, 0.3, 0.3), 0.6)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.6, depth=0.7, vertices=64, location=(0, 0, 0))
    r = bpy.context.object; r.rotation_euler = (math.radians(90), 0, 0)
    bevel_mod(r, 0.08, 6); smooth(r); r.data.materials.append(cream)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.72, vertices=48, location=(0, 0, 0))
    h = bpy.context.object; h.rotation_euler = (math.radians(90), 0, 0)
    h.data.materials.append(mat('Hole', (0.35, 0.3, 0.28), 0.8)); smooth(h)
    # faixa vermelha
    bpy.ops.mesh.primitive_torus_add(major_radius=0.6, minor_radius=0.045, location=(0, 0.18, 0))
    s1 = bpy.context.object; s1.rotation_euler = (math.radians(90), 0, 0); s1.data.materials.append(stripe); smooth(s1)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.6, minor_radius=0.045, location=(0, -0.18, 0))
    s2 = bpy.context.object; s2.rotation_euler = (math.radians(90), 0, 0); s2.data.materials.append(stripe); smooth(s2)
    # ponta solta: tira curva
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0.42, 0, -0.66))
    t = bpy.context.object; t.scale = (0.85, 0.62, 1); t.rotation_euler = (0, math.radians(14), 0)
    sol = t.modifiers.new('Sol', 'SOLIDIFY'); sol.thickness = 0.03
    t.data.materials.append(cream)
    return [r, h, s1, s2, t]

def make_bolt():
    m = mat('Bolt', (0.75, 0.15, 1.0), 0.3, (0.6, 0.1, 1.0), 0.8)
    pts = [(0.15, 1.0), (-0.45, -0.05), (-0.02, -0.05), (-0.25, -1.0), (0.5, 0.2), (0.05, 0.2), (0.35, 1.0)]
    me = bpy.data.meshes.new('B'); bm = bmesh.new()
    vs = [bm.verts.new((x, 0, y)) for x, y in pts]; f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f]); 
    for v in [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]: v.co.y += 0.22
    bm.to_mesh(me); o = bpy.data.objects.new('Bolt', me); bpy.context.scene.collection.objects.link(o)
    bv = o.modifiers.new('B', 'BEVEL'); bv.width = 0.06; bv.segments = 6
    o.data.materials.append(m)
    return [o]

def make_lock():
    gold = mat('Lock', (0.95, 0.55, 0.06), 0.35)
    steel = mat('Steel', (0.75, 0.75, 0.85), 0.3)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -0.3))
    b = bpy.context.object; b.scale = (1.0, 0.45, 0.8); bpy.ops.object.transform_apply(scale=True)
    bv = b.modifiers.new('B', 'BEVEL'); bv.width = 0.16; bv.segments = 8
    smooth(b); b.data.materials.append(gold)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.33, minor_radius=0.09, location=(0, 0, 0.18), major_segments=48)
    s = bpy.context.object; s.rotation_euler = (math.radians(90), 0, 0); smooth(s); s.data.materials.append(steel)
    # buraco da chave
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.1, location=(0, -0.23, -0.25))
    k = bpy.context.object; k.rotation_euler = (math.radians(90), 0, 0); k.data.materials.append(mat('K', (0.15, 0.1, 0.05), 0.8))
    return [b, s, k]

def make_ammo():
    return load(U + 'assets/raw/tripo/ITM_Municao.glb')

JOBS = {
    # nome: (fonte, rotação ZXY em graus (az, elev, roll) )
    'Pistol':   (U + 'assets/work/weapons/SM_AlienPistol.fbx', (20, 10, -18)),
    'Shotgun':  (U + 'assets/raw/tripo/ARM_Escopeta.glb', (20, 10, -22)),
    'Sniper':   (U + 'assets/raw/tripo/ARM_Sniper.glb', (18, 10, -18)),
    'Stick':    (U + 'assets/raw/tripo/ARM_Graveto.glb', (90, 0, 48)),
    'Medkit':   (U + 'assets/raw/tripo/ITM_KitMedico.glb', (300, 14, 0)),
    'CarKey':   (U + 'assets/raw/tripo/ITM_Chave.glb', (285, 8, -12)),
    'Fuel':     (U + 'assets/raw/tripo/ITM_Galao.glb', (300, 10, 0)),
    'Explosive':(U + 'assets/raw/tripo/ITM_Explosivo.glb', (300, 10, 0)),
    'Hand':     (make_hand, (8, 0, -12)),
    'Bandage':  (make_bandage, (-25, 18, 0)),
    'Fury':     (make_bolt, (0, 0, -8)),
    'Lock':     (make_lock, (-18, 12, 0)),
}
for name, (src, rot) in JOBS.items():
    if ONLY and name not in ONLY: continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    setup_scene(RES, SAMPLES)
    objs = load(src) if isinstance(src, str) else src()
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    e = bpy.data.objects.new('Pivot', None); bpy.context.scene.collection.objects.link(e)
    mn, mx = bbox(objs); e.location = (mn + mx) / 2
    bpy.context.view_layer.update()
    for o in objs:
        if o.parent is None:
            mw = o.matrix_world.copy(); o.parent = e; o.matrix_world = mw
    e.rotation_mode = 'ZXY'
    e.rotation_euler = (math.radians(rot[1]), math.radians(rot[2]), math.radians(rot[0]))
    bpy.context.view_layer.update()
    camera_fit(objs, 1.08)
    render(f'{OUT}/{name}.png')
