"""Storyboard da abertura (A-074): 4 quadros com formas simples, só para mostrar os planos.

Roda no Blender (bpy 5.3), fora da Unreal:
  blender -b -P tools/blender/preview_intro.py -- --out assets/work/intro/previews [--fonte assets/raw/fonts/fredoka]
ou: python tools/blender/preview_intro.py --out ... (com o módulo bpy instalado)
Gera intro_0_start.png, intro_1_cabine.png, intro_2_queda.png, intro_4_heroi.png e intro_storyboard.png (os 4 juntos),
com as faixas de cinema, legendas e menu desenhados por cima (PIL), no estilo do AJRIntroHUD.
Não é a imagem do jogo: nave, herói e terreno são caixas e esferas.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS and ARGS.index(name) + 1 < len(ARGS) else default


OUT = os.path.abspath(opt("--out", "assets/work/intro/previews"))
FONT_DIR = opt("--fonte", "assets/raw/fonts/fredoka")
W, H = 960, 540
os.makedirs(OUT, exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 12
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 3
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -1.3
    world = bpy.data.worlds.new("Ceu")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    tex = nt.nodes.new("ShaderNodeTexSky") if False else None
    grad = nt.nodes.new("ShaderNodeTexGradient")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (0.95, 0.55, 0.45, 1)   # horizonte rosado
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (0.18, 0.12, 0.42, 1)   # céu roxo do planeta
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.7
    del tex, grad
    sun = bpy.data.lights.new("Sol", "SUN")
    sun.energy = 3.0
    sun.color = (1.0, 0.85, 0.75)
    so = bpy.data.objects.new("Sol", sun)
    so.rotation_euler = (math.radians(55), 0, math.radians(35))
    sc.collection.objects.link(so)
    return sc


def mat(name, color, emit=0.0, rough=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    if emit > 0:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


def obj_from(op, name, loc, scale=(1, 1, 1), rot=(0, 0, 0), m=None, **kw):
    op(location=loc, **kw)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.rotation_euler = [math.radians(a) for a in rot]
    if m:
        o.data.materials.append(m)
    return o


def terrain():
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=160, y_subdivisions=160, size=4000, location=(0, 0, 0))
    g = bpy.context.active_object
    for v in g.data.vertices:
        x, y = v.co.x, v.co.y
        v.co.z = (math.sin(x * 0.004) * 30 + math.cos(y * 0.005) * 25 + math.sin((x + y) * 0.011) * 6
                  + max(0.0, (abs(x) + abs(y)) - 1300) * 0.12)
    bpy.ops.object.shade_smooth()
    g.data.materials.append(mat("Chao", (0.20, 0.34, 0.30), rough=0.9))
    # pedras e arbustos cristalinos espalhados
    rnd = 7
    for i in range(60):
        rnd = (rnd * 1103515245 + 12345) % 2 ** 31
        a = (rnd % 3600) / 10.0
        r = 120 + (rnd % 900)
        x, y = math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r
        z = math.sin(x * 0.004) * 30 + math.cos(y * 0.005) * 25
        if i % 3 == 0:
            obj_from(bpy.ops.mesh.primitive_cone_add, f"Cristal{i}", (x, y, z), (2, 2, 6 + i % 5), m=CRISTAL, vertices=5)
        else:
            obj_from(bpy.ops.mesh.primitive_ico_sphere_add, f"Pedra{i}", (x, y, z), (4 + i % 6, 3 + i % 4, 2 + i % 3),
                     m=PEDRA, subdivisions=1)
    return g


def ship(name, loc, rot, broken=False):
    parts = []
    body = obj_from(bpy.ops.mesh.primitive_uv_sphere_add, name + "_Corpo", loc, (10, 3.2, 2.6), rot, NAVE, segments=24, ring_count=12)
    parts.append(body)
    wing = obj_from(bpy.ops.mesh.primitive_cube_add, name + "_Asa", loc, (3, 9, 0.3), rot, NAVE)
    parts.append(wing)
    cab = obj_from(bpy.ops.mesh.primitive_uv_sphere_add, name + "_Cabine", loc, (2.6, 1.8, 1.4), rot, VIDRO)
    # cabine na frente (+X local)
    rx, ry, rz = [math.radians(a) for a in rot]
    from mathutils import Euler
    fwd = Euler((rx, ry, rz)).to_matrix() @ Vector((6.5, 0, 1.6))
    cab.location = Vector(loc) + fwd
    parts.append(cab)
    if broken:
        tail = obj_from(bpy.ops.mesh.primitive_uv_sphere_add, name + "_Cauda", loc, (5, 2.8, 2.3), (rot[0] + 8, rot[1], rot[2] + 25),
                        NAVE, segments=20, ring_count=10)
        back = Euler((rx, ry, rz)).to_matrix() @ Vector((-14, 3, -0.6))
        tail.location = Vector(loc) + back
        parts.append(tail)
    return parts


def hero(loc, yaw):
    b = obj_from(bpy.ops.mesh.primitive_cylinder_add, "Heroi", (loc[0], loc[1], loc[2] + 0.9), (0.32, 0.32, 0.7), (0, 0, yaw),
                 HEROI, vertices=16)
    obj_from(bpy.ops.mesh.primitive_uv_sphere_add, "Cabeca", (loc[0], loc[1], loc[2] + 1.85), (0.24, 0.24, 0.26), m=PELE)
    return b


def fire(loc, s=1.0):
    obj_from(bpy.ops.mesh.primitive_ico_sphere_add, "Fogo", loc, (1.6 * s, 1.6 * s, 2.4 * s), m=FOGO, subdivisions=2)
    li = bpy.data.lights.new("FogoLuz", "POINT")
    li.energy = 60000 * s
    li.color = (1.0, 0.45, 0.12)
    lo = bpy.data.objects.new("FogoLuz", li)
    lo.location = (loc[0], loc[1], loc[2] + 2)
    bpy.context.scene.collection.objects.link(lo)


def camera(loc, look, lens=35):
    cd = bpy.data.cameras.new("Cam")
    cd.lens = lens
    cd.clip_end = 20000
    co = bpy.data.objects.new("Cam", cd)
    co.location = loc
    d = Vector(look) - Vector(loc)
    co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(co)
    bpy.context.scene.camera = co


def ground_z(x, y):
    return math.sin(x * 0.004) * 30 + math.cos(y * 0.005) * 25 + math.sin((x + y) * 0.011) * 6


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def build_materials():
    global NAVE, VIDRO, HEROI, PELE, FOGO, CRISTAL, PEDRA, FAISCA, ALARME
    NAVE = mat("Nave", (0.75, 0.77, 0.82), rough=0.35)
    VIDRO = mat("Vidro", (0.25, 0.85, 0.95), emit=1.5, rough=0.1)
    HEROI = mat("Heroi", (0.20, 0.35, 0.75))
    PELE = mat("Pele", (0.85, 0.62, 0.48))
    FOGO = mat("Fogo", (1.0, 0.35, 0.05), emit=6.0)
    CRISTAL = mat("Cristal", (0.30, 0.95, 0.90), emit=3.0, rough=0.2)
    PEDRA = mat("Pedra", (0.32, 0.30, 0.38), rough=0.9)
    FAISCA = mat("Faisca", (1.0, 0.5, 0.1), emit=12.0)
    ALARME = mat("Alarme", (1.0, 0.04, 0.02), emit=20.0)


SHIP_CRASH = (0.0, 0.0)


def shot_start():
    sc = reset()
    build_materials()
    terrain()
    camera((-900, -700, 420), (200, 300, 60), lens=24)
    render(os.path.join(OUT, "_raw_0.png"))


def shot_cabin():
    sc = reset()
    build_materials()
    terrain()
    loc = (300, -1200, 900)
    ship("Nave", loc, (0, 0, 60))
    li = bpy.data.lights.new("Alarme", "POINT")
    li.energy = 60000
    li.color = (1.0, 0.05, 0.03)
    lo = bpy.data.objects.new("Alarme", li)
    lo.location = (loc[0] + 3, loc[1] + 4, loc[2] + 6)
    sc.collection.objects.link(lo)
    obj_from(bpy.ops.mesh.primitive_uv_sphere_add, "Lampada", lo.location, (1.0, 1.0, 0.6), m=ALARME)
    # câmera na frente-direita do nariz, olhando a cabine
    fwd = Vector((math.cos(math.radians(60)), math.sin(math.radians(60)), 0))
    right = Vector((fwd.y, -fwd.x, 0))
    cam = Vector(loc) + fwd * 14 + right * 7 + Vector((0, 0, 3))
    camera(cam, Vector(loc) + fwd * 4 + Vector((0, 0, 1.2)), lens=32)
    render(os.path.join(OUT, "_raw_1.png"))


def shot_dive():
    sc = reset()
    build_materials()
    terrain()
    camp = (120, -260)
    cz = ground_z(*camp) + 2.2
    # nave descendo com fumaça/faíscas atrás
    p = Vector((-40, 120, 140))
    ship("Nave", p, (0, -28, 205))
    back = Vector((math.cos(math.radians(25)), math.sin(math.radians(25)), 0.55)).normalized()
    for i in range(24):
        q = p + back * (8 + i * 4.5) + Vector(((i * 37) % 7 - 3, (i * 53) % 7 - 3, (i * 29) % 5 - 2)) * 0.6
        obj_from(bpy.ops.mesh.primitive_ico_sphere_add, f"Faisca{i}", q, (1.4 - i * 0.04,) * 3, m=FAISCA, subdivisions=1)
    camera((camp[0], camp[1], cz), p, lens=60)
    render(os.path.join(OUT, "_raw_2.png"))


def shot_hero():
    sc = reset()
    build_materials()
    terrain()
    sx, sy = SHIP_CRASH
    sz = ground_z(sx, sy) + 2.0
    ship("NaveCaida", (sx, sy, sz), (-9, 17, 35), broken=True)
    for dx, dy in ((-4, -2), (5, 3), (-12, 6)):
        fire((sx + dx, sy + dy, sz + 1.5), 1.0)
    # herói ao lado da nave, do lado do acampamento, olhando para o acampamento (+Y)
    hx, hy = sx + 6, sy - 22
    hz = ground_z(hx, hy)
    hero((hx, hy, hz), 0)
    camera((hx + 2.2, hy - 7.5, hz + 1.3), (hx - 1.0, hy + 6, hz + 3.2), lens=28)
    render(os.path.join(OUT, "_raw_4.png"))


# ------------------------------------------------------------------ por cima (PIL), no estilo do AJRIntroHUD
def overlay():
    from PIL import Image, ImageDraw, ImageFont

    def font(bold, size):
        name = "Fredoka-Bold.ttf" if bold else "Fredoka-SemiBold.ttf"
        for d in (FONT_DIR, os.path.join(os.path.dirname(__file__), "..", "..", FONT_DIR)):
            p = os.path.join(d, name)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)

    ink, navy, yellow, soft, cyan, white = (12, 13, 32), (24, 30, 62), (255, 214, 92), (196, 206, 236), (90, 240, 246), (250, 250, 255)
    ui = H / 1080.0

    def center_text(d, y, text, f, fill):
        w = d.textlength(text, font=f)
        d.text(((W - w) / 2 + 2, y + 2), text, font=f, fill=(0, 0, 5, 160))
        d.text(((W - w) / 2, y), text, font=f, fill=fill)

    def pill(d, x, y, w, h, fill):
        d.rounded_rectangle([x, y, x + w, y + h], radius=h / 2, fill=fill)

    def letterbox(img):
        d = ImageDraw.Draw(img)
        bar = int(H * 0.11)
        d.rectangle([0, 0, W, bar], fill=(0, 0, 0, 255))
        d.rectangle([0, H - bar, W, H], fill=(0, 0, 0, 255))

    def subtitle(img, text):
        d = ImageDraw.Draw(img)
        f = font(True, int(34 * ui))
        tw = d.textlength(text, font=f)
        ph = 34 * ui * 1.7
        pw = tw + 90 * ui
        y = H * 0.76
        pill(d, (W - pw) / 2, y, pw, ph, navy + (235,))
        center_text(d, y + (ph - 34 * ui * 1.1) / 2, text, f, yellow)

    def skip(img, prog):
        d = ImageDraw.Draw(img)
        f = font(False, int(22 * ui))
        t = "Segure ESPAÇO ou A para pular"
        tw = d.textlength(t, font=f)
        x = W - 40 * ui - tw
        y = H - 40 * ui - 30 * ui
        d.text((x, y), t, font=f, fill=soft + (220,))
        d.rectangle([x, y + 22 * ui + 8, x + tw, y + 22 * ui + 8 + 5 * ui], fill=navy + (220,))
        d.rectangle([x, y + 22 * ui + 8, x + tw * prog, y + 22 * ui + 8 + 5 * ui], fill=cyan + (255,))

    def label(img, text):
        d = ImageDraw.Draw(img)
        f = font(True, 18)
        d.rectangle([0, 0, d.textlength(text, font=f) + 16, 28], fill=(0, 0, 0, 200))
        d.text((8, 4), text, font=f, fill=white)

    frames = []
    # 0: tela de start
    img = Image.open(os.path.join(OUT, "_raw_0.png")).convert("RGBA")
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle([0, 0, W, H], fill=ink + (90,))
    center_text(d, H * 0.17, "JOGO DE RESGATE", font(True, int(112 * ui)), yellow)
    center_text(d, H * 0.17 + 112 * ui * 1.2, "Fase 1: Vale dos Zumbis", font(False, int(32 * ui)), soft)
    items = ["Jogar", "Ver abertura", "Sair"]
    for i, it in enumerate(items):
        sel = i == 0
        g = 1.06 if sel else 1.0
        w_, h_ = 430 * ui * g, 78 * ui * g
        y = H * 0.50 + i * (78 + 22) * ui - (h_ - 78 * ui) / 2
        pill(d, (W - w_) / 2, y, w_, h_, (64, 214, 214, 255) if sel else navy + (235,))
        center_text(d, y + h_ * 0.18, it, font(True, int(40 * ui * g)), ink if sel else white)
    center_text(d, H - 70 * ui, "W/S ou setas: escolher     Enter, Espaço ou A: confirmar     Mouse: clique",
                font(False, int(22 * ui)), soft)
    img = Image.alpha_composite(img, ov)
    label(img, "Ato 0  tela de start (câmera girando devagar sobre o vale)")
    frames.append(img)

    for raw, sub, lab, prog in (("_raw_1.png", "ALERTA: falha no motor principal!", "Ato 1  cabine: alarme e luz vermelha (7 s)", 0.0),
                                ("_raw_2.png", "PERDA DE CONTROLE", "Ato 2  do acampamento: a nave cai soltando faíscas (10 s)", 0.35),
                                ("_raw_4.png", None, "Ato 4  nave caída pegando fogo, herói ao lado dá os primeiros passos (9 s)", 0.0)):
        img = Image.open(os.path.join(OUT, raw)).convert("RGBA")
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        letterbox(ov)
        if sub:
            subtitle(ov, sub)
        skip(ov, prog)
        img = Image.alpha_composite(img, ov)
        label(img, lab)
        frames.append(img)

    names = ["intro_0_start.png", "intro_1_cabine.png", "intro_2_queda.png", "intro_4_heroi.png"]
    for f_, n in zip(frames, names):
        f_.convert("RGB").save(os.path.join(OUT, n))
    sheet = Image.new("RGB", (W * 2 + 12, H * 2 + 12), (20, 20, 30))
    for i, f_ in enumerate(frames):
        sheet.paste(f_.convert("RGB"), ((i % 2) * (W + 12), (i // 2) * (H + 12)))
    sheet.save(os.path.join(OUT, "intro_storyboard.png"))
    for raw in ("_raw_0.png", "_raw_1.png", "_raw_2.png", "_raw_4.png"):
        try:
            os.remove(os.path.join(OUT, raw))
        except OSError:
            pass


if __name__ == "__main__":
    only = opt("--so", "0124")
    if "0" in only:
        shot_start()
    if "1" in only:
        shot_cabin()
    if "2" in only:
        shot_dive()
    if "4" in only:
        shot_hero()
    overlay()
    print("prévias em", OUT)
