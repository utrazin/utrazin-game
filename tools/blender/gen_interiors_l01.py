#!/usr/bin/env python3
"""Construções com interior da Fase 1 (A-070): cascas ocas, móveis e prévias, feitos no Blender (bpy 5.3).

Uso (Blender sem interface ou Python com o módulo bpy):
  python tools/blender/gen_interiors_l01.py [saida] [--only PostoLoja,CasaVila] [--no-render] [--no-export]
  (saida padrão: assets/work/interiors)
Grava em <saida>:
  SM_INT_<Predio>.fbx       casca da construção (paredes 20 cm, vãos de porta e janela, vidro, batentes, piso,
                            teto/telhado) com caixas de colisão UCX_ por parede (o vão da porta fica livre)
  SM_INT_<Movel>.fbx        móveis da biblioteca (prateleira, balcão, geladeira, cama, mesa...), com UCX_
  interiors_l01.json        para tools/unreal/build_interiors_l01.py: tamanhos, móveis, itens, luzes, zona de
                            câmera, portas, o que cada prédio substitui no mapa
  previews/<Predio>_*.png   prévias: fora (3/4), corte de cima sem teto e olho do herói (170 cm) de dentro
Coordenadas de cada prédio: metros, origem no centro do piso, +X = frente (porta principal), +Y = esquerda,
Z para cima (igual à Unreal com x frente; o build gira pelo yaw). Materiais com o nome das texturas repetíveis
do usuário (MI_User_<Nome>, projeção alinhada ao mundo na Unreal), então não dependem de UV.
Regras (skill enterable-interior): porta >= 1,2 x 2,2 m; pé-direito >= 2,8 m; corredor >= 1,5 m; cada cômodo
com 1 interação, 3+ objetos de contexto e um ponto focal visível da porta; luzes fracas em candelas.
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy
from mathutils import Vector

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TEX_DIR = os.path.join(REPO, "assets", "work", "textures", "user")
WALL_T = 0.2
TILE_M = {"Tijolo": 2.5, "Reboco": 4.0, "MadeiraPiso": 3.0, "Concreto": 4.0, "MetalOndulado": 3.0,
          "VidroSujo": 2.0, "TelhaCeramica": 2.5, "MadeiraTabuas": 3.0, "MadeiraVelha": 3.0, "Asfalto": 6.0,
          "MetalAlien": 3.0, "Lona": 3.0}
# cores lisas dos móveis (estilo low-poly da Quaternius): nome -> (r, g, b, rugosidade, emissão)
FLAT = {"Pintura": (0.78, 0.80, 0.84, 0.6, 0), "Metal": (0.42, 0.45, 0.50, 0.35, 0), "Escuro": (0.10, 0.11, 0.14, 0.5, 0),
        "Vermelho": (0.72, 0.16, 0.14, 0.5, 0), "Azul": (0.16, 0.34, 0.68, 0.5, 0), "Amarelo": (0.95, 0.70, 0.15, 0.5, 0),
        "Verde": (0.20, 0.55, 0.30, 0.5, 0), "Laranja": (0.92, 0.45, 0.12, 0.5, 0), "Branco": (0.92, 0.92, 0.90, 0.4, 0),
        "Tecido": (0.30, 0.36, 0.55, 0.9, 0), "Couro": (0.40, 0.20, 0.12, 0.7, 0), "Colchao": (0.85, 0.82, 0.74, 0.9, 0),
        "Tela": (0.10, 0.70, 0.75, 0.3, 2.0), "Geladeira": (0.70, 0.90, 1.00, 0.1, 0.6), "Cristal": (0.30, 0.95, 0.90, 0.2, 3.0),
        "Lampada": (1.00, 0.90, 0.70, 0.3, 6.0), "Borracha": (0.06, 0.06, 0.07, 0.8, 0), "Papel": (0.90, 0.87, 0.78, 0.9, 0),
        "Brasa": (1.00, 0.42, 0.10, 0.6, 5.0), "Lixo": (0.32, 0.28, 0.22, 0.95, 0)}

# ====================================================================== cena e materiais

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    return sc


_MATS = {}


def tex_mat(name):
    """Material com a textura repetível do usuário (projeção em caixa, ladrilho TILE_M) chamado MI_User_<Nome>."""
    key = f"MI_User_{name}"
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    path = os.path.join(TEX_DIR, f"T_User_{name}_D.png")
    if os.path.exists(path):
        img = bpy.data.images.load(path, check_existing=True)
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        s = 1.0 / TILE_M.get(name, 3.0)
        mp.inputs["Scale"].default_value = (s, s, s)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        ti = nt.nodes.new("ShaderNodeTexImage")
        ti.image = img
        ti.projection = "BOX"
        ti.projection_blend = 0.25
        nt.links.new(mp.outputs["Vector"], ti.inputs["Vector"])
        nt.links.new(ti.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.15 if name == "VidroSujo" else 0.85
    # cor média da textura (vista rápida/planta no Workbench, que não lê a projeção em caixa)
    try:
        from PIL import Image as _PILImage
        im = _PILImage.open(path).convert("RGB").resize((16, 16))
        px = list(im.getdata())
        m.diffuse_color = tuple(sum(c[i] for c in px) / len(px) / 255.0 for i in range(3)) + (1.0,)
    except Exception:  # noqa: BLE001
        pass
    if name == "VidroSujo":
        bsdf.inputs["Alpha"].default_value = 0.35
        m.blend_method = "BLEND" if hasattr(m, "blend_method") else m.blend_method
    _MATS[key] = m
    return m


def flat_mat(name):
    key = f"M_INT_{name}"
    if key in _MATS:
        return _MATS[key]
    r, g, b, rough, emit = FLAT[name]
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1)
    m.diffuse_color = (r, g, b, 1)
    bsdf.inputs["Roughness"].default_value = rough
    if name == "Metal":
        bsdf.inputs["Metallic"].default_value = 0.8
    if emit:
        bsdf.inputs["Emission Color"].default_value = (r, g, b, 1)
        bsdf.inputs["Emission Strength"].default_value = emit
    _MATS[key] = m
    return m


def mat(name):
    return tex_mat(name) if name in TILE_M else flat_mat(name)


# ====================================================================== geometria básica

class Builder:
    """Junta caixas (e cilindros) de um objeto num mesh só, com um slot por material, e guarda caixas de colisão."""

    def __init__(self, name):
        self.name = name
        self.verts, self.faces, self.face_mat = [], [], []
        self.mats = []
        self.colliders = []      # (centro, tamanho, rot_z)
        self.hulls = []          # colisores convexos: lista de vértices (rampas)

    def _mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def box(self, c, s, m, rot=0.0, collide=False, mat_out=None, center_xy=(0.0, 0.0)):
        """Caixa de centro c e tamanho s. mat_out: material das faces viradas para fora do prédio."""
        cx, cy, cz = c
        hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
        co, si = math.cos(rot), math.sin(rot)
        base = len(self.verts)
        for dz in (-hz, hz):
            for dx, dy in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)):
                self.verts.append((cx + dx * co - dy * si, cy + dx * si + dy * co, cz + dz))
        quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        normals = [(0, 0, -1), (0, 0, 1), (si * 1, -co, 0), (co, si, 0), (-si, co, 0), (-co, -si, 0)]
        for q, nrm in zip(quads, normals):
            self.faces.append(tuple(base + i for i in q))
            use = m
            if mat_out is not None and abs(nrm[2]) < 0.5:
                # face lateral: para fora do prédio = mesma direção do centro da face menos o centro do prédio
                fc = Vector((cx, cy)) + Vector((nrm[0], nrm[1])) * 0.01
                out = Vector((fc.x - center_xy[0], fc.y - center_xy[1]))
                if out.length > 0 and out.normalized().dot(Vector((nrm[0], nrm[1]))) > 0.3:
                    use = mat_out
            self.face_mat.append(self._mi(use))
        if collide:
            self.colliders.append((c, s, rot))

    def cyl(self, c, r, h, m, n=12, collide=False, axis="Z"):
        cx, cy, cz = c
        base = len(self.verts)
        for k in (0, 1):
            for i in range(n):
                a = 2 * math.pi * i / n
                u, v, w = r * math.cos(a), r * math.sin(a), (k - 0.5) * h
                p = (u, v, w) if axis == "Z" else ((w, u, v) if axis == "X" else (u, w, v))
                self.verts.append((cx + p[0], cy + p[1], cz + p[2]))
        mi = self._mi(m)
        for i in range(n):
            j = (i + 1) % n
            self.faces.append((base + i, base + j, base + n + j, base + n + i))
            self.face_mat.append(mi)
        self.faces.append(tuple(base + i for i in reversed(range(n))))
        self.face_mat.append(mi)
        self.faces.append(tuple(base + n + i for i in range(n)))
        self.face_mat.append(mi)
        if collide:
            d = 2 * r
            self.colliders.append((c, (d, d, h) if axis == "Z" else ((h, d, d) if axis == "X" else (d, h, d)), 0.0))

    def tri_prism(self, a, b, h_apex, apex_off, thick, z0, m):
        """Empena (triângulo) da parede entre os pontos a e b, de z0 até z0 + h_apex, com espessura."""
        ax, ay = a
        bx, by = b
        d = Vector((bx - ax, by - ay))
        n = Vector((-d.y, d.x)).normalized() * (thick / 2)
        mid = Vector(((ax + bx) / 2, (ay + by) / 2)) + d.normalized() * apex_off
        base = len(self.verts)
        for s in (-1, 1):
            o = n * s
            self.verts += [(ax + o.x, ay + o.y, z0), (bx + o.x, by + o.y, z0), (mid.x + o.x, mid.y + o.y, z0 + h_apex)]
        mi = self._mi(m)
        for f in ((0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)):
            self.faces.append(tuple(base + i for i in f))
            self.face_mat.append(mi)

    def wedge(self, base0, base1, depth, drop, m, collide=True):
        """Rampa: a borda alta vai de base0 a base1 (no nível do piso, encostada na parede) e desce `drop` metros
        ao longo de `depth` metros para fora (direção perpendicular, para longe do centro do prédio)."""
        a, b = Vector(base0), Vector(base1)
        d = (b - a).normalized()
        out = Vector((d.y, -d.x)) if Vector((d.y, -d.x)).dot((a + b) / 2) > 0 else Vector((-d.y, d.x))
        a2, b2 = a + out * depth, b + out * depth
        z0, z1 = -0.02, -drop
        pts = [(a.x, a.y, z0), (b.x, b.y, z0), (b2.x, b2.y, z1), (a2.x, a2.y, z1),
               (a.x, a.y, z1 - 0.3), (b.x, b.y, z1 - 0.3), (b2.x, b2.y, z1 - 0.3), (a2.x, a2.y, z1 - 0.3)]
        base = len(self.verts)
        self.verts += pts
        mi = self._mi(m)
        for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 3, 7, 4), (1, 5, 6, 2), (0, 4, 5, 1), (3, 2, 6, 7)):
            self.faces.append(tuple(base + i for i in f))
            self.face_mat.append(mi)
        if collide:
            self.hulls.append(pts)

    def quad(self, pts, m):
        base = len(self.verts)
        self.verts += [tuple(p) for p in pts]
        self.faces.append(tuple(base + i for i in range(len(pts))))
        self.face_mat.append(self._mi(m))

    def build(self, collection=None, loc=(0, 0, 0)):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata(self.verts, [], self.faces)
        me.update()
        for m in self.mats:
            me.materials.append(m)
        for poly, mi in zip(me.polygons, self.face_mat):
            poly.material_index = mi
        ob = bpy.data.objects.new(self.name, me)
        ob.location = loc
        (collection or bpy.context.scene.collection).objects.link(ob)
        cols = []
        for i, (c, s, rot) in enumerate(self.colliders):
            cb = Builder(f"UCX_{self.name}_{i:02d}")
            cb.box(c, s, flat_mat("Escuro"), rot)
            co, _ = cb.build(collection, loc)
            co.data.materials.clear()
            co.display_type = "WIRE"
            co.hide_render = True
            cols.append(co)
        for j, pts in enumerate(self.hulls):
            hm = bpy.data.meshes.new(f"UCX_{self.name}_R{j:02d}")
            hm.from_pydata(pts, [], [(0, 1, 2, 3), (7, 6, 5, 4), (0, 3, 7, 4), (1, 5, 6, 2), (0, 4, 5, 1), (3, 2, 6, 7)])
            hm.update()
            ho = bpy.data.objects.new(f"UCX_{self.name}_R{j:02d}", hm)
            ho.location = loc
            (collection or bpy.context.scene.collection).objects.link(ho)
            ho.display_type = "WIRE"
            ho.hide_render = True
            cols.append(ho)
        return ob, cols


# ====================================================================== paredes com vãos

def wall(B, p0, p1, height, openings, m_in, m_out, center, collide=True, thick=WALL_T, frame="MadeiraVelha"):
    """Parede reta de p0 a p1 (eixo central). openings: [(offset_m do p0 ao centro, largura, peitoril, topo, tipo)]
    tipo 'porta' ou 'janela' (janela ganha vidro). Monta em pedaços: cheios entre vãos, verga em cima, peitoril embaixo."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    u = d.normalized()
    rot = math.atan2(u.y, u.x)
    ops = sorted(openings, key=lambda o: o[0])

    def piece(t0, t1, z0, z1, collide_piece=True):
        if t1 - t0 < 0.01 or z1 - z0 < 0.01:
            return
        mid = p0 + u * ((t0 + t1) / 2)
        B.box((mid.x, mid.y, (z0 + z1) / 2), (t1 - t0, thick, z1 - z0), m_in, rot, collide and collide_piece, m_out, center)

    t = 0.0
    for off, w, sill, top, kind in ops:
        a, b = off - w / 2, off + w / 2
        piece(t, a, 0, height)
        piece(a, b, top, height)                 # verga
        if sill > 0:
            piece(a, b, 0, sill)                 # peitoril
        # batente (moldura de madeira) e vidro
        fm = mat(frame)
        for tt in (a, b):
            q = p0 + u * tt
            B.box((q.x, q.y, (sill + top) / 2), (0.08, thick + 0.06, top - sill), fm, rot)
        q = p0 + u * off
        B.box((q.x, q.y, top + 0.04), (w + 0.16, thick + 0.06, 0.08), fm, rot)
        if kind == "janela":
            B.box((q.x, q.y, sill - 0.03), (w + 0.16, thick + 0.12, 0.06), fm, rot)
            B.box((q.x, q.y, (sill + top) / 2), (w, 0.03, top - sill), mat("VidroSujo"), rot, collide)
        t = b
    piece(t, L, 0, height)


def gable_roof(B, sx, sy, h, rise, m_roof, m_wall, overhang=0.45, along="Y"):
    """Telhado de duas águas. along: direção da cumeeira ('Y' = cumeeira ao longo de Y)."""
    hx, hy = sx / 2 + overhang, sy / 2 + overhang
    th = 0.12
    if along == "Y":
        for s in (-1, 1):
            B.quad([(s * hx, -hy, h - 0.1), (s * hx, hy, h - 0.1), (0, hy, h + rise), (0, -hy, h + rise)][::(1 if s < 0 else -1)], m_roof)
            B.quad([(s * hx, -hy, h - 0.1 - th), (0, -hy, h + rise - th), (0, hy, h + rise - th), (s * hx, hy, h - 0.1 - th)][::(1 if s < 0 else -1)], mat("MadeiraVelha"))
        for y in (-sy / 2, sy / 2):
            B.tri_prism((-sx / 2, y), (sx / 2, y), rise, 0.0, WALL_T, h, m_wall)
    else:
        for s in (-1, 1):
            B.quad([(-hx, s * hy, h - 0.1), (hx, s * hy, h - 0.1), (hx, 0, h + rise), (-hx, 0, h + rise)][::(-1 if s < 0 else 1)], m_roof)
            B.quad([(-hx, s * hy, h - 0.1 - th), (-hx, 0, h + rise - th), (hx, 0, h + rise - th), (hx, s * hy, h - 0.1 - th)][::(-1 if s < 0 else 1)], mat("MadeiraVelha"))
        for x in (-sx / 2, sx / 2):
            B.tri_prism((x, -sy / 2), (x, sy / 2), rise, 0.0, WALL_T, h, m_wall)
    # forro interior (fecha a luz do céu) com colisão: a câmera nunca sai pelo telhado
    B.box((0, 0, h + 0.05), (sx, sy, 0.1), mat("MadeiraTabuas"), 0, True)


# ====================================================================== móveis (biblioteca)

def furniture(kind):
    """Monta um móvel como Builder (origem no chão, frente +X). Retorna (Builder, raio_m, altura_m)."""
    B = Builder(f"SM_INT_{kind}")
    if kind == "Gondola":            # prateleira de loja dupla face, 2,4 m, com produtos coloridos
        B.box((0, 0, 0.06), (0.9, 2.4, 0.12), mat("Escuro"), collide=True)
        B.box((0, 0, 0.8), (0.06, 2.4, 1.5), mat("Pintura"))
        cols = ["Vermelho", "Azul", "Amarelo", "Verde", "Laranja", "Branco"]
        for k, z in enumerate((0.35, 0.75, 1.15, 1.5)):
            B.box((0, 0, z), (0.9, 2.4, 0.04), mat("Pintura"))
            for side in (-1, 1):
                for j in range(8):
                    if (j * 7 + k * 3 + side) % 5 == 0:
                        continue          # buracos: loja saqueada
                    hh = 0.16 + 0.08 * ((j + k) % 3)
                    B.box((side * 0.22, -1.05 + j * 0.3, z + 0.02 + hh / 2), (0.3, 0.22, hh), mat(cols[(j + k + (side > 0)) % 6]))
        B.colliders = [((0, 0, 0.8), (0.9, 2.4, 1.6), 0.0)]
        return B, 1.3, 1.6
    if kind == "Balcao":             # balcão do caixa 2,6 m com registradora
        B.box((0, 0, 0.5), (0.7, 2.6, 1.0), mat("MadeiraTabuas"), collide=True)
        B.box((0, 0, 1.02), (0.8, 2.7, 0.05), mat("Escuro"))
        B.box((0.05, 0.7, 1.15), (0.4, 0.45, 0.2), mat("Escuro"))
        B.box((0.0, 0.7, 1.32), (0.05, 0.38, 0.22), mat("Tela"), rot=0)
        B.box((0.1, -0.6, 1.1), (0.3, 0.5, 0.12), mat("Papel"))
        return B, 1.4, 1.1
    if kind == "Geladeira":          # geladeira vertical de vidro 1 porta (encostar na parede, frente +X)
        B.box((0, 0, 1.0), (0.7, 0.9, 2.0), mat("Branco"), collide=True)
        B.box((0.36, 0, 1.05), (0.02, 0.78, 1.7), mat("Geladeira"))
        for z in (0.5, 0.95, 1.4):
            for j in range(3):
                B.cyl((0.15, -0.25 + j * 0.25, z + 0.12), 0.05, 0.25, mat(("Vermelho", "Verde", "Laranja")[j]), 8)
        return B, 0.6, 2.0
    if kind == "PrateleiraParede":   # estante de metal 2 m (depósito)
        for y in (-0.95, 0.95):
            for x in (-0.25, 0.25):
                B.box((x, y, 1.0), (0.05, 0.05, 2.0), mat("Metal"))
        for z in (0.15, 0.7, 1.25, 1.8):
            B.box((0, 0, z), (0.55, 1.95, 0.03), mat("Metal"))
            for j in range(3):
                if (j + int(z * 10)) % 4:
                    B.box((0, -0.6 + j * 0.6, z + 0.18), (0.45, 0.5, 0.34), mat("MadeiraVelha"))
        B.colliders = [((0, 0, 1.0), (0.6, 2.0, 2.0), 0.0)]
        return B, 1.05, 2.0
    if kind == "Caixotes":           # pilha de caixotes
        for (x, y, z, s) in ((0, 0, 0.3, 0.6), (0.05, 0.62, 0.3, 0.6), (0.02, 0.3, 0.9, 0.58)):
            B.box((x, y, z), (s, s, s), mat("MadeiraVelha"), collide=True)
        return B, 0.7, 1.2
    if kind == "Mesa":
        B.box((0, 0, 0.74), (1.0, 1.6, 0.06), mat("MadeiraPiso"))
        for x in (-0.42, 0.42):
            for y in (-0.72, 0.72):
                B.box((x, y, 0.36), (0.07, 0.07, 0.72), mat("MadeiraVelha"))
        B.colliders = [((0, 0, 0.4), (1.0, 1.6, 0.8), 0.0)]
        return B, 0.95, 0.8
    if kind == "Cadeira":
        B.box((0, 0, 0.45), (0.45, 0.45, 0.05), mat("MadeiraVelha"))
        B.box((-0.2, 0, 0.75), (0.05, 0.45, 0.6), mat("MadeiraVelha"))
        for x in (-0.18, 0.18):
            for y in (-0.18, 0.18):
                B.box((x, y, 0.22), (0.04, 0.04, 0.45), mat("MadeiraVelha"))
        B.colliders = [((0, 0, 0.5), (0.45, 0.45, 1.0), 0.0)]
        return B, 0.35, 1.05
    if kind == "Cama":
        B.box((0, 0, 0.22), (2.0, 1.0, 0.3), mat("MadeiraVelha"), collide=True)
        B.box((0, 0, 0.45), (1.9, 0.92, 0.18), mat("Colchao"))
        B.box((0.2, 0, 0.56), (1.3, 0.94, 0.05), mat("Tecido"))
        B.box((-0.75, 0, 0.6), (0.35, 0.6, 0.12), mat("Branco"))
        B.box((-1.0, 0, 0.5), (0.06, 1.0, 1.0), mat("MadeiraVelha"))
        return B, 1.1, 1.0
    if kind == "Armario":
        B.box((0, 0, 0.95), (0.55, 1.2, 1.9), mat("MadeiraVelha"), collide=True)
        B.box((0.28, -0.3, 0.95), (0.02, 0.56, 1.8), mat("MadeiraTabuas"))
        B.box((0.28, 0.3, 0.95), (0.02, 0.56, 1.8), mat("MadeiraTabuas"))
        return B, 0.7, 1.9
    if kind == "Cozinha":            # bancada com pia e fogão, 2,4 m, encostada (frente +X)
        B.box((0, 0, 0.45), (0.6, 2.4, 0.9), mat("Branco"), collide=True)
        B.box((0, 0, 0.92), (0.65, 2.45, 0.04), mat("Escuro"))
        B.box((0.02, -0.6, 0.9), (0.45, 0.55, 0.06), mat("Metal"))
        for j in range(4):
            B.cyl((0.0 + (j % 2) * 0.22 - 0.1, 0.55 + (j // 2) * 0.25, 0.95), 0.08, 0.02, mat("Borracha"), 10)
        B.box((-0.25, 0, 1.6), (0.35, 2.4, 0.7), mat("MadeiraTabuas"))
        return B, 1.3, 2.0
    if kind == "Sofa":
        B.box((0, 0, 0.22), (0.9, 2.0, 0.44), mat("Tecido"), collide=True)
        B.box((-0.35, 0, 0.6), (0.2, 2.0, 0.6), mat("Tecido"))
        for y in (-0.95, 0.95):
            B.box((0, y, 0.45), (0.9, 0.12, 0.5), mat("Tecido"))
        return B, 1.1, 0.9
    if kind == "Escrivaninha":       # mesa com rádio velho e papéis
        B.box((0, 0, 0.74), (0.7, 1.4, 0.05), mat("MadeiraPiso"))
        B.box((0, 0.5, 0.37), (0.65, 0.4, 0.72), mat("MadeiraVelha"))
        B.box((0, -0.6, 0.37), (0.6, 0.05, 0.72), mat("MadeiraVelha"))
        B.box((-0.1, -0.2, 0.88), (0.3, 0.5, 0.22), mat("Escuro"))
        B.box((0.06, -0.2, 0.9), (0.02, 0.3, 0.1), mat("Tela"))
        B.box((0.05, 0.35, 0.78), (0.3, 0.4, 0.02), mat("Papel"))
        B.colliders = [((0, 0, 0.4), (0.7, 1.4, 0.8), 0.0)]
        return B, 0.8, 1.0
    if kind == "Arquivo":
        B.box((0, 0, 0.65), (0.5, 0.45, 1.3), mat("Metal"), collide=True)
        for z in (0.3, 0.65, 1.0):
            B.box((0.26, 0, z), (0.02, 0.36, 0.25), mat("Pintura"))
        return B, 0.4, 1.3
    if kind == "Bancada":            # bancada de oficina com ferramentas e painel
        B.box((0, 0, 0.88), (0.75, 2.2, 0.06), mat("MadeiraTabuas"))
        for y in (-1.0, 1.0):
            B.box((0, y, 0.43), (0.7, 0.08, 0.86), mat("Metal"))
        B.box((-0.36, 0, 1.6), (0.04, 2.2, 1.2), mat("MadeiraVelha"))
        for j in range(6):
            B.box((-0.32, -0.9 + j * 0.36, 1.55 + (j % 2) * 0.25), (0.04, 0.08, 0.35), mat(("Vermelho", "Metal", "Amarelo")[j % 3]))
        B.box((0.05, 0.6, 0.98), (0.35, 0.25, 0.14), mat("Vermelho"))
        B.colliders = [((0, 0, 0.5), (0.75, 2.2, 1.0), 0.0)]
        return B, 1.2, 2.2
    if kind == "Pneus":
        for k in range(4):
            B.cyl((0, 0, 0.1 + k * 0.21), 0.36, 0.2, mat("Borracha"), 14)
        B.colliders = [((0, 0, 0.45), (0.72, 0.72, 0.9), 0.0)]
        return B, 0.4, 0.9
    if kind == "Elevador":           # elevador de carro de duas colunas (oficina)
        for y in (-1.6, 1.6):
            B.box((0, y, 1.6), (0.35, 0.35, 3.2), mat("Amarelo"), collide=True)
            B.box((0.0, y * 0.6, 0.55), (0.12, 1.2, 0.1), mat("Metal"))
        B.box((0, 0, 3.15), (0.25, 3.5, 0.15), mat("Amarelo"))
        return B, 1.9, 3.2
    if kind == "Armarios":           # armários de vestiário
        for j in range(4):
            B.box((0, -0.75 + j * 0.5, 0.95), (0.5, 0.48, 1.9), mat(("Azul", "Metal")[j % 2]))
            B.box((0.26, -0.75 + j * 0.5, 1.5), (0.02, 0.3, 0.08), mat("Escuro"))
        B.colliders = [((0, 0, 0.95), (0.5, 2.0, 1.9), 0.0)]
        return B, 1.05, 1.9
    if kind == "MesaLab":            # bancada de laboratório com amostras de cristal brilhando
        B.box((0, 0, 0.45), (0.8, 2.4, 0.9), mat("Branco"), collide=True)
        B.box((0, 0, 0.92), (0.85, 2.45, 0.04), mat("Escuro"))
        for j in range(5):
            B.cyl((0.1, -0.9 + j * 0.45, 1.05), 0.07, 0.22, mat("Geladeira"), 10)
            B.box((0.1, -0.9 + j * 0.45, 1.06), (0.06, 0.06, 0.14), mat("Cristal"), rot=0.6)
        B.box((-0.2, 0.9, 1.1), (0.3, 0.4, 0.3), mat("Escuro"))
        return B, 1.3, 1.2
    if kind == "Radio":              # mesa de rádio da torre (ponto focal)
        B.box((0, 0, 0.74), (0.7, 1.8, 0.05), mat("Metal"))
        B.box((0, 0, 0.37), (0.65, 1.7, 0.72), mat("Escuro"))
        B.box((-0.18, 0, 1.05), (0.3, 1.4, 0.55), mat("Metal"))
        for j in range(5):
            B.box((-0.02, -0.55 + j * 0.27, 1.1), (0.02, 0.16, 0.1), mat(("Tela", "Amarelo", "Tela", "Vermelho", "Tela")[j]))
        B.colliders = [((0, 0, 0.6), (0.7, 1.8, 1.2), 0.0)]
        return B, 1.0, 1.4
    if kind == "Vaso":
        B.box((0, 0, 0.2), (0.4, 0.55, 0.4), mat("Branco"), collide=True)
        B.box((-0.18, 0, 0.6), (0.18, 0.45, 0.5), mat("Branco"))
        return B, 0.35, 0.85
    # ---------------- [A-076] mais coisas para encher os cômodos vazios
    if kind == "Barril":             # tambor de metal 200 L
        B.cyl((0, 0, 0.45), 0.29, 0.9, mat("Vermelho"), 14, collide=True)
        for z in (0.25, 0.65):
            B.cyl((0, 0, z), 0.3, 0.04, mat("Escuro"), 14)
        return B, 0.32, 0.9
    if kind == "TamborFogo":         # tambor com fogo (abrigo): brasa brilhando em cima
        B.cyl((0, 0, 0.42), 0.29, 0.84, mat("Escuro"), 14, collide=True)
        B.cyl((0, 0, 0.86), 0.25, 0.04, mat("Brasa"), 12)
        for j in range(3):
            B.box((0.05 * j - 0.05, 0.0, 0.9), (0.06, 0.4, 0.06), mat("MadeiraVelha"), rot=0.9 * j)
        return B, 0.32, 0.95
    if kind == "Lixo":               # entulho no chão (papéis, tábuas, latas): sem colisão, passa por cima
        bits = [((0.1, 0.2, 0.012), (0.5, 0.35, 0.02), "Papel", 0.4), ((-0.3, -0.1, 0.012), (0.4, 0.3, 0.02), "Papel", -0.7),
                ((0.2, -0.35, 0.03), (1.1, 0.12, 0.05), "MadeiraVelha", 0.5), ((-0.1, 0.45, 0.03), (0.9, 0.1, 0.05), "MadeiraVelha", -0.3),
                ((0.4, 0.0, 0.01), (0.7, 0.6, 0.015), "Lixo", 0.2)]
        for c, sz, m, r in bits:
            B.box(c, sz, mat(m), rot=r)
        for j in range(4):
            B.cyl((-0.45 + j * 0.27, -0.45 + (j % 2) * 0.8, 0.05), 0.04, 0.1, mat(("Vermelho", "Metal", "Verde", "Metal")[j]), 8)
        return B, 0.0, 0.1
    if kind == "Tapete":             # tapete (sem colisão)
        B.box((0, 0, 0.006), (1.6, 2.2, 0.012), mat("Vermelho"))
        B.box((0, 0, 0.013), (1.3, 1.9, 0.004), mat("Tecido"))
        return B, 0.0, 0.02
    if kind == "Estante":            # estante de livros 1,6 m encostada (frente +X)
        B.box((-0.17, 0, 1.0), (0.04, 1.6, 2.0), mat("MadeiraVelha"))
        for y in (-0.78, 0.78):
            B.box((0, y, 1.0), (0.38, 0.04, 2.0), mat("MadeiraVelha"))
        for k, z in enumerate((0.05, 0.5, 0.95, 1.4, 1.95)):
            B.box((0, 0, z), (0.38, 1.6, 0.03), mat("MadeiraVelha"))
            if z < 1.9:
                for j in range(9):
                    if (j * 5 + k) % 7 == 0:
                        continue
                    hb = 0.24 + 0.05 * ((j + k) % 3)
                    B.box((0.0, -0.66 + j * 0.165, z + 0.02 + hb / 2), (0.26, 0.13, hb),
                          mat(("Vermelho", "Azul", "Verde", "Couro", "Amarelo")[(j + k) % 5]))
        B.colliders = [((0, 0, 1.0), (0.4, 1.6, 2.0), 0.0)]
        return B, 0.85, 2.0
    if kind == "Beliche":            # beliche (abrigo)
        for x in (-0.45, 0.45):
            for y in (-0.95, 0.95):
                B.box((x, y, 0.85), (0.06, 0.06, 1.7), mat("Metal"))
        for z in (0.35, 1.25):
            B.box((0, 0, z), (0.92, 1.95, 0.08), mat("Metal"))
            B.box((0, 0, z + 0.1), (0.85, 1.85, 0.14), mat("Colchao"))
            B.box((0.1, 0.25, z + 0.19), (0.75, 1.1, 0.04), mat("Tecido"))
        B.colliders = [((0, 0, 0.85), (0.95, 2.0, 1.7), 0.0)]
        return B, 1.1, 1.7
    if kind == "Gerador":            # gerador a diesel amarelo
        B.box((0, 0, 0.35), (0.75, 1.1, 0.6), mat("Amarelo"), collide=True)
        B.box((0, 0, 0.03), (0.8, 1.2, 0.06), mat("Escuro"))
        B.cyl((0, -0.25, 0.72), 0.16, 0.12, mat("Metal"), 12)
        B.box((0.38, 0.25, 0.45), (0.02, 0.35, 0.2), mat("Escuro"))
        B.box((0.39, 0.25, 0.5), (0.01, 0.1, 0.05), mat("Tela"))
        B.cyl((-0.25, 0.45, 0.85), 0.04, 0.4, mat("Escuro"), 8)
        return B, 0.65, 0.9
    if kind == "MesaCentro":         # mesinha de centro com revistas
        B.box((0, 0, 0.42), (0.6, 1.0, 0.05), mat("MadeiraPiso"), collide=True)
        for x in (-0.25, 0.25):
            for y in (-0.45, 0.45):
                B.box((x, y, 0.2), (0.05, 0.05, 0.4), mat("MadeiraVelha"))
        B.box((0.05, 0.1, 0.46), (0.25, 0.3, 0.02), mat("Papel"), rot=0.3)
        B.colliders = [((0, 0, 0.22), (0.6, 1.0, 0.45), 0.0)]
        return B, 0.6, 0.45
    if kind == "TV":                 # rack com TV de tubo
        B.box((0, 0, 0.3), (0.45, 1.3, 0.6), mat("MadeiraVelha"), collide=True)
        B.box((0, 0.1, 0.85), (0.45, 0.6, 0.5), mat("Escuro"))
        B.box((0.23, 0.1, 0.85), (0.01, 0.48, 0.38), mat("Tela"))
        return B, 0.7, 1.1
    if kind == "Quadro":             # quadro de avisos/mapa na parede (frente +X, sem colisão)
        B.box((0, 0, 1.5), (0.03, 1.4, 0.9), mat("Couro"))
        B.box((0.02, -0.2, 1.55), (0.01, 0.7, 0.5), mat("Papel"))
        for j in range(4):
            B.box((0.02, 0.35 + (j % 2) * 0.15, 1.3 + j * 0.12), (0.01, 0.18, 0.12), mat(("Papel", "Amarelo")[j % 2]))
        B.box((0.025, -0.1, 1.6), (0.01, 0.04, 0.04), mat("Vermelho"))
        return B, 0.0, 1.95
    if kind == "Barricada":          # tábuas e sacos tapando um canto (abrigo)
        for j in range(3):
            B.box((0, -0.6 + j * 0.6, 0.18), (0.5, 0.58, 0.34), mat("Lona"))
        B.box((0.05, 0, 0.5), (0.45, 1.6, 0.3), mat("Lona"))
        for j in range(3):
            B.box((-0.2, 0, 0.6 + j * 0.3), (0.05, 1.9, 0.18), mat("MadeiraVelha"), rot=0.0)
        B.colliders = [((0, 0, 0.6), (0.55, 1.9, 1.2), 0.0)]
        return B, 1.0, 1.2
    if kind == "Fogao":              # fogão a lenha / bancada de cozinha curta
        B.box((0, 0, 0.42), (0.6, 0.9, 0.84), mat("Branco"), collide=True)
        for j in range(4):
            B.cyl(((j % 2) * 0.24 - 0.12, (j // 2) * 0.36 - 0.18, 0.86), 0.08, 0.02, mat("Borracha"), 10)
        B.box((0.31, 0, 0.45), (0.01, 0.6, 0.35), mat("Escuro"))
        return B, 0.55, 0.9
    if kind == "Luminaria":          # luminária de teto (sem colisão)
        B.box((0, 0, -0.05), (0.25, 1.2, 0.08), mat("Metal"))
        B.box((0, 0, -0.1), (0.18, 1.1, 0.03), mat("Lampada"))
        return B, 0.0, 0.0
    raise KeyError(kind)


# ====================================================================== [A-076] folhas de porta (AJRDoor)
# Dobradiça na origem; a folha vai de y = 0 a y = -1 m (vira +Y na Unreal), z de 0 a 2,2 m, 4,5 cm de espessura
# centrada em x = 0. O AJRDoor estica para o tamanho do vão (largura e altura).
DOOR_STYLE = {"MadeiraVelha": "PortaMadeira", "Metal": "PortaMetal"}


def door_leaf(style):
    B = Builder(f"SM_INT_{style}")
    W, H, T = 1.0, 2.2, 0.045
    if style == "PortaMadeira":     # tábuas verticais com travessas e "Z"
        for j in range(5):
            B.box((0, -0.1 - j * 0.2, H / 2), (T, 0.19, H), mat("MadeiraTabuas"))
        for z in (0.35, 1.1, 1.85):
            for sgn in (-1, 1):
                B.box((sgn * (T / 2 + 0.012), -W / 2, z), (0.025, W * 0.92, 0.12), mat("MadeiraVelha"))
        m_handle = "Metal"
    elif style == "PortaVidro":     # porta de loja: moldura de metal e vidro
        for (yc, w) in ((-0.04, 0.08), (-W + 0.04, 0.08)):
            B.box((0, yc, H / 2), (T, w, H), mat("Metal"))
        for (zc, h) in ((0.06, 0.12), (H - 0.05, 0.1), (1.0, 0.08)):
            B.box((0, -W / 2, zc), (T, W, h), mat("Metal"))
        B.box((0, -W / 2, 0.56), (0.012, W - 0.16, 0.86), mat("VidroSujo"))
        B.box((0, -W / 2, 1.6), (0.012, W - 0.16, 1.1), mat("VidroSujo"))
        m_handle = "Escuro"
    else:                            # PortaMetal: chapa com reforços (galpão, oficina, contêiner)
        B.box((0, -W / 2, H / 2), (T, W, H), mat("MetalOndulado"))
        for z in (0.25, 1.1, 1.95):
            for sgn in (-1, 1):
                B.box((sgn * (T / 2 + 0.01), -W / 2, z), (0.02, W, 0.08), mat("Metal"))
        m_handle = "Escuro"
    for sgn in (-1, 1):              # maçaneta dos dois lados, perto da ponta livre
        B.box((sgn * (T / 2 + 0.04), -W + 0.1, 1.0), (0.03, 0.14, 0.03), mat(m_handle))
        B.box((sgn * (T / 2 + 0.02), -W + 0.1, 1.0), (0.04, 0.03, 0.03), mat(m_handle))
    B.colliders = [((0, -W / 2, H / 2), (T, W, H), 0.0)]
    return B


def door_list(spec):
    """Portas do prédio (externas e internas), no sistema do prédio: centro do vão no chão, yaw da normal (graus),
    largura, altura, porta dupla, começa aberta, estilo da folha."""
    sx, sy = spec["size"]
    hx, hy = sx / 2, sy / 2
    style_default = DOOR_STYLE.get(spec.get("frame", "MadeiraVelha"), "PortaMadeira")
    out = []
    pos = {"+X": lambda o: ((hx, o), 0.0), "-X": lambda o: ((-hx, -o), 180.0),
           "+Y": lambda o: ((-o, hy), 90.0), "-Y": lambda o: ((o, -hy), -90.0)}
    glass = set(spec.get("glass_doors", []))
    for side, ops in spec["walls"].items():
        for k, o in enumerate(ops):
            if o[4] != "porta":
                continue
            (x, y), yaw = pos[side](o[0])
            w = o[1]
            style = "PortaVidro" if (side, k) in glass else style_default
            out.append({"x": round(x, 3), "y": round(y, 3), "yaw": yaw, "width_m": w, "height_m": o[3],
                        "double": w >= 1.7, "start_open": w >= 3.0, "style": style, "inner": False})
    for (a, b, ops) in spec.get("inner", []):
        a, b = Vector(a), Vector(b)
        u = (b - a).normalized()
        n = Vector((-u.y, u.x))
        for o in ops:
            if o[4] != "porta":
                continue
            c = a + u * o[0]
            out.append({"x": round(c.x, 3), "y": round(c.y, 3), "yaw": round(math.degrees(math.atan2(n.y, n.x)), 2),
                        "width_m": o[1], "height_m": o[3], "double": o[1] >= 1.7, "start_open": False,
                        "style": "PortaMadeira" if style_default != "PortaMetal" else "PortaMetal", "inner": True})
    return out


# ====================================================================== construções (dados)
# Cada sala: walls internos [(p0, p1, [(off, w, sill, top, tipo)])]; móveis [(tipo, x, y, yaw_graus)];
# itens [(tipo do JRPickup, x, y, z_sobre_o_chão)]; baús [(rotulo, x, y, yaw)]; luzes [(x, y)].
DOOR = (1.3, 0.0, 2.25, "porta")


def door(off, w=1.3):
    return (off, w, 0.0, 2.25, "porta")


def win(off, w=1.6, sill=0.95, top=2.1):
    return (off, w, sill, top, "janela")


BUILDINGS = {
    "PostoLoja": {
        "nome": "Loja de conveniência do posto", "zona": 2, "size": (10.0, 14.0), "h": 3.4, "roof": "flat",
        "ext": "Reboco", "int": "Reboco", "floor": "Concreto", "frame": "Metal",
        # paredes externas: frente (+X) com vitrine e porta dupla; fundos (-X) com porta do depósito
        "walls": {"+X": [win(-4.5, 3.4, 0.6, 2.6), door(-1.6, 1.8), win(2.0, 3.4, 0.6, 2.6), win(5.4, 2.0, 0.6, 2.6)],
                  "-X": [door(5.0, 1.2)], "+Y": [win(0.0, 2.0)], "-Y": []},
        # parede interna separando o depósito (fundos, x < -2.2) e o banheiro
        # paredes internas: offset dos vãos medido a partir do primeiro ponto (p0)
        "inner": [((-2.2, -7.0), (-2.2, 7.0), [door(4.0, 1.4), door(12.6, 1.0)]),
                  ((-5.0, 4.2), (-2.2, 4.2), [])],
        "facade": {"band": "Vermelho", "awning": True, "awning_depth": 1.8, "awning_z": 2.9},
        "glass_doors": [("+X", 1)],      # [A-076] porta dupla de vidro na frente da loja
        "furniture": [("Balcao", 2.9, -4.6, 180), ("Gondola", 0.6, -0.8, 0), ("Gondola", 0.6, 2.6, 0),
                      ("Gondola", -1.0, -0.8, 0), ("Gondola", -1.0, 2.6, 0), ("Geladeira", -0.9, 6.45, -90),
                      ("Geladeira", 0.1, 6.45, -90), ("Geladeira", 1.1, 6.45, -90), ("Geladeira", 2.1, 6.45, -90),
                      ("PrateleiraParede", -4.6, -2.6, 0), ("PrateleiraParede", -4.6, -0.2, 0),
                      ("PrateleiraParede", -4.6, 2.4, 0), ("Caixotes", -3.0, -6.1, 20), ("Barril", -4.5, -6.4, 0),
                      ("Gerador", -3.1, 3.4, 0), ("Arquivo", -2.6, -0.6, 180), ("Lixo", -3.5, -1.2, 40),
                      ("Vaso", -4.4, 6.0, 0), ("Caixotes", 4.0, 4.8, -15), ("Lixo", 2.0, 1.2, 30),
                      ("Lixo", -0.2, 4.6, -20), ("Quadro", -2.11, 1.5, 0)],
        "lights": [(1.5, -4.0), (0.0, 1.0), (1.5, 5.0), (-3.6, -3.0), (-3.6, 5.6)],
        "pickups": [("BANDAGE", 0.6, 2.0, 0.77), ("BANDAGE", -3.6, 5.4, 0.0)],
        # itens do layout que eram "da loja" (o plano antigo punha na calçada): kit no depósito, munição no balcão
        "absorb_pickups": {"Pickup_Medkit_Posto": (-4.3, -4.2), "Pickup_Municao_Posto": (2.95, -5.4)},
        "chests": [],
        "story": None,
        "replaces": {"user": ["CON_PostoLoja"], "blockout": [("Posto", "SpaceKit/Building_L"), ("Posto", "SpaceKit/Roof_Radar")]},
        "note": "Loja 10 x 14 m (era 8,5 x 10 m fechada). Vitrine e porta dupla na frente, geladeiras na parede, 4 gôndolas, "
                "balcão com caixa; depósito nos fundos com estantes e medkit; banheiro.",
    },
    "Escritorio": {
        "nome": "Escritório do posto (sala trancada)", "zona": 2, "size": (6.0, 7.0), "h": 3.0, "roof": "flat",
        "ext": "Tijolo", "int": "Reboco", "floor": "MadeiraPiso", "frame": "MadeiraVelha",
        "walls": {"+X": [door(-1.8, 1.2), win(1.5, 1.6)], "-X": [win(0.0, 1.4)], "+Y": [], "-Y": [win(0.0, 1.4)]},
        "inner": [],
        "furniture": [("Escrivaninha", -2.0, 0.0, 0), ("Cadeira", -1.2, 0.3, 180), ("Arquivo", -2.6, 3.0, 0),
                      ("Arquivo", -2.6, 2.45, 0), ("Armario", 1.8, 3.1, -90), ("Caixotes", 2.4, -3.0, 90),
                      ("Estante", -2.7, -1.7, 0), ("Tapete", 0.4, 0.3, 90), ("Quadro", 0.0, 3.39, -90),
                      ("Lixo", 0.8, -1.0, 20), ("Cadeira", 0.6, 1.2, 40)],
        "lights": [(0.0, 0.0)],
        "pickups": [("AMMO", -2.0, 0.45, 0.79)],
        "chests": [("Bau_Pistola_Posto", -1.0, -2.7, 0)],
        "story": None,
        "replaces": {"blockout": [("SalaTrancada", "SpaceKit/House_Single")]},
        "note": "Sala dos fundos do posto: escrivaninha, arquivos, o baú da pistola no canto.",
    },
    "Conteiner": {
        "nome": "Contêiner do acampamento", "zona": 0, "size": (6.1, 2.5), "h": 2.6, "roof": "flat",
        "ext": "MetalOndulado", "int": "MetalOndulado", "floor": "MadeiraTabuas", "frame": "Metal",
        "walls": {"+X": [door(0.0, 2.2)], "-X": [], "+Y": [], "-Y": []},
        "inner": [],
        "furniture": [("Caixotes", -2.6, 0.75, -90), ("PrateleiraParede", -0.6, 0.85, -90), ("Barril", -2.6, -0.75, 0),
                      ("Cadeira", -1.2, -0.6, 30), ("Lixo", 0.4, -0.3, 10)],
        "lights": [(0.0, 0.0)],
        "pickups": [("BANDAGE", -0.6, 0.85, 0.73)],
        "chests": [],
        "story": None,
        "replaces": {"user": ["CON_Conteiner"]},
        "note": "Contêiner aberto numa ponta (porta de 2,2 m), estante e caixotes, bandagem.",
    },
    "CasaSobrevivente": {
        "nome": "Casa da vila (sala, cozinha, quarto)", "zona": 6, "size": (9.0, 11.0), "h": 3.0, "roof": "gable",
        "ext": "Tijolo", "int": "Reboco", "floor": "MadeiraPiso", "frame": "MadeiraVelha", "roof_mat": "TelhaCeramica",
        "walls": {"+X": [door(-1.0, 1.3), win(2.6, 1.8), win(-4.0, 1.4)], "-X": [win(2.8, 1.4), win(-3.0, 1.4)],
                  "+Y": [win(0.5, 1.6)], "-Y": [win(-1.0, 1.4)]},
        "inner": [((-0.5, -5.5), (-0.5, 5.5), [door(3.0, 1.1), door(8.2, 1.1)]),
                  ((-4.5, 1.5), (-0.5, 1.5), [])],
        "furniture": [("Sofa", 2.6, 4.2, -90), ("MesaCentro", 2.6, 3.0, 90), ("TV", 2.6, 1.6, 90),
                      ("Tapete", 2.6, 3.0, 90), ("Mesa", 2.0, -2.8, 0), ("Cadeira", 2.0, -3.9, 90),
                      ("Cadeira", 2.0, -1.7, -90), ("Armario", 3.9, 1.4, 180), ("Caixotes", 3.7, -4.6, 0),
                      ("Cozinha", -4.1, -3.4, 0), ("Mesa", -2.5, -0.4, 90), ("Cadeira", -2.5, 0.45, -90),
                      ("Cadeira", -2.5, -1.25, 90), ("Cama", -2.6, 4.2, 0), ("Armario", -4.0, 2.3, 0),
                      ("Tapete", -2.6, 3.0, 0), ("Quadro", -4.39, 4.2, 0)],
        "lights": [(2.2, 2.5), (2.0, -3.0), (-2.5, -2.5), (-2.5, 3.5)],
        "pickups": [("HEALTH", -4.1, -2.4, 0.95), ("AMMO", 2.0, -2.8, 0.79)],
        "chests": [("Bau_Vila_Municao", -2.4, 2.3, 0)],
        "story": None,
        "replaces": {"user": ["CON_CasaVila#0"]},
        "note": "Casa de tijolo 9 x 11 m com telhado de duas águas: sala com sofá e mesa, cozinha, quarto com o baú.",
    },
    "CasaSaqueada": {
        "nome": "Casa saqueada", "zona": 6, "size": (8.0, 9.0), "h": 3.0, "roof": "gable",
        "ext": "Reboco", "int": "Reboco", "floor": "MadeiraTabuas", "frame": "MadeiraVelha", "roof_mat": "TelhaCeramica",
        "walls": {"+X": [door(0.0, 1.3), win(3.0, 1.4)], "-X": [win(0.0, 1.4)], "+Y": [win(0.0, 1.4)], "-Y": [win(1.5, 1.4)]},
        "inner": [((-1.0, -4.5), (-1.0, 4.5), [door(3.0, 1.2)])],
        "furniture": [("Mesa", 1.8, 2.5, 25), ("Cadeira", 1.0, 1.5, 70), ("Armario", -3.6, -3.0, 0),
                      ("Cama", -2.5, 2.8, 0), ("Sofa", 2.0, -3.6, 90), ("Caixotes", -0.3, 3.3, 0),
                      ("Fogao", 0.8, 4.0, -90), ("TV", 3.4, 3.4, 180), ("Barril", -3.4, -0.9, 0), ("Tapete", 1.5, 0.8, 15),
                      ("Lixo", 0.5, -1.0, 30), ("Lixo", 2.5, 1.0, -40), ("Lixo", -2.5, -3.0, 10), ("Lixo", -2.6, 1.2, 70)],
        "lights": [(1.5, 0.0), (-2.6, 0.0)],
        "pickups": [("FURY", -3.0, -1.0, 0.0), ("HEALTH", 1.8, 2.5, 0.79)],
        "chests": [],
        "story": None,
        "replaces": {"user": ["CON_CasaVila#1"]},
        "note": "Casa revirada: móveis tortos, quarto nos fundos com Fúria.",
    },
    "Oficina": {
        "nome": "Oficina/cabana da vila", "zona": 6, "size": (7.0, 7.0), "h": 3.2, "roof": "gable",
        "ext": "MadeiraVelha", "int": "MadeiraTabuas", "floor": "Concreto", "frame": "MadeiraVelha", "roof_mat": "MetalOndulado",
        "walls": {"+X": [door(0.0, 2.4)], "-X": [win(0.0, 1.6)], "+Y": [], "-Y": [win(-1.0, 1.4)]},
        "inner": [],
        "furniture": [("Bancada", -2.9, 0.0, 0), ("Pneus", 2.4, 2.6, 0), ("Pneus", 1.6, 2.8, 0),
                      ("Armarios", 1.8, -3.0, 90), ("Caixotes", -2.6, 3.0, -90), ("Barril", -3.0, -2.9, 0),
                      ("Barril", -2.35, -3.0, 0), ("Gerador", -0.5, 2.8, 0), ("Lixo", 0.5, -0.5, 20)],
        "lights": [(0.0, 0.0)],
        "pickups": [("AMMO", -2.9, 0.6, 0.94), ("BANDAGE", -2.9, -0.7, 0.94)],
        "chests": [],
        "story": None,
        "replaces": {"user": ["CON_Cabana"]},
        "note": "Cabana virou oficina 7 x 7 m com portão largo, bancada de ferramentas, pneus e armários.",
    },
    # ---------------- lugares novos de exploração
    "OficinaEstrada": {
        "nome": "Oficina da estrada (lugar novo)", "zona": 1, "size": (12.0, 10.0), "h": 4.2, "roof": "gable_x",
        "ext": "MetalOndulado", "int": "MetalOndulado", "floor": "Concreto", "frame": "Metal", "roof_mat": "MetalOndulado",
        "walls": {"+X": [door(-1.5, 4.0)], "-X": [door(3.5, 1.2)], "+Y": [win(-2.0, 2.0, 1.4, 2.8), win(3.0, 2.0, 1.4, 2.8)],
                  "-Y": [win(0.0, 2.0, 1.4, 2.8)]},
        "inner": [((-3.0, 2.0), (-3.0, 5.0), [door(1.5, 1.0)]), ((-6.0, 2.0), (-3.0, 2.0), [])],
        "furniture": [("Elevador", 1.0, -1.5, 0), ("Bancada", -5.45, 0.3, 0), ("Arquivo", -5.6, -1.4, 0),
                      ("Pneus", 4.8, 4.2, 0), ("Pneus", 4.0, 4.3, 0), ("Pneus", 3.5, 3.4, 0), ("Armarios", -4.5, 4.5, -90),
                      ("Mesa", -5.0, 3.0, 0), ("Cadeira", -4.2, 2.6, 180), ("PrateleiraParede", 2.0, 4.5, -90),
                      ("Caixotes", -3.6, -4.5, 90), ("Barril", 5.3, -4.3, 0), ("Barril", 4.7, -4.4, 0),
                      ("Barril", 5.4, -3.7, 0), ("Gerador", -1.5, 4.3, -90), ("Lixo", -1.0, -3.0, 15),
                      ("Lixo", 3.0, 1.5, -30)],
        "lights": [(0.0, -1.5), (-4.5, -2.5), (2.5, 3.0), (-4.5, 3.5)],
        "pickups": [("REPAIR", 4.2, -4.0, 0.0), ("NITRO", -5.4, -1.8, 0.94), ("AMMO", -4.5, 3.4, 0.0)],
        "chests": [],
        "story": ("Oficina da estrada", "Uma oficina! Deve ter peças pro buggy.", "Procure peças na oficina"),
        "replaces": {},
        "place": {"near_route": "main", "zone": 1, "side_m": 26.0},
        "note": "Galpão de metal 12 x 10 m, portão de 4 m (o buggy entra), elevador, bancada, pneus; reparo e nitro.",
    },
    "CabanaPesquisador": {
        "nome": "Cabana do pesquisador (lugar novo)", "zona": 3, "size": (7.0, 8.0), "h": 3.0, "roof": "gable",
        "ext": "MadeiraTabuas", "int": "MadeiraTabuas", "floor": "MadeiraPiso", "frame": "MadeiraVelha", "roof_mat": "TelhaCeramica",
        "walls": {"+X": [door(-1.5, 1.2), win(1.8, 1.6)], "-X": [win(0.0, 1.8)], "+Y": [win(0.0, 1.4)], "-Y": [win(1.0, 1.4)]},
        "inner": [],
        "furniture": [("MesaLab", -2.9, 0.5, 0), ("Cadeira", -2.0, 0.5, 0), ("Escrivaninha", 1.5, 3.3, -90),
                      ("Cadeira", 1.5, 2.5, 90), ("Cama", -1.0, -3.3, 0), ("Arquivo", -2.9, -3.3, 0),
                      ("PrateleiraParede", -3.1, -2.0, 0), ("Estante", -2.0, 3.7, -90), ("Tapete", 0.5, 0.0, 0),
                      ("Lixo", 0.8, -1.0, 20)],
        "lights": [(0.0, 0.0), (-2.5, 0.5)],
        "pickups": [("HEALTH", 1.5, 3.3, 0.79), ("AMMO", -3.1, -2.0, 0.73)],
        "chests": [],
        "story": ("Cabana do pesquisador", "Anotações: 'os cristais acordam os mortos'... Pegue o que puder.", "Revire a cabana"),
        "replaces": {},
        "place": {"near_route": "main", "zone": 3, "side_m": 30.0},
        "note": "Cabana 7 x 8 m na floresta: bancada com cristais brilhando, mesa de anotações, cama.",
    },
    "Galpao": {
        "nome": "Galpão de abrigo (lugar novo)", "zona": 5, "size": (14.0, 10.0), "h": 4.5, "roof": "gable_x",
        "ext": "MetalOndulado", "int": "Concreto", "floor": "Concreto", "frame": "Metal", "roof_mat": "MetalOndulado",
        "walls": {"+X": [door(0.0, 4.5)], "-X": [door(-3.0, 1.2)], "+Y": [win(-3.0, 2.4, 1.6, 3.0), win(3.0, 2.4, 1.6, 3.0)],
                  "-Y": [win(-3.0, 2.4, 1.6, 3.0), win(3.0, 2.4, 1.6, 3.0)]},
        "inner": [],
        "furniture": [("PrateleiraParede", -6.5, -2.5, 0), ("PrateleiraParede", -6.5, 0.0, 0), ("Beliche", -5.2, 3.85, 0),
                      ("Beliche", -0.2, 3.85, 0), ("Armarios", 5.5, 4.3, -90), ("TamborFogo", -2.6, 1.2, 0),
                      ("Cadeira", -3.4, 1.2, 0), ("Cadeira", -2.6, 2.0, -90), ("Mesa", -2.5, -1.0, 90),
                      ("Cadeira", -2.5, -1.85, 90), ("Caixotes", 3.5, -3.5, 10), ("Caixotes", -4.6, -3.6, -15),
                      ("Caixotes", 0.0, 0.0, 30), ("Gerador", 5.8, -4.2, 0), ("Barril", 6.3, -3.2, 0),
                      ("Barricada", -3.0, -4.6, 90), ("Barricada", 3.0, -4.6, 90), ("Tapete", -2.7, 3.5, 0),
                      ("Lixo", 1.5, -2.0, 30), ("Lixo", -4.5, 0.5, -20)],
        "lights": [(-3.0, 0.0), (3.0, 0.0), (-5.0, 3.0), (3.0, 3.5)],
        "pickups": [("FURY", 0.0, 0.0, 1.2), ("AMMO", -6.5, -2.5, 0.88), ("HEALTH", -2.5, -1.0, 0.79)],
        "chests": [],
        "story": ("Galpão", "Um galpão. Dá pra recuperar o fôlego aqui dentro.", "Pegue suprimentos no galpão"),
        "replaces": {},
        "place": {"near_route": "main", "zone": 5, "side_m": 34.0},
        "note": "Galpão 14 x 10 m de pé-direito alto, portão de 4,5 m, estantes industriais, caixotes e Fúria.",
    },
    "CabineRadio": {
        "nome": "Cabine da torre de rádio (lugar novo)", "zona": 2, "size": (4.5, 5.0), "h": 2.9, "roof": "flat",
        "ext": "Concreto", "int": "Concreto", "floor": "Concreto", "frame": "Metal",
        "walls": {"+X": [door(-1.2, 1.2)], "-X": [win(0.0, 1.4)], "+Y": [win(0.0, 1.2)], "-Y": []},
        "inner": [],
        "furniture": [("Radio", -1.6, 0.4, 0), ("Cadeira", -0.9, 0.4, 180), ("Arquivo", 1.4, 2.1, -90),
                      ("Gerador", -1.5, -1.8, 90), ("Barril", 1.7, 1.2, 0), ("Cama", 0.1, 1.9, 0), ("Lixo", 0.3, -0.6, 0),
                      ("Quadro", 0.6, -2.39, 90)],
        "lights": [(0.0, 0.0)],
        "pickups": [("AMMO", 1.4, 2.1, 1.3)],
        "chests": [],
        "story": ("Cabine do rádio", "Rádio: '...resgate... vale... sigam para o portão norte...'", "Ouça o rádio da torre"),
        "replaces": {},
        "place": {"poi": "TorreRadio", "offset_m": (-9.0, 0.0)},
        "note": "Cabine 4,5 x 5 m ao pé da torre: rádio chiando (história), munição.",
    },
}


# ====================================================================== montagem de um prédio

def build_building(key, spec, col):
    sx, sy = spec["size"]
    h = spec["h"]
    hx, hy = sx / 2, sy / 2
    B = Builder(f"SM_INT_{key}")
    m_in, m_out = mat(spec["int"]), mat(spec["ext"])
    frame = spec.get("frame", "MadeiraVelha")
    # piso (laje) e rodapé externo
    B.box((0, 0, -0.08), (sx + 0.4, sy + 0.4, 0.16), mat(spec["floor"]), 0, True)
    # base funda (o piso fica acima do ponto mais alto do chão; no lado baixo a base cobre o vão até 1,5 m)
    B.box((0, 0, -0.8), (sx + 0.5, sy + 0.5, 1.4), mat("Concreto"))
    # paredes externas: a parede de um lado vai de canto a canto (offset medido a partir do centro do lado)
    t2 = WALL_T / 2
    # as paredes +X/-X vão de canto a canto (cobrem a quina); as +Y/-Y ficam entre elas (sem sobrepor: sem quina preta)
    sides = {"+X": ((hx, -hy - t2), (hx, hy + t2)), "-X": ((-hx, hy + t2), (-hx, -hy - t2)),
             "+Y": ((hx - t2, hy), (-hx + t2, hy)), "-Y": ((-hx + t2, -hy), (hx - t2, -hy))}
    for side, (a, b) in sides.items():
        L = math.dist(a, b)
        # offset dos vãos: medido do centro do lado; o sinal segue o sentido de a para b
        ops = [(o[0] + L / 2,) + tuple(o[1:]) for o in spec["walls"].get(side, [])]
        wall(B, a, b, h, ops, m_in, m_out, (0, 0), frame=frame)
    # rampa de entrada em cada porta externa (desce 1,3 m em 3,8 m: ~19 graus, o herói sobe andando)
    for side, (a, b) in sides.items():
        L = math.dist(a, b)
        u = (Vector(b) - Vector(a)).normalized()
        for o in spec["walls"].get(side, []):
            if o[4] != "porta":
                continue
            c0 = Vector(a) + u * (o[0] + L / 2)
            outn = Vector((c0.x, c0.y)).normalized()
            outn = Vector((1, 0)) if side == "+X" else Vector((-1, 0)) if side == "-X" else Vector((0, 1)) if side == "+Y" else Vector((0, -1))
            edge = c0 + outn * (t2 + 0.1)
            w = o[1] + 0.8
            B.wedge(edge - u * (w / 2), edge + u * (w / 2), 3.8, 1.3, mat("Concreto"))
    for (a, b, ops) in spec.get("inner", []):
        wall(B, a, b, h, ops, m_in, m_in, (99, 99), frame=frame, thick=0.15)
    # fachada: faixa colorida no alto e marquise sobre a frente (+X)
    fac = spec.get("facade")
    if fac:
        if fac.get("band"):
            B.box((hx + t2 + 0.03, 0, h - 0.25), (0.06, sy + WALL_T, 0.5), mat(fac["band"]))
        if fac.get("awning"):
            d = fac.get("awning_depth", 1.6)
            B.box((hx + t2 + d / 2, 0, fac.get("awning_z", 2.85)), (d, sy * 0.92, 0.14), mat(fac.get("awning_mat", "Metal")))
            B.box((hx + t2 + d, 0, fac.get("awning_z", 2.85) - 0.08), (0.06, sy * 0.92, 0.3), mat(fac["band"] or "Metal"))
    # teto/telhado
    roof = spec.get("roof", "flat")
    if roof == "flat":
        B.box((0, 0, h + 0.1), (sx + 0.3, sy + 0.3, 0.2), mat("Concreto"), 0, True)
        for (cx, cy, lx, ly) in ((hx + 0.1, 0, 0.2, sy + 0.4), (-hx - 0.1, 0, 0.2, sy + 0.4), (0, hy + 0.1, sx + 0.4, 0.2), (0, -hy - 0.1, sx + 0.4, 0.2)):
            B.box((cx, cy, h + 0.45), (lx, ly, 0.5), m_out)        # platibanda
        B.box((0, 0, h - 0.02), (sx - 0.05, sy - 0.05, 0.04), mat("Branco"))   # forro
    else:
        rise = 1.8 if roof == "gable" else 1.4
        gable_roof(B, sx, sy, h, rise, mat(spec.get("roof_mat", "TelhaCeramica")), m_out, along=("X" if roof == "gable_x" else "Y"))
    ob, cols = B.build(col)
    return ob, cols


def place_furniture(spec, col, cache):
    """Instâncias dos móveis (preview) + luminárias no teto."""
    obs = []
    for kind, x, y, yaw in spec["furniture"]:
        if kind not in cache:
            fb, r, hh = furniture(kind)
            fob, fcols = fb.build(col)
            fob.hide_render = True
            fob.hide_viewport = True
            for c in fcols:
                c.hide_viewport = True
            cache[kind] = (fob, fcols, r, hh)
        src = cache[kind][0]
        inst = bpy.data.objects.new(f"{kind}_{len(obs)}", src.data)
        inst.location = (x, y, 0)
        inst.rotation_euler = (0, 0, math.radians(yaw))
        col.objects.link(inst)
        obs.append(inst)
    if "Luminaria" not in cache:
        fb, _, _ = furniture("Luminaria")
        fob, fcols = fb.build(col)
        fob.hide_render = True
        fob.hide_viewport = True
        cache["Luminaria"] = (fob, fcols, 0, 0)
    for (x, y) in spec["lights"]:
        inst = bpy.data.objects.new("Luminaria", cache["Luminaria"][0].data)
        inst.location = (x, y, spec["h"] - 0.02)
        col.objects.link(inst)
        L = bpy.data.lights.new("luz", "POINT")
        L.energy = 120
        L.color = (1.0, 0.9, 0.75)
        L.shadow_soft_size = 0.3
        lo = bpy.data.objects.new("luz", L)
        lo.location = (x, y, spec["h"] - 0.35)
        col.objects.link(lo)
    # [A-076] folhas das portas na prévia: entreabertas (70 graus) para dentro; portões largos abertos para fora
    for d in door_list(spec):
        if d["style"] not in cache:
            lb = door_leaf(d["style"])
            lob, lcols = lb.build(col)
            lob.hide_render = True
            lob.hide_viewport = True
            for c in lcols:
                c.hide_viewport = True
            cache[d["style"]] = (lob, lcols, 0.0, 2.2)
        w = d["width_m"]
        leaves = 2 if d["double"] else 1
        lw = max(0.2, (w / 2 if d["double"] else w) - 0.07 * (1.5 if d["double"] else 2.0))
        # graus no sistema da Unreal (yaw da dobradiça): portas externas abertas para fora (a câmera de dentro vê
        # o cômodo livre), internas entreabertas
        ang = -100.0 if d["start_open"] else (-80.0 if not d["inner"] else 70.0)
        yaw = math.radians(d["yaw"])
        for k in range(leaves):
            sgn = 1 if k == 0 else -1                  # folha A: dobradiça em -Y da Unreal (= +Y do Blender)
            hx_, hy_ = 0.0, sgn * (w / 2 - 0.07)
            inst = bpy.data.objects.new(f"porta_{len(obs)}", cache[d["style"]][0].data)
            # Blender: y invertido em relação à Unreal, então o giro também inverte
            leaf_rot = -math.radians(ang) * (1 if k == 0 else -1) + (0 if k == 0 else math.pi)
            inst.rotation_euler = (0, 0, yaw + leaf_rot)
            inst.scale = (1.0, lw, (d["height_m"] - 0.03) / 2.2)
            inst.location = (d["x"] + hx_ * math.cos(yaw) - hy_ * math.sin(yaw), d["y"] + hx_ * math.sin(yaw) + hy_ * math.cos(yaw), 0.01)
            col.objects.link(inst)
            obs.append(inst)
    # marcadores dos itens (bolinhas coloridas) e baús (caixa) na prévia
    for (t, x, y, z) in spec["pickups"]:
        b = Builder(f"item_{t}")
        b.box((x, y, z + 0.15), (0.3, 0.3, 0.3), mat("Amarelo" if t in ("AMMO", "FURY") else "Vermelho"))
        b.build(col)
    for (lab, x, y, yaw) in spec["chests"]:
        b = Builder(f"bau_{lab}")
        b.box((x, y, 0.27), (1.0, 0.72, 0.53), mat("MadeiraVelha"), math.radians(yaw))
        b.build(col)
    return obs


def hero_dummy(col, x, y, yaw=0.0):
    """Boneco de 1,80 m para dar escala nas prévias."""
    b = Builder("HeroiEscala")
    b.cyl((x, y, 0.85), 0.22, 1.1, mat("Laranja"), 12)
    b.cyl((x, y, 1.62), 0.13, 0.3, mat("Colchao"), 12)
    b.box((x, y, 0.3), (0.3, 0.42, 0.6), mat("Azul"))
    return b.build(col)[0]


# ====================================================================== render

def setup_render(sc, w=1280, h=720, samples=48):
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 1
    sc.cycles.transmission_bounces = 2
    sc.cycles.transparent_max_bounces = 4
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in sc.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    world = bpy.data.worlds.new("Ceu")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.35, 0.30, 0.55, 1)
    bg.inputs["Strength"].default_value = 0.9
    sun = bpy.data.lights.new("Sol", "SUN")
    sun.energy = 2.8
    sun.color = (1.0, 0.78, 0.6)
    so = bpy.data.objects.new("Sol", sun)
    so.rotation_euler = (math.radians(55), 0, math.radians(35))
    sc.collection.objects.link(so)
    # chão em volta (terra) para a prévia
    g = Builder("Chao")
    g.box((0, 0, -0.6), (80, 80, 0.4), mat("Asfalto") if False else flat_mat("Couro"))
    g.build(sc.collection)


def camera(sc, loc, look, lens=24):
    cam = bpy.data.cameras.new("Cam")
    cam.lens = lens
    cam.clip_start = 0.05
    co = bpy.data.objects.new("Cam", cam)
    co.location = loc
    d = Vector(look) - Vector(loc)
    co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(co)
    sc.camera = co
    return co


def render(sc, path):
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def previews(key, spec, ob, out_dir, samples):
    sc = bpy.context.scene
    os.makedirs(out_dir, exist_ok=True)
    sx, sy = spec["size"]
    h = spec["h"]
    files = []
    # 1) fora, 3/4 de frente
    hero_dummy(sc.collection, sx / 2 + 2.0, -1.0)
    c = camera(sc, (sx / 2 + 10 + sx * 0.4, -sy * 0.8 - 6, 2.2 + h * 0.6), (0, 0, h * 0.45), 24)
    p = os.path.join(out_dir, f"{key}_fora.png")
    render(sc, p)
    files.append(p)
    bpy.data.objects.remove(c)
    # 2) corte de cima (sem teto): esconde a casca e mostra só a parte de baixo das paredes com um plano de corte
    ob.hide_render = True
    cut = cut_copy(ob, h * 0.55)
    c = camera(sc, (0.01, 0.01, max(sx, sy) * 1.25 + 6), (0, 0, 0), 30)
    p = os.path.join(out_dir, f"{key}_planta.png")
    # planta: renderizador rápido (Workbench) com as texturas; a luz não importa aqui
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.display.shading.show_shadows = True
    render(sc, p)
    sc.render.engine = "CYCLES"
    files.append(p)
    bpy.data.objects.remove(c)
    bpy.data.objects.remove(cut)
    ob.hide_render = False
    # 3) olho do herói (1,70 m) logo depois da porta principal, olhando para dentro
    dx = spec["walls"]["+X"]
    doors = [o for o in dx if o[4] == "porta"]
    dy = doors[0][0] if doors else 0.0
    c = camera(sc, (sx / 2 - 0.6, dy, 1.7), (-sx / 2, dy * 0.2, 1.3), 18)
    p = os.path.join(out_dir, f"{key}_dentro.png")
    render(sc, p)
    files.append(p)
    bpy.data.objects.remove(c)
    return files


def cut_copy(ob, z_cut):
    """Cópia da casca cortada na altura z_cut (planta baixa da prévia)."""
    cp = ob.copy()
    cp.data = ob.data.copy()
    bpy.context.scene.collection.objects.link(cp)
    cp.hide_render = False
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(cp.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z_cut), plane_no=(0, 0, 1), clear_outer=True)
    bmesh.ops.contextual_create(bm, geom=[e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)])
    bm.to_mesh(cp.data)
    bm.free()
    return cp


# ====================================================================== exportação

def export_fbx(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.hide_viewport = False
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL",
                             axis_forward="X", axis_up="Z", object_types={"MESH"}, mesh_smooth_type="FACE",
                             use_mesh_modifiers=True, add_leaf_bones=False, bake_space_transform=False)


def plan_entry(key, spec, furn_info):
    sx, sy = spec["size"]
    return {
        "nome": spec["nome"], "zona": spec["zona"], "size_m": [sx, sy], "h_m": spec["h"],
        "mesh": f"SM_INT_{key}", "note": spec.get("note", ""),
        "doors": [{"side": s, "offset_m": o[0], "width_m": o[1]} for s, ops in spec["walls"].items() for o in ops if o[4] == "porta"],
        "furniture": [{"mesh": f"SM_INT_{k}", "x": x, "y": y, "yaw": yaw, "radius_m": furn_info[k][0]} for k, x, y, yaw in spec["furniture"]],
        "door_leaves": [dict(d, mesh=f"SM_INT_{d['style']}") for d in door_list(spec)],   # [A-076]
        "lights": [{"x": x, "y": y, "z": spec["h"] - 0.35, "candelas": 30.0} for x, y in spec["lights"]],
        "luminaire_mesh": "SM_INT_Luminaria",
        "pickups": [{"type": t, "x": x, "y": y, "z": z} for t, x, y, z in spec["pickups"]],
        "chests": [{"label": lab, "x": x, "y": y, "yaw": yaw} for lab, x, y, yaw in spec["chests"]],
        "story": ({"label": f"Historia_INT_{key}", "titulo": spec["story"][0], "message": spec["story"][1],
                   "objective_hint": spec["story"][2]} if spec.get("story") else None),
        "camera_zone": {"extent_m": [sx / 2 - 0.1, sy / 2 - 0.1, spec["h"] / 2], "arm_cm": 190.0},
        "replaces": spec.get("replaces", {}), "place": spec.get("place"),
        "absorb_pickups": spec.get("absorb_pickups", {}),
    }


def main(argv=None):
    argv = argv if argv is not None else sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    out = next((a for a in argv if not a.startswith("--") and not a.startswith("PostoLoja")), os.path.join(REPO, "assets", "work", "interiors"))
    only = None
    for i, a in enumerate(argv):
        if a == "--only":
            only = set(argv[i + 1].split(","))
    do_render = "--no-render" not in argv
    do_export = "--no-export" not in argv
    samples = 12 if "--fast" in argv else 48
    os.makedirs(out, exist_ok=True)
    plan = {"version": 1, "unit": "m", "buildings": {}, "furniture": {}}
    furn_info = {}
    for key, spec in BUILDINGS.items():
        if only and key not in only:
            continue
        sc = reset()
        _MATS.clear()
        if do_render:
            setup_render(sc, *((960, 540) if "--fast" in argv else (1280, 720)), samples=samples)
        col = sc.collection
        ob, cols = build_building(key, spec, col)
        cache = {}
        place_furniture(spec, col, cache)
        for k, (fob, fcols, r, hh) in cache.items():
            furn_info[k] = (r, hh)
            if do_export and not os.path.exists(os.path.join(out, f"SM_INT_{k}.fbx")):
                export_fbx([fob] + fcols, os.path.join(out, f"SM_INT_{k}.fbx"))
        if do_export:
            export_fbx([ob] + cols, os.path.join(out, f"SM_INT_{key}.fbx"))
        plan["buildings"][key] = plan_entry(key, spec, furn_info)
        if do_render:
            for f in previews(key, spec, ob, os.path.join(out, "previews"), samples):
                print("prévia", f)
        print("ok", key)
    for k, (r, hh) in furn_info.items():
        plan["furniture"][f"SM_INT_{k}"] = {"radius_m": r, "height_m": hh}
    path = os.path.join(out, "interiors_l01.json")
    if only and os.path.exists(path):
        old = json.load(open(path, encoding="utf-8"))
        old["buildings"].update(plan["buildings"])
        old["furniture"].update(plan["furniture"])
        plan = old
    json.dump(plan, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("plano", path)


if __name__ == "__main__":
    main()
