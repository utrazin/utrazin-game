"""[A-098] Tufos de grama estilizada (cards cruzados, sem billboard) + textura de lâminas, para a cidade.

Uso (Blender 5.3, gera malhas FBX e a textura):
    blender -b --factory-startup --python tools/blender/gen_grass_tufts.py -- assets/work/grass
Só a textura (Python comum com numpy + Pillow, sem Blender):
    python tools/blender/gen_grass_tufts.py --tex-only assets/work/grass
Atalho no Windows: E:\\game\\gerar_grama.bat

Saída em <pasta>:
  SM_Grama_Tufo_0.fbx  curta e densa (~30 cm), 3 cards
  SM_Grama_Tufo_1.fbx  média (~50 cm), 3 cards
  SM_Grama_Tufo_2.fbx  alta e rala (~75 cm), 3 cards + 1 card curto no meio
  T_Grama_Laminas.png  RGBA 1024 x 1024, ladrilha na horizontal. NÃO é cor: é dado (sRGB desligado na Unreal)
                       R = altura dentro da lâmina (0 base, 1 ponta), G = sorteio por lâmina (variação de cor),
                       B = sombreado cartunesco (lado claro 1,0 / lado da dobra 0,72), A = recorte
  grass_tufts.json     medidas de cada tufo

Regras dos tufos (pesquisa A-098):
  - 3 quads cruzados a 0/60/120 graus, cada um curvado (arco na horizontal e para fora no alto): nada de "PNG reto"
  - NORMAIS TODAS PARA CIMA (0, 0, 1): a lâmina pega a mesma luz do chão, sem lado escuro
  - pivô na base, base 3 cm abaixo de zero (não flutua em desnível)
  - UV: V vai de 0 (base) a 1 (ponta) em todo card (o material usa 1 - V da Unreal como peso do vento);
        U cobre largura/altura do card (a textura ladrilha, a lâmina mantém a proporção)
Funções puras (textura e geometria) não usam bpy; bpy só em build_blender().
"""
from __future__ import annotations

import json
import math
import os
import random
import sys

TEX_SIZE = 1024
SEED = 9821
# nome: (altura cm, largura cm, cards, inclinação para fora, arco)
TUFTS = {
    "SM_Grama_Tufo_0": {"h": 30.0, "w": 42.0, "cards": 3, "lean": 0.18, "bow": 0.10, "extra": False},
    "SM_Grama_Tufo_1": {"h": 50.0, "w": 58.0, "cards": 3, "lean": 0.22, "bow": 0.12, "extra": False},
    "SM_Grama_Tufo_2": {"h": 75.0, "w": 62.0, "cards": 3, "lean": 0.26, "bow": 0.14, "extra": True},
}
NX, NZ = 4, 5  # subdivisões por card (curva lisa, nada facetado)


# ------------------------------------------------------------------ textura (numpy puro)
def blade_texture(size=TEX_SIZE, seed=SEED, n_blades=95):
    """Lâminas curvas e afinadas, ladrilháveis em X. Devolve array uint8 (size, size, 4)."""
    import numpy as np

    rng = random.Random(seed)
    H = W = size
    img = np.zeros((H, W, 4), np.float32)
    xs = np.arange(W, dtype=np.float32)
    blades = []
    for _ in range(n_blades):
        blades.append({
            "x0": rng.uniform(0, W), "h": rng.uniform(0.5, 0.985) * H, "lean": rng.uniform(-0.22, 0.22),
            "w0": rng.uniform(0.03, 0.055) * W, "g": rng.random(), "curl": rng.uniform(1.6, 2.6),
        })
    blades.sort(key=lambda b: -b["h"])  # altas atrás, curtas na frente
    base_y = H - 1.0
    for b in blades:
        y_top = int(max(0, base_y - b["h"]))
        for y in range(y_top, H):
            t = (base_y - y) / b["h"]  # 0 base, 1 ponta
            if t < 0 or t > 1:
                continue
            c = b["x0"] + b["lean"] * b["h"] * (t ** b["curl"])
            hw = 0.5 * b["w0"] * ((1.0 - t) ** 0.6)
            if hw < 0.35:
                continue
            for shift in (-W, 0.0, W):  # ladrilha em X
                d = xs - (c + shift)
                cov = np.clip(hw - np.abs(d) + 0.5, 0.0, 1.0)
                m = cov > 0
                if not m.any():
                    continue
                shade = np.where(d < 0, 1.0, 0.72)  # dobra da lâmina: um lado claro, outro escuro
                a = cov[m]
                row = img[y, m]
                row[:, 0] = row[:, 0] * (1 - a) + t * a
                row[:, 1] = row[:, 1] * (1 - a) + b["g"] * a
                row[:, 2] = row[:, 2] * (1 - a) + shade[m] * a
                row[:, 3] = np.maximum(row[:, 3], a)
                img[y, m] = row
    # "sangra" a cor para dentro do transparente (sem borda escura nos mips)
    rgb, alpha = img[..., :3].copy(), img[..., 3]
    filled = alpha > 0.02
    for _ in range(24):
        if filled.all():
            break
        acc = np.zeros_like(rgb)
        cnt = np.zeros(alpha.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh_f = np.roll(np.roll(filled, dy, 0), dx, 1)
            sh_c = np.roll(np.roll(rgb, dy, 0), dx, 1)
            acc += sh_c * sh_f[..., None]
            cnt += sh_f
        new = (~filled) & (cnt > 0)
        rgb[new] = acc[new] / cnt[new][:, None]
        filled = filled | new
    out = np.concatenate([rgb, alpha[..., None]], -1)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


# ------------------------------------------------------------------ geometria (pura)
def card_vertices(angle_deg, w, h, lean, bow, offset, u0, flip):
    """Grade (NX+1) x (NZ+1) de um card curvado. Devolve (verts, uvs) em metros."""
    a = math.radians(angle_deg)
    ax, ay = math.cos(a), math.sin(a)       # eixo do card
    nx, ny = -ay, ax                         # normal geométrica (só para curvar; a normal final é para cima)
    sgn = -1.0 if flip else 1.0
    verts, uvs = [], []
    for j in range(NZ + 1):
        t = j / NZ
        for i in range(NX + 1):
            s = i / NX - 0.5
            out = sgn * (lean * h * t * t + bow * w * (4 * s * s - 1) * 0.5 * (0.4 + 0.6 * t))
            spread = 1.0 + 0.18 * t          # abre um pouco no alto (cara de tufo)
            x = offset[0] + ax * s * w * spread + nx * out
            y = offset[1] + ay * s * w * spread + ny * out
            z = -0.03 + h * t * (1.0 - 0.06 * t * t)
            verts.append((x, y, z))
            uvs.append((u0 + (s + 0.5) * (w / h), t))
    return verts, uvs


def tuft_geometry(spec, seed):
    rng = random.Random(seed)
    h, w = spec["h"] / 100.0, spec["w"] / 100.0
    cards = []
    base_angle = rng.uniform(0, 60)
    for k in range(spec["cards"]):
        ang = base_angle + k * 60.0 + rng.uniform(-8, 8)
        off = (rng.uniform(-0.04, 0.04) * w, rng.uniform(-0.04, 0.04) * w)
        cards.append(card_vertices(ang, w * rng.uniform(0.9, 1.05), h * rng.uniform(0.9, 1.04), spec["lean"],
                                   spec["bow"], off, rng.random() * 3.0, k % 2 == 1))
    if spec.get("extra"):
        cards.append(card_vertices(base_angle + 30, w * 0.6, h * 0.55, spec["lean"] * 0.5, spec["bow"], (0, 0),
                                   rng.random() * 3.0, False))
    return cards


# ------------------------------------------------------------------ Blender
def build_blender(out_dir):
    import bpy  # noqa: WPS433 (bpy só aqui)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    report = {}
    for idx, (name, spec) in enumerate(TUFTS.items()):
        cards = tuft_geometry(spec, SEED + idx * 17)
        verts, faces, uvs = [], [], []
        for cv, cu in cards:
            base = len(verts)
            verts += cv
            for j in range(NZ):
                for i in range(NX):
                    a = base + j * (NX + 1) + i
                    faces.append((a, a + 1, a + NX + 2, a + NX + 1))
            uvs.append(cu)
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        me.update()
        uv = me.uv_layers.new(name="UVMap")
        flat_uv = [u for cu in uvs for u in cu]
        for poly in me.polygons:
            for li in poly.loop_indices:
                uv.data[li].uv = flat_uv[me.loops[li].vertex_index]
        for poly in me.polygons:
            poly.use_smooth = True
        me.normals_split_custom_set([(0.0, 0.0, 1.0)] * len(me.loops))  # normais para cima
        mat = bpy.data.materials.get("M_Grama_Tufo") or bpy.data.materials.new("M_Grama_Tufo")
        me.materials.append(mat)
        obj = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(obj)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        path = os.path.join(out_dir, f"{name}.fbx")
        kw = dict(filepath=path, use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL",
                  axis_forward="X", axis_up="Z", object_types={"MESH"}, mesh_smooth_type="OFF",
                  use_mesh_modifiers=True, add_leaf_bones=False, bake_space_transform=False)
        bpy.ops.export_scene.fbx(**kw)
        report[name] = {"tris": len(faces) * 2, "verts": len(verts), "h_cm": spec["h"], "w_cm": spec["w"],
                        "cards": len(cards)}
        print(f"[grama] {name}: {len(faces) * 2} triângulos -> {path}")
        bpy.data.objects.remove(obj, do_unlink=True)
    save_texture_blender(out_dir)
    return report


def save_texture_blender(out_dir):
    import bpy
    import numpy as np

    arr = blade_texture()
    img = bpy.data.images.new("T_Grama_Laminas", TEX_SIZE, TEX_SIZE, alpha=True, float_buffer=False)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set((np.flipud(arr).astype(np.float32) / 255.0).ravel())  # Blender guarda de baixo para cima
    img.filepath_raw = os.path.join(out_dir, "T_Grama_Laminas.png")
    img.file_format = "PNG"
    img.save()
    print("[grama] T_Grama_Laminas.png salva")


def save_texture_pil(out_dir):
    from PIL import Image

    Image.fromarray(blade_texture(), "RGBA").save(os.path.join(out_dir, "T_Grama_Laminas.png"))
    print("[grama] T_Grama_Laminas.png salva (Pillow)")


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    args = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    tex_only = "--tex-only" in args
    args = [a for a in args if not a.startswith("--")]
    out_dir = os.path.abspath(args[0] if args else os.path.join(os.path.dirname(__file__), "..", "..", "assets", "work", "grass"))
    os.makedirs(out_dir, exist_ok=True)
    if tex_only:
        save_texture_pil(out_dir)
        return 0
    report = build_blender(out_dir)
    with open(os.path.join(out_dir, "grass_tufts.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print("[grama] fim")
    return 0


if __name__ == "__main__":
    code = main(sys.argv)
    if "bpy" not in sys.modules:
        sys.exit(code)
