"""Etapa 7 (Céu): troca o céu "da Terra" por um céu alienígena. Pode rodar de novo.

RODA NO EDITOR (caixa Cmd), sem Play:
  py "E:/game/utrazin-game/tools/unreal/setup_alien_sky.py"            (padrão: entardecer alienígena)
  py "E:/game/utrazin-game/tools/unreal/setup_alien_sky.py" day        (dia)
  py "E:/game/utrazin-game/tools/unreal/setup_alien_sky.py" night      (noite)

Antes, gere as malhas e texturas (uma vez; já vêm no repositório em assets/work/sky/):
  blender -b --python tools/blender/make_sky.py -- assets/work/sky

O que faz:
 1. Importa assets/work/sky/*.png e *.fbx para /Game/Environment/Sky (Textures/Meshes)
 2. Cria os materiais M_Sky_Body (planeta e luas, sem luz própria, sombreado pelo sol no material),
    M_Sky_Ring (anéis translúcidos com a sombra do planeta), M_Sky_Stars (cúpula de estrelas aditiva)
    e M_Sky_Aurora (faixa de aurora verde animada) + instâncias MI_Sky_*
 3. Em cada mapa (o aberto agora, /Game/Levels/Test/L_VehicleTest e
    /Game/Levels/L01_ZombieValley/L01_ZombieValley, se existirem):
    - apaga os atores com a tag AlienSkyGen (deste script) e os recria: planeta com anéis, 2 luas,
      cúpula de estrelas e aurora (pasta "Ceu" no Outliner);
    - apaga TODAS as VolumetricCloud (nuvens da Terra);
    - reajusta (ou cria) Sol, SkyAtmosphere, SkyLight e ExponentialHeightFog com as cores alienígenas;
    - cria/reaproveita UM PostProcessVolume infinito (tag AlienSkyGen, "ExposicaoFixa") com exposição
      MANUAL (o olho não se adapta: o céu não fica preto/claro conforme a direção da câmera) e sem
      exposição local; SkyLight sem captura em tempo real (estável);
    - salva o mapa. No fim reabre o mapa que estava aberto.
 O mapa aberto, se nunca foi salvo, recebe o céu mas NÃO é salvo (salve você).

Método (A-045 em docs/decisions/ASSUMPTIONS.md): os astros ficam PARADOS a 50 a 70 km do centro
do mapa, enormes (escala ~11000), com material "Is Sky" (sem neblina e sem perspectiva aérea).
O mapa tem 2 x 2 km, então andar até a borda muda a posição deles no céu em no máximo ~1,5 grau:
não precisa de ator que siga a câmera.

Se rodar build_l01.py ou build_vehicle_test.py de novo, rode este script depois
(ou o build chama apply_to_current_level() deste módulo).
Relatório: reports/setup_alien_sky.json
"""
import json
import math
import os
import sys
import traceback
from datetime import datetime

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SRC = os.path.join(REPO, "assets", "work", "sky")
SKY = "/Game/Environment/Sky"
TEX = f"{SKY}/Textures"
MESHES = f"{SKY}/Meshes"
MATS = f"{SKY}/Materials"
TAG = "AlienSkyGen"
FOLDER = "Ceu"
EXTRA_MAPS = ["/Game/Levels/Test/L_VehicleTest", "/Game/Levels/L01_ZombieValley/L01_ZombieValley"]
DEFAULT_PRESET = "dusk"

# ------------------------------------------------------------------ AJUSTES (mude aqui e rode de novo)
# Gira o arranjo inteiro (sol + astros + aurora) em volta do mapa, em graus.
SKY_YAW = 0.0
# Raio da malha-base (esfera de 1 m no Blender = 100 cm na Unreal).
MESH_RADIUS_CM = 100.0
# Anéis: raio interno/externo em raios do planeta (iguais aos de make_sky.py).
RING_INNER = 1.25
RING_OUTER = 2.30
# Astros: azimute (graus, 0 = +X, 90 = +Y, somado a SKY_YAW), elevação acima do horizonte,
# distância ao centro do mapa (km) e raio aparente (graus). roll/pitch inclinam os anéis.
BODIES = [
    {"key": "planet", "label": "Ceu_Planeta", "mesh": "SM_Sky_Planet", "mi": "MI_Sky_Planet",
     "az": 0.0, "el": 21.0, "dist_km": 60.0, "ang_r": 11.0, "roll": 16.0, "pitch": 9.0},
    {"key": "moon_a", "label": "Ceu_LuaGelo", "mesh": "SM_Sky_Moon", "mi": "MI_Sky_MoonA",
     "az": -34.0, "el": 41.0, "dist_km": 50.0, "ang_r": 3.0, "roll": 0.0, "pitch": 0.0},
    {"key": "moon_b", "label": "Ceu_LuaFerrugem", "mesh": "SM_Sky_Moon", "mi": "MI_Sky_MoonB",
     "az": 52.0, "el": 11.0, "dist_km": 70.0, "ang_r": 1.8, "roll": 0.0, "pitch": 25.0},
]
# Aurora: arco de raio 1 na malha (de -55 a +55 graus, altura 0,18 a ~0,52); escala = raio em metros.
AURORA = {"label": "Ceu_Aurora", "mesh": "SM_Sky_Aurora", "mi": "MI_Sky_Aurora", "az": 128.0, "radius_km": 40.0}
STAR_DOME = {"label": "Ceu_Estrelas", "mesh": "SM_Sky_StarDome", "mi": "MI_Sky_Stars", "radius_km": 200.0}
# Ordem de desenho dos translúcidos (maior = por cima): estrelas atrás de tudo.
SORT_PRIORITY = {"stars": -10, "aurora": 0, "rings": 2}

# Atmosfera alienígena (SkyAtmosphere). Terra: Rayleigh (0.175, 0.41, 1.0) x 0.0331, Mie 0.004.
# Rayleigh com pouco verde e escala menor (atmosfera mais fina, avermelha menos o sol baixo) = céu
# roxo; Mie verde-água = brilho turquesa em volta do sol; "ozônio" que come vermelho = menos marrom
# no entardecer. sky_luminance (por preset) puxa mais para o violeta.
ATMOSPHERE = {
    "rayleigh": (0.50, 0.22, 1.00), "rayleigh_scale": 0.014, "rayleigh_km": 8.0,
    "mie": (0.15, 0.95, 0.80), "mie_scale": 0.010, "mie_km": 1.2, "mie_g": 0.85,
    "mie_abs": (0.50, 0.30, 0.60), "mie_abs_scale": 0.0008,
    "ozone": (1.80, 0.30, 0.10), "ozone_scale": 0.0022,
    "ground_albedo": (60, 40, 80), "multi_scattering": 1.0,
}
# Presets de hora do dia. sun_az/sun_el = de onde vem a luz (graus). Brilhos em "nits" (o projeto
# usa exposição fixa: r.DefaultFeature.AutoExposure=False). fog_* = ExponentialHeightFog.
PRESETS = {
    "dusk": {  # entardecer alienígena (padrão): sol baixo e laranja, plantas brilham mais
        "exposure_bias": 0.5, "multi_scattering": 1.6,
        "sun_az": 250.0, "sun_el": 7.0, "sun_lux": 5.0, "sun_color": (255, 185, 150), "sun_disk": (1.0, 0.75, 0.55),
        "sun_angle": 1.6, "sky_luminance": (1.0, 1.0, 1.5),
        "planet_bright": 1.5, "moon_bright": 1.7, "ambient": 0.06, "rim": 0.55, "haze": (0.035, 0.015, 0.05),
        "ring_bright": 1.3, "ring_opacity": 0.9, "stars": 1.2, "aurora": 3.0,
        "fog_density": 0.0045, "fog_falloff": 0.18, "fog_color": (0.26, 0.13, 0.38), "fog_dir": (0.65, 0.30, 0.16),
        "fog_dir_exp": 6.0, "fog_start": 2500.0, "skylight": 1.25, "lower_hemi": (0.05, 0.03, 0.08),
    },
    "day": {
        "exposure_bias": -1.0,
        "sun_az": 250.0, "sun_el": 42.0, "sun_lux": 8.0, "sun_color": (255, 214, 182), "sun_disk": (1.0, 0.9, 0.8),
        "sun_angle": 1.4, "sky_luminance": (1.0, 1.0, 1.3),
        "planet_bright": 2.6, "moon_bright": 3.0, "ambient": 0.10, "rim": 0.45, "haze": (0.10, 0.06, 0.14),
        "ring_bright": 2.2, "ring_opacity": 0.75, "stars": 0.0, "aurora": 0.6,
        "fog_density": 0.0035, "fog_falloff": 0.2, "fog_color": (0.30, 0.20, 0.45), "fog_dir": (0.5, 0.35, 0.2),
        "fog_dir_exp": 8.0, "fog_start": 3000.0, "skylight": 1.0, "lower_hemi": (0.08, 0.05, 0.10),
    },
    "night": {  # o "sol" vira luz fria refletida pelo planeta gigante; céu escuro, estrelas e aurora fortes
        "exposure_bias": 1.0,
        "sun_az": 250.0, "sun_el": 18.0, "sun_lux": 1.4, "sun_color": (150, 196, 255), "sun_disk": (0.0, 0.0, 0.0),
        "sun_angle": 0.5, "sky_luminance": (0.15, 0.14, 0.25),
        "planet_bright": 0.9, "moon_bright": 1.0, "ambient": 0.03, "rim": 0.4, "haze": (0.01, 0.005, 0.02),
        "ring_bright": 0.8, "ring_opacity": 0.9, "stars": 6.0, "aurora": 4.0,
        "fog_density": 0.005, "fog_falloff": 0.18, "fog_color": (0.06, 0.05, 0.12), "fog_dir": (0.05, 0.12, 0.15),
        "fog_dir_exp": 6.0, "fog_start": 2000.0, "skylight": 1.6, "lower_hemi": (0.02, 0.02, 0.04),
    },
}
AURORA_COLORS = {"bottom": (0.10, 1.0, 0.35), "top": (0.30, 0.20, 1.0)}
PLANET_RIM = (0.45, 0.95, 0.9)
# Neblina volumétrica: desligada (custa ~1 a 2 ms). True liga com densidade baixa.
VOLUMETRIC_FOG = False
# 0 = desligado. Em cm: a neblina de altura para de agir depois dessa distância (plano B se os
# astros ficarem cobertos de neblina mesmo com "Is Sky"; ex.: 2500000 = 25 km).
# [A-063] 30 km: o mapa tem 2 km, então nada muda no chão; os astros (45 a 70 km) ficam fora da neblina
# agora que o material deles não é mais "Is Sky".
FOG_CUTOFF_CM = 3000000.0
# [A-063] "Is Sky" no planeta e nas luas dava o aviso "YOUR SCENE CONTAINS A SKYDOME MESH WITH A SKY MATERIAL
# BUT IT DOES NOT COVER THAT PART OF THE SCREEN" (eles cobrem só um pedaço do céu). False = material comum
# (unlit opaco) e neblina cortada em FOG_CUTOFF_CM. Se o planeta ficar lavado pela atmosfera, volte para True
# (o aviso só aparece no editor e em build de desenvolvimento, não no jogo final).
BODY_IS_SKY = False

# Exposição FIXA (A-050). Bug: "o céu fica preto ou mais claro dependendo de pra onde eu olho" = a câmera
# adaptando o brilho ao que está na tela. Um PostProcessVolume infinito trava a exposição em modo Manual
# (EV100 = EXPOSURE_EV100, sem câmera física) + "exposure_bias" do preset (em stops: +1 = 2x mais claro).
# Cena escura demais: aumente exposure_bias do preset; clara demais: diminua. Rode o script de novo.
EXPOSURE_EV100 = 0.0
# Exposição local (UE 5.1+) também clareia/escurece partes da tela conforme o que aparece: desligada (1.0).
LOCAL_EXPOSURE_OFF = True
PPV_LABEL = "ExposicaoFixa"
PPV_PRIORITY = 100.0
# SkyLight: captura em tempo real refaz a luz do céu aos poucos (pode "pulsar"); o céu é parado, então
# uma captura só (no load do mapa e quando o script roda) é estável e mais barata.
SKYLIGHT_REAL_TIME = False

R = {"time": datetime.now().isoformat(), "preset": None, "maps": {}, "assets": {}, "steps": [], "warnings": [], "errors": []}


# ------------------------------------------------------------------ funções puras (testadas em tests/python)
def parse_preset(argv):
    """Primeiro argumento conhecido (dusk/day/night ou entardecer/dia/noite); senão o padrão."""
    alias = {"entardecer": "dusk", "dia": "day", "noite": "night"}
    for a in argv or []:
        k = alias.get(str(a).lower(), str(a).lower())
        if k in PRESETS:
            return k
    return DEFAULT_PRESET


def dir_from_az_el(az, el):
    """Vetor unitário (x, y, z) para azimute/elevação em graus (convenção Unreal: yaw 0 = +X, 90 = +Y)."""
    a, e = math.radians(az), math.radians(el)
    return (math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))


def rotator_axes(pitch, yaw, roll):
    """Eixos X, Y, Z do ator (igual ao FRotationMatrix da Unreal), em graus."""
    p, y, r = math.radians(pitch), math.radians(yaw), math.radians(roll)
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    x = (cp * cy, cp * sy, sp)
    ya = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
    z = (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)
    return x, ya, z


def sun_rotator(sun_az, sun_el):
    """(pitch, yaw, roll) da DirectionalLight para a luz VIR de sun_az/sun_el."""
    return (-float(sun_el), (float(sun_az) + 180.0) % 360.0, 0.0)


def sun_direction(preset, sky_yaw=SKY_YAW):
    """Direção da superfície PARA o sol (o mesmo que o nó SkyAtmosphereLightDirection devolve)."""
    return dir_from_az_el(preset["sun_az"] + sky_yaw, preset["sun_el"])


def body_transform(body, center_cm=(0.0, 0.0, 0.0), sky_yaw=SKY_YAW):
    """Local (cm), rotação (pitch, yaw, roll) e escala uniforme de um astro."""
    az = body["az"] + sky_yaw
    d = dir_from_az_el(az, body["el"])
    dist_cm = body["dist_km"] * 100000.0
    loc = tuple(center_cm[i] + d[i] * dist_cm for i in range(3))
    radius_cm = dist_cm * math.sin(math.radians(body["ang_r"]))
    return loc, (body.get("pitch", 0.0), az, body.get("roll", 0.0)), radius_cm / MESH_RADIUS_CM


def package_from_world_path(path):
    """'/Game/Levels/X/L_Map.L_Map' -> '/Game/Levels/X/L_Map'; mapa nunca salvo ('/Temp/...') -> None."""
    if not path:
        return None
    pkg = str(path).split(".")[0]
    return pkg if pkg.startswith("/Game/") else None


def maps_to_process(current, extra, exists):
    out = []
    for m in [current, *extra]:
        if m and m not in out and exists(m):
            out.append(m)
    return out


def exposure_settings(preset_name):
    """Campos do FPostProcessSettings (nomes do Python) para a exposição fixa do preset."""
    p = PRESETS[preset_name]
    out = {
        "override_auto_exposure_method": True, "auto_exposure_method": "MANUAL",
        "override_auto_exposure_apply_physical_camera_exposure": True,
        "auto_exposure_apply_physical_camera_exposure": False,
        "override_auto_exposure_bias": True, "auto_exposure_bias": float(p.get("exposure_bias", 0.0)),
        # Reserva: se o modo Manual não existir, Histogram com mínimo = máximo também não adapta.
        "override_auto_exposure_min_brightness": True, "auto_exposure_min_brightness": float(EXPOSURE_EV100),
        "override_auto_exposure_max_brightness": True, "auto_exposure_max_brightness": float(EXPOSURE_EV100),
    }
    if LOCAL_EXPOSURE_OFF:
        out.update({
            "override_local_exposure_highlight_contrast_scale": True, "local_exposure_highlight_contrast_scale": 1.0,
            "override_local_exposure_shadow_contrast_scale": True, "local_exposure_shadow_contrast_scale": 1.0,
        })
    return out


def texture_kind(filename):
    """Como importar cada PNG do céu."""
    if filename.startswith("T_Sky_Aurora"):
        return "mask"
    if filename.startswith("T_Sky_Stars"):
        return "sky"
    return "color"


# ------------------------------------------------------------------ editor
def log(m):
    import unreal
    R["steps"].append(m)
    unreal.log(f"[alien_sky] {m}")


def warn(m):
    import unreal
    R["warnings"].append(m)
    unreal.log_warning(f"[alien_sky] {m}")


def err(where, exc):
    import unreal
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-1000:]})
    unreal.log_error(f"[alien_sky] {where}: {exc}")


def setp(obj, k, v, where=""):
    """set_editor_property com aviso no relatório se o nome não existir nesta versão."""
    try:
        obj.set_editor_property(k, v)
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"{where or obj.get_name()}.{k}: {exc}")
        return False


def lc(c):
    import unreal
    return unreal.LinearColor(float(c[0]), float(c[1]), float(c[2]), 1.0)


def color_u8(c):
    """FColor por nome (a ordem posicional do FColor é B, G, R na memória: nomes evitam troca)."""
    import unreal
    return unreal.Color(r=int(c[0]), g=int(c[1]), b=int(c[2]), a=255)


def vec(c):
    import unreal
    return unreal.Vector(float(c[0]), float(c[1]), float(c[2]))


def rot(p_y_r):
    import unreal
    p, y, r = p_y_r
    return unreal.Rotator(roll=float(r), pitch=float(p), yaw=float(y))


# ---------------- 1. import
def import_png(path, kind):
    import unreal
    eal = unreal.EditorAssetLibrary
    name = os.path.splitext(os.path.basename(path))[0]
    task = unreal.AssetImportTask()
    task.filename = path
    task.destination_path = TEX
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    t = eal.load_asset(f"{TEX}/{name}")
    if t is None:
        raise RuntimeError(f"textura não importada: {path}")
    if kind == "mask":
        setp(t, "srgb", False, name)
    if kind == "sky":
        setp(t, "lod_group", unreal.TextureGroup.TEXTUREGROUP_SKYBOX, name)
    setp(t, "never_stream", True, name)
    eal.save_loaded_asset(t, only_if_is_dirty=False)
    return t


def import_mesh(path):
    import unreal
    eal = unreal.EditorAssetLibrary
    name = os.path.splitext(os.path.basename(path))[0]
    task = unreal.AssetImportTask()
    task.filename = path
    task.destination_path = MESHES
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    o = unreal.FbxImportUI()
    o.import_mesh = True
    o.import_as_skeletal = False
    o.import_animations = False
    o.import_materials = False
    o.import_textures = False
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    d = o.static_mesh_import_data
    for k, v in (("combine_meshes", True), ("auto_generate_collision", False), ("generate_lightmap_u_vs", False),
                 ("build_nanite", False), ("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE),
                 ("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)):
        setp(d, k, v, f"import {name}")
    task.options = o
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sm = eal.load_asset(f"{MESHES}/{name}")
    if sm is None and task.imported_object_paths:
        sm = eal.load_asset(str(task.imported_object_paths[0]).split(".")[0])
    if not isinstance(sm, unreal.StaticMesh):
        raise RuntimeError(f"malha não importada: {path}")
    return sm


# ---------------- 2. materiais
class MB:
    """Monta um material por nós (MaterialEditingLibrary). Mesmo padrão de setup_wave1.py."""

    def __init__(self, path):
        import unreal
        self.u = unreal
        self.eal = unreal.EditorAssetLibrary
        self.mel = unreal.MaterialEditingLibrary
        folder, name = path.rsplit("/", 1)
        self.eal.make_directory(folder)
        if self.eal.does_asset_exist(path):
            self.m = self.eal.load_asset(path)
            self.mel.delete_all_material_expressions(self.m)
        else:
            self.m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                name, folder, unreal.Material, unreal.MaterialFactoryNew())
        self.x, self.y = -1600, 0

    def node(self, cls, **props):
        e = self.mel.create_material_expression(self.m, cls, self.x, self.y)
        self.y += 150
        if self.y > 2400:
            self.y, self.x = 0, self.x + 280
        for k, v in props.items():
            setp(e, k, v, f"{self.m.get_name()}.{cls.__name__}")
        return e

    def opt(self, cls_name, **props):
        """Nó opcional: None se a classe não existir nesta versão da Unreal."""
        cls = getattr(self.u, cls_name, None)
        if cls is None:
            warn(f"{self.m.get_name()}: nó {cls_name} não existe nesta versão (usando o parâmetro)")
            return None
        return self.node(cls, **props)

    def link(self, a, a_out, b, b_in):
        if not self.mel.connect_material_expressions(a, a_out, b, b_in):
            warn(f"{self.m.get_name()}: ligação {a.get_name()}.{a_out} -> {b.get_name()}.{b_in} falhou")

    def out(self, e, prop, e_out=""):
        if not self.mel.connect_material_property(e, e_out, prop):
            warn(f"{self.m.get_name()}: saída {prop} não ligou")

    def scalar(self, name, v):
        return self.node(self.u.MaterialExpressionScalarParameter, parameter_name=name, default_value=float(v))

    def vector(self, name, c):
        return self.node(self.u.MaterialExpressionVectorParameter, parameter_name=name, default_value=lc(c))

    def rgb(self, e, e_out=""):
        m = self.node(self.u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
        self.link(e, e_out, m, "")
        return m

    def chan(self, e, ch, e_out=""):
        m = self.node(self.u.MaterialExpressionComponentMask, r=ch == "r", g=ch == "g", b=ch == "b", a=ch == "a")
        self.link(e, e_out, m, "")
        return m

    def texp(self, name, texture, uv=None, linear=False):
        e = self.node(self.u.MaterialExpressionTextureSampleParameter2D, parameter_name=name, texture=texture)
        if linear:
            setp(e, "sampler_type", self.u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR, name)
        if uv is not None:
            self.link(uv, "", e, "UVs")
        return e

    def bin(self, cls, a, b=None, a_out="", b_out="", cb=None):
        e = self.node(cls)
        self.link(a, a_out, e, "A")
        if b is not None:
            self.link(b, b_out, e, "B")
        elif cb is not None:
            setp(e, "const_b", float(cb))
        return e

    def mul(self, a, b=None, cb=None, a_out="", b_out=""):
        return self.bin(self.u.MaterialExpressionMultiply, a, b, a_out, b_out, cb)

    def add(self, a, b=None, cb=None, a_out="", b_out=""):
        return self.bin(self.u.MaterialExpressionAdd, a, b, a_out, b_out, cb)

    def sub(self, a, b=None, cb=None):
        return self.bin(self.u.MaterialExpressionSubtract, a, b, cb=cb)

    def div(self, a, b=None, cb=None):
        return self.bin(self.u.MaterialExpressionDivide, a, b, cb=cb)

    def dot(self, a, b):
        return self.bin(self.u.MaterialExpressionDotProduct, a, b)

    def sat(self, a):
        e = self.node(self.u.MaterialExpressionSaturate)
        self.link(a, "", e, "")
        return e

    def lerp(self, a, b, alpha, ca=None, cb=None):
        e = self.node(self.u.MaterialExpressionLinearInterpolate)
        if a is not None:
            self.link(a, "", e, "A")
        else:
            setp(e, "const_a", float(ca))
        if b is not None:
            self.link(b, "", e, "B")
        else:
            setp(e, "const_b", float(cb))
        self.link(alpha, "", e, "Alpha")
        return e

    def sun_dir(self):
        """Direção para o sol: nó SkyAtmosphereLightDirection (segue o Sol do mapa) misturado com o
        parâmetro SunDirection (que o script também preenche). UseAtmosphereSun 0 = só o parâmetro."""
        p = self.rgb(self.vector("SunDirection", (0.0, 0.0, 1.0)))
        a = self.opt("MaterialExpressionSkyAtmosphereLightDirection", light_index=0)
        if a is None:
            return p
        return self.lerp(p, a, self.scalar("UseAtmosphereSun", 1.0))

    def settings(self, blend, two_sided=False, is_sky=False, fog=True):
        u = self.u
        setp(self.m, "shading_model", u.MaterialShadingModel.MSM_UNLIT)
        setp(self.m, "blend_mode", blend)
        setp(self.m, "two_sided", two_sided)
        setp(self.m, "is_sky", bool(is_sky))   # [A-063] também DESLIGA (material já existente)
        if not fog:
            # "Apply Fogging" = bUseTranslucencyVertexFog; desligado = sem neblina/perspectiva aérea
            setp(self.m, "use_translucency_vertex_fog", False)

    def finish(self):
        self.mel.recompile_material(self.m)
        self.eal.save_loaded_asset(self.m, only_if_is_dirty=False)
        log(f"material {self.m.get_name()} pronto")
        return self.m


def mat_body(tex):
    """Planeta e luas: unlit opaco "Is Sky"; luz do sol calculada no material (lado escuro + borda)."""
    import unreal
    MP = unreal.MaterialProperty
    b = MB(f"{MATS}/M_Sky_Body")
    b.settings(unreal.BlendMode.BLEND_OPAQUE, is_sky=BODY_IS_SKY)
    albedo = b.texp("Albedo", tex)
    n = b.node(unreal.MaterialExpressionVertexNormalWS)
    lam = b.dot(n, b.sun_dir())
    # terminador suave: 0,15 de "luz enrolada" para o lado escuro
    s = b.sat(b.add(b.mul(lam, cb=0.85), cb=0.15))
    shade = b.lerp(b.scalar("Ambient", 0.06), None, s, cb=1.0)
    col = b.mul(b.mul(b.mul(b.rgb(albedo), shade), b.scalar("Brightness", 1.5)), b.rgb(b.vector("Tint", (1, 1, 1))))
    fres = b.node(unreal.MaterialExpressionFresnel, exponent=3.0, base_reflect_fraction=0.0)
    rim = b.mul(b.mul(b.mul(fres, b.rgb(b.vector("RimColor", PLANET_RIM))), b.scalar("RimStrength", 0.5)), s)
    em = b.add(b.add(col, rim), b.rgb(b.vector("HazeColor", (0.03, 0.015, 0.05))))
    b.out(em, MP.MP_EMISSIVE_COLOR)
    return b.finish()


def mat_ring(tex):
    """Anéis: translúcido unlit dos dois lados, sem neblina, com a sombra do planeta (cilindro)."""
    import unreal
    MP = unreal.MaterialProperty
    b = MB(f"{MATS}/M_Sky_Ring")
    b.settings(unreal.BlendMode.BLEND_TRANSLUCENT, two_sided=True, fog=False)
    t = b.texp("RingTex", tex)
    L = b.sun_dir()
    d = b.sub(b.node(unreal.MaterialExpressionWorldPosition), b.node(unreal.MaterialExpressionObjectPositionWS))
    tl = b.dot(d, L)                                   # distância ao longo da luz
    dist = b.node(unreal.MaterialExpressionDistance)    # distância até o eixo da sombra
    b.link(d, "", dist, "A")
    b.link(b.mul(L, tl), "", dist, "B")
    rad = b.scalar("PlanetRadius", 1100000.0)           # cm (o script preenche)
    outside = b.sat(b.div(b.sub(dist, rad), b.mul(rad, cb=0.03)))
    behind = b.sat(b.div(b.mul(tl, cb=-1.0), b.mul(rad, cb=0.2)))
    shadow = b.lerp(None, outside, behind, ca=1.0)
    col = b.mul(b.mul(b.mul(b.rgb(t), b.scalar("Brightness", 1.3)), shadow), b.rgb(b.vector("Tint", (1, 1, 1))))
    b.out(col, MP.MP_EMISSIVE_COLOR)
    b.out(b.mul(b.chan(t, "a"), b.scalar("Opacity", 0.9)), MP.MP_OPACITY)
    return b.finish()


def mat_stars(tex):
    """Cúpula de estrelas: aditiva, sem neblina; some perto do sol (ver StarBrightness por preset)."""
    import unreal
    MP = unreal.MaterialProperty
    b = MB(f"{MATS}/M_Sky_Stars")
    b.settings(unreal.BlendMode.BLEND_ADDITIVE, two_sided=True, fog=False)
    t = b.texp("StarTex", tex)
    cv = b.node(unreal.MaterialExpressionCameraVectorWS)
    fade = b.sat(b.add(b.mul(b.dot(cv, b.sun_dir()), cb=1.6), cb=1.5))
    b.out(b.mul(b.mul(b.rgb(t), fade), b.scalar("StarBrightness", 2.5)), MP.MP_EMISSIVE_COLOR)
    return b.finish()


def mat_aurora(tex):
    """Aurora: aditiva, dois painéis de raios andando em sentidos opostos (Panner), cor verde -> violeta."""
    import unreal
    MP = unreal.MaterialProperty
    b = MB(f"{MATS}/M_Sky_Aurora")
    b.settings(unreal.BlendMode.BLEND_ADDITIVE, two_sided=True, fog=False)
    uv1 = b.node(unreal.MaterialExpressionTextureCoordinate)
    p1 = b.node(unreal.MaterialExpressionPanner, speed_x=0.006, speed_y=0.0)
    b.link(uv1, "", p1, "Coordinate")
    uv2 = b.node(unreal.MaterialExpressionTextureCoordinate, u_tiling=2.3, v_tiling=1.0)
    p2 = b.node(unreal.MaterialExpressionPanner, speed_x=-0.011, speed_y=0.0)
    b.link(uv2, "", p2, "Coordinate")
    t1 = b.texp("AuroraTex", tex, p1, linear=True)
    t2 = b.texp("AuroraTex2", tex, p2, linear=True)
    t0 = b.texp("AuroraTex3", tex, uv1, linear=True)
    rays = b.mul(b.mul(b.chan(t1, "r"), b.chan(t2, "r")), cb=2.2)
    prof = b.chan(t0, "g")                               # perfil vertical (borda de baixo forte)
    height = b.chan(t0, "b")                             # 0 embaixo, 1 em cima
    color = b.lerp(b.rgb(b.vector("ColorBottom", AURORA_COLORS["bottom"])),
                   b.rgb(b.vector("ColorTop", AURORA_COLORS["top"])), height)
    vc = b.node(unreal.MaterialExpressionVertexColor)    # R = some nas pontas do arco
    em = b.mul(b.mul(b.mul(b.mul(rays, prof), color), b.scalar("Intensity", 2.2)), vc, b_out="R")
    b.out(em, MP.MP_EMISSIVE_COLOR)
    return b.finish()


def make_mi(name, parent):
    import unreal
    eal = unreal.EditorAssetLibrary
    path = f"{MATS}/{name}"
    mi = eal.load_asset(path) if eal.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    unreal.MaterialEditingLibrary.set_material_instance_parent(mi, parent)
    return mi


def mi_params(mi, scalars=None, vectors=None, textures=None):
    import unreal
    mel = unreal.MaterialEditingLibrary
    for k, v in (scalars or {}).items():
        try:
            mel.set_material_instance_scalar_parameter_value(mi, k, float(v))
        except Exception as exc:  # noqa: BLE001
            warn(f"{mi.get_name()}.{k}: {exc}")
    for k, v in (vectors or {}).items():
        try:
            mel.set_material_instance_vector_parameter_value(mi, k, lc(v))
        except Exception as exc:  # noqa: BLE001
            warn(f"{mi.get_name()}.{k}: {exc}")
    for k, v in (textures or {}).items():
        try:
            mel.set_material_instance_texture_parameter_value(mi, k, v)
        except Exception as exc:  # noqa: BLE001
            warn(f"{mi.get_name()}.{k}: {exc}")
    mel.update_material_instance(mi)
    unreal.EditorAssetLibrary.save_loaded_asset(mi, only_if_is_dirty=False)


ASSETS = {}


def ensure_assets(preset_name):
    """Importa texturas/malhas, monta materiais e instâncias (uma vez por execução)."""
    import unreal
    eal = unreal.EditorAssetLibrary
    if ASSETS.get("preset") == preset_name:
        return ASSETS
    if not ASSETS:
        if not os.path.isdir(SRC):
            raise RuntimeError(f"falta a pasta {SRC}: rode tools/blender/make_sky.py")
        for d in (TEX, MESHES, MATS):
            eal.make_directory(d)
        tex = {}
        for f in sorted(os.listdir(SRC)):
            if f.startswith("T_Sky_") and f.endswith(".png"):
                tex[f[:-4]] = import_png(os.path.join(SRC, f), texture_kind(f))
        meshes = {}
        for f in sorted(os.listdir(SRC)):
            if f.startswith("SM_Sky_") and f.endswith(".fbx"):
                meshes[f[:-4]] = import_mesh(os.path.join(SRC, f))
        need_t = ["T_Sky_Planet", "T_Sky_MoonA", "T_Sky_MoonB", "T_Sky_Rings", "T_Sky_Stars", "T_Sky_Aurora"]
        need_m = ["SM_Sky_Planet", "SM_Sky_Rings", "SM_Sky_Moon", "SM_Sky_StarDome", "SM_Sky_Aurora"]
        miss = [n for n in need_t if n not in tex] + [n for n in need_m if n not in meshes]
        if miss:
            raise RuntimeError(f"faltam arquivos em assets/work/sky: {miss} (rode make_sky.py)")
        log(f"{len(tex)} texturas e {len(meshes)} malhas importadas em {SKY}")
        R["assets"] = {"textures": sorted(tex), "meshes": sorted(meshes)}
        mats = {}
        for key, fn, t in (("body", mat_body, "T_Sky_Planet"), ("ring", mat_ring, "T_Sky_Rings"),
                           ("stars", mat_stars, "T_Sky_Stars"), ("aurora", mat_aurora, "T_Sky_Aurora")):
            try:
                mats[key] = fn(tex[t])
            except Exception as exc:  # noqa: BLE001
                err(f"material {key}", exc)
        if len(mats) < 4:
            raise RuntimeError("algum material do céu falhou (ver errors)")
        mis = {
            "MI_Sky_Planet": make_mi("MI_Sky_Planet", mats["body"]),
            "MI_Sky_MoonA": make_mi("MI_Sky_MoonA", mats["body"]),
            "MI_Sky_MoonB": make_mi("MI_Sky_MoonB", mats["body"]),
            "MI_Sky_Rings": make_mi("MI_Sky_Rings", mats["ring"]),
            "MI_Sky_Stars": make_mi("MI_Sky_Stars", mats["stars"]),
            "MI_Sky_Aurora": make_mi("MI_Sky_Aurora", mats["aurora"]),
        }
        # material padrão de cada malha (a lua B troca no ator)
        for mesh, mi in (("SM_Sky_Planet", "MI_Sky_Planet"), ("SM_Sky_Rings", "MI_Sky_Rings"),
                         ("SM_Sky_Moon", "MI_Sky_MoonA"), ("SM_Sky_StarDome", "MI_Sky_Stars"),
                         ("SM_Sky_Aurora", "MI_Sky_Aurora")):
            try:
                meshes[mesh].set_material(0, mis[mi])
                eal.save_loaded_asset(meshes[mesh], only_if_is_dirty=False)
            except Exception as exc:  # noqa: BLE001
                warn(f"{mesh} material: {exc}")
        ASSETS.update({"tex": tex, "meshes": meshes, "mis": mis})
    # parâmetros do preset (as instâncias são as mesmas em todos os mapas: vale o último preset rodado)
    P = PRESETS[preset_name]
    sd = sun_direction(P)
    tex, mis = ASSETS["tex"], ASSETS["mis"]
    planet = BODIES[0]
    _, _, planet_scale = body_transform(planet)
    mi_params(mis["MI_Sky_Planet"], {"Brightness": P["planet_bright"], "Ambient": P["ambient"], "RimStrength": P["rim"]},
              {"SunDirection": sd, "HazeColor": P["haze"], "RimColor": PLANET_RIM}, {"Albedo": tex["T_Sky_Planet"]})
    mi_params(mis["MI_Sky_MoonA"], {"Brightness": P["moon_bright"], "Ambient": P["ambient"], "RimStrength": P["rim"] * 0.4},
              {"SunDirection": sd, "HazeColor": P["haze"], "RimColor": (0.7, 0.8, 1.0)}, {"Albedo": tex["T_Sky_MoonA"]})
    mi_params(mis["MI_Sky_MoonB"], {"Brightness": P["moon_bright"], "Ambient": P["ambient"], "RimStrength": P["rim"] * 0.3},
              {"SunDirection": sd, "HazeColor": P["haze"], "RimColor": (1.0, 0.6, 0.4)}, {"Albedo": tex["T_Sky_MoonB"]})
    mi_params(mis["MI_Sky_Rings"], {"Brightness": P["ring_bright"], "Opacity": P["ring_opacity"],
                                    "PlanetRadius": planet_scale * MESH_RADIUS_CM}, {"SunDirection": sd})
    mi_params(mis["MI_Sky_Stars"], {"StarBrightness": P["stars"]}, {"SunDirection": sd})
    mi_params(mis["MI_Sky_Aurora"], {"Intensity": P["aurora"]},
              {"ColorBottom": AURORA_COLORS["bottom"], "ColorTop": AURORA_COLORS["top"]})
    ASSETS["preset"] = preset_name
    log(f"instâncias MI_Sky_* ajustadas para o preset '{preset_name}'")
    return ASSETS


# ---------------- 3. atores no mapa
def comp_of(actor, cls):
    try:
        return actor.get_component_by_class(cls)
    except Exception:  # noqa: BLE001
        return None


def map_center(actors):
    """Centro XY dos StaticMeshActors (sem os do céu); z = chão mais baixo. Sem malhas: origem."""
    import unreal
    lo, hi = [1e18, 1e18, 1e18], [-1e18, -1e18, -1e18]
    n = 0
    for a in actors:
        if not isinstance(a, unreal.StaticMeshActor) or TAG in [str(t) for t in a.tags]:
            continue
        try:
            o, e = a.get_actor_bounds(False)
        except Exception:  # noqa: BLE001
            continue
        if max(e.x, e.y) > 2000000:  # ignora coisas gigantes (cúpulas antigas etc.)
            continue
        for i, k in enumerate("xyz"):
            lo[i] = min(lo[i], getattr(o, k) - getattr(e, k))
            hi[i] = max(hi[i], getattr(o, k) + getattr(e, k))
        n += 1
    if n == 0:
        return (0.0, 0.0, 0.0)
    return ((lo[0] + hi[0]) * 0.5, (lo[1] + hi[1]) * 0.5, lo[2])


def prep_sky_actor(a, label, sort_priority=None, mi=None):
    """Flags de um ator do céu: sem colisão, sem sombra, sem navmesh, nunca some por distância."""
    import unreal
    a.set_actor_label(label)
    a.set_folder_path(FOLDER)
    setp(a, "tags", [unreal.Name(TAG)], label)
    setp(a, "is_spatially_loaded", False, label)  # World Partition: nunca descarregar (fica a 50+ km)
    c = a.static_mesh_component
    if mi is not None:
        c.set_material(0, mi)
    try:
        c.set_collision_profile_name("NoCollision")
    except Exception as exc:  # noqa: BLE001
        warn(f"{label} colisão: {exc}")
    for k, v in (("cast_shadow", False), ("affect_distance_field_lighting", False),
                 ("affect_dynamic_indirect_lighting", False), ("can_ever_affect_navigation", False),
                 ("receives_decals", False), ("never_distance_cull", True), ("visible_in_ray_tracing", False)):
        setp(c, k, v, label)
    if sort_priority is not None:
        setp(c, "translucency_sort_priority", int(sort_priority), label)


def spawn_mesh(ss, sm, loc, prot, scale, label, sort_priority=None, mi=None):
    import unreal
    a = ss.spawn_actor_from_object(sm, vec(loc), rot(prot))
    if a is None:
        raise RuntimeError(f"não criou {label}")
    a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    prep_sky_actor(a, label, sort_priority, mi)
    return a


def spawn_cls(ss, cls, loc, label):
    import unreal
    a = ss.spawn_actor_from_class(cls, vec(loc), unreal.Rotator(0, 0, 0))
    a.set_actor_label(label)
    a.set_folder_path(FOLDER)
    setp(a, "tags", [unreal.Name(TAG)], label)
    return a


def tune_sun(actors, ss, P, center, info):
    import unreal
    suns = [a for a in actors if isinstance(a, unreal.DirectionalLight)]
    main = None
    for a in suns:
        c = comp_of(a, unreal.DirectionalLightComponent)
        try:
            if c and c.get_editor_property("atmosphere_sun_light"):
                main = a
                break
        except Exception:  # noqa: BLE001
            pass
    if main is None and suns:
        main = suns[0]
    if main is None:
        main = spawn_cls(ss, unreal.DirectionalLight, (center[0], center[1], center[2] + 50000), "Sol")
        info["sun"] = "criado"
    else:
        info["sun"] = main.get_actor_label()
    main.set_actor_rotation(rot(sun_rotator(P["sun_az"] + SKY_YAW, P["sun_el"])), False)
    c = comp_of(main, unreal.DirectionalLightComponent)
    try:
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
    except Exception as exc:  # noqa: BLE001
        warn(f"sol mobilidade: {exc}")
    for k, v in (("intensity", P["sun_lux"]), ("use_temperature", False),
                 ("light_color", color_u8(P["sun_color"])),
                 ("atmosphere_sun_light", True), ("atmosphere_sun_light_index", 0),
                 ("light_source_angle", P["sun_angle"]), ("atmosphere_sun_disk_color_scale", lc(P["sun_disk"]))):
        setp(c, k, v, "Sol")
    # outros sóis com "atmosphere sun light" brigariam pelo índice 0
    for a in suns:
        if a != main:
            oc = comp_of(a, unreal.DirectionalLightComponent)
            if oc is not None:
                setp(oc, "atmosphere_sun_light", False, a.get_actor_label())
                warn(f"luz direcional extra '{a.get_actor_label()}' deixou de ser sol da atmosfera")


def tune_atmosphere(actors, ss, P, info):
    import unreal
    sa = [a for a in actors if isinstance(a, unreal.SkyAtmosphere)]
    if not sa:
        sa = [spawn_cls(ss, unreal.SkyAtmosphere, (0, 0, 0), "Ceu")]
        info["sky_atmosphere"] = "criado"
    A = ATMOSPHERE
    for a in sa:
        c = comp_of(a, unreal.SkyAtmosphereComponent)
        if c is None:
            warn(f"{a.get_actor_label()}: sem SkyAtmosphereComponent")
            continue
        for k, v in (("rayleigh_scattering", lc(A["rayleigh"])), ("rayleigh_scattering_scale", A["rayleigh_scale"]),
                     ("rayleigh_exponential_distribution", A["rayleigh_km"]),
                     ("mie_scattering", lc(A["mie"])), ("mie_scattering_scale", A["mie_scale"]),
                     ("mie_absorption", lc(A["mie_abs"])), ("mie_absorption_scale", A["mie_abs_scale"]),
                     ("mie_anisotropy", A["mie_g"]), ("mie_exponential_distribution", A["mie_km"]),
                     ("other_absorption", lc(A["ozone"])), ("other_absorption_scale", A["ozone_scale"]),
                     ("multi_scattering_factor", P.get("multi_scattering", A["multi_scattering"])),
                     ("ground_albedo", color_u8(A["ground_albedo"])),
                     ("sky_luminance_factor", lc(P["sky_luminance"]))):
            setp(c, k, v, "SkyAtmosphere")
    if len(sa) > 1:
        warn(f"{len(sa)} SkyAtmosphere no mapa (devia ser 1); todos ajustados")


def tune_skylight(actors, ss, P, center, info):
    import unreal
    sl = [a for a in actors if isinstance(a, unreal.SkyLight)]
    if not sl:
        sl = [spawn_cls(ss, unreal.SkyLight, (center[0], center[1], center[2] + 2000), "LuzDoCeu")]
        info["skylight"] = "criado"
    for a in sl:
        c = comp_of(a, unreal.SkyLightComponent)
        if c is None:
            continue
        try:
            c.set_mobility(unreal.ComponentMobility.MOVABLE)
        except Exception as exc:  # noqa: BLE001
            warn(f"skylight mobilidade: {exc}")
        for k, v in (("real_time_capture", bool(SKYLIGHT_REAL_TIME)), ("intensity", P["skylight"]),
                     ("lower_hemisphere_is_black", False), ("lower_hemisphere_color", lc(P["lower_hemi"]))):
            setp(c, k, v, "SkyLight")
        try:
            c.recapture_sky()
        except Exception:  # noqa: BLE001
            pass


def enum_member(enum_names, hint):
    """Membro de enum do Python da Unreal pelo pedaço do nome (ex.: AutoExposureMethod / MANUAL)."""
    import unreal
    for en in enum_names:
        e = getattr(unreal, en, None)
        if e is None:
            continue
        for m in dir(e):
            if hint in m.upper():
                return getattr(e, m)
    return None


def tune_exposure(actors, ss, preset_name, center, info):
    """Um PostProcessVolume infinito (tag AlienSkyGen) com exposição fixa; reaproveitado ao rodar de novo."""
    import unreal
    ppvs = [a for a in actors if isinstance(a, unreal.PostProcessVolume)]
    ours = [a for a in ppvs if TAG in [str(t) for t in a.tags]]
    others = []
    for a in ppvs:
        if a in ours:
            continue
        try:
            others.append({"label": a.get_actor_label(), "unbound": bool(a.get_editor_property("unbound")),
                           "priority": float(a.get_editor_property("priority"))})
        except Exception:  # noqa: BLE001
            others.append({"label": a.get_actor_label()})
    if others:
        warn(f"outros PostProcessVolume no mapa (o de exposição tem prioridade {PPV_PRIORITY}): {others}")
    for extra in ours[1:]:
        ss.destroy_actor(extra)
    if ours:
        vol = ours[0]
        info["exposure_volume"] = "reaproveitado"
    else:
        vol = spawn_cls(ss, unreal.PostProcessVolume, center, PPV_LABEL)
        info["exposure_volume"] = "criado"
    vol.set_actor_label(PPV_LABEL)
    for k, v in (("unbound", True), ("priority", PPV_PRIORITY), ("blend_weight", 1.0), ("enabled", True)):
        setp(vol, k, v, PPV_LABEL)
    st = vol.get_editor_property("settings")
    applied = {}
    for k, v in exposure_settings(preset_name).items():
        if k == "auto_exposure_method":
            v = enum_member(("AutoExposureMethod", "EAutoExposureMethod"), v)
            if v is None:
                warn("enum AutoExposureMethod.MANUAL não encontrado: fica Histogram com mínimo = máximo (também fixo)")
                continue
        if setp(st, k, v, PPV_LABEL):
            applied[k] = str(v)
    vol.set_editor_property("settings", st)
    info["exposure"] = applied
    info["other_post_process_volumes"] = others


def tune_fog(actors, ss, P, center, info):
    import unreal
    fogs = [a for a in actors if isinstance(a, unreal.ExponentialHeightFog)]
    if not fogs:
        fogs = [spawn_cls(ss, unreal.ExponentialHeightFog, center, "Neblina")]
        info["fog"] = "criado"
    for a in fogs:
        c = comp_of(a, unreal.ExponentialHeightFogComponent)
        if c is None:
            continue
        for k, v in (("fog_density", P["fog_density"]), ("fog_height_falloff", P["fog_falloff"]),
                     ("start_distance", P["fog_start"]), ("fog_max_opacity", 1.0),
                     ("fog_inscattering_luminance", lc(P["fog_color"])),
                     ("directional_inscattering_luminance", lc(P["fog_dir"])),
                     ("directional_inscattering_exponent", P["fog_dir_exp"]),
                     ("fog_cutoff_distance", float(FOG_CUTOFF_CM)),
                     ("enable_volumetric_fog", bool(VOLUMETRIC_FOG))):
            setp(c, k, v, "Neblina")
        if VOLUMETRIC_FOG:
            for k, v in (("volumetric_fog_scattering_distribution", 0.6),
                         ("volumetric_fog_albedo", color_u8((200, 170, 255))),
                         ("volumetric_fog_extinction_scale", 0.6), ("volumetric_fog_distance", 6000.0)):
                setp(c, k, v, "Neblina")


def apply_to_current_level(preset_name=DEFAULT_PRESET, save=False):
    """Aplica o céu no mapa aberto. build_l01.py pode chamar isto (import setup_alien_sky)."""
    import unreal
    ss = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    A = ensure_assets(preset_name)
    P = PRESETS[preset_name]
    info = {}
    actors = ss.get_all_level_actors()

    old = [a for a in actors if TAG in [str(t) for t in a.tags]
           and not isinstance(a, (unreal.DirectionalLight, unreal.SkyAtmosphere, unreal.SkyLight, unreal.ExponentialHeightFog,
                                  unreal.PostProcessVolume))]
    clouds = [a for a in actors if isinstance(a, unreal.VolumetricCloud)]
    for a in old + clouds:
        ss.destroy_actor(a)
    info["removed_sky_actors"] = len(old)
    info["removed_clouds"] = len(clouds)
    for a in actors:
        cname = a.get_class().get_name()
        if "SkySphere" in cname or "Sky_Sphere" in cname:
            warn(f"ator antigo de céu '{a.get_actor_label()}' ({cname}) continua no mapa: apague à mão se cobrir o céu")
    actors = ss.get_all_level_actors()

    center = map_center(actors)
    info["center_cm"] = [round(v) for v in center]
    tune_sun(actors, ss, P, center, info)
    tune_atmosphere(actors, ss, P, info)
    tune_skylight(actors, ss, P, center, info)
    tune_fog(actors, ss, P, center, info)
    tune_exposure(actors, ss, preset_name, center, info)

    meshes, mis = A["meshes"], A["mis"]
    placed = {}
    for body in BODIES:
        loc, prot, scale = body_transform(body, center)
        spawn_mesh(ss, meshes[body["mesh"]], loc, prot, scale, body["label"], mi=mis[body["mi"]])
        placed[body["key"]] = {"loc_km": [round(v / 100000.0, 2) for v in loc], "scale": round(scale, 1)}
        if body["key"] == "planet":
            spawn_mesh(ss, meshes["SM_Sky_Rings"], loc, prot, scale, "Ceu_Aneis", SORT_PRIORITY["rings"], mis["MI_Sky_Rings"])
    dome_scale = STAR_DOME["radius_km"] * 100000.0 / MESH_RADIUS_CM
    spawn_mesh(ss, meshes["SM_Sky_StarDome"], center, (0, 0, 0), dome_scale, STAR_DOME["label"],
               SORT_PRIORITY["stars"], mis["MI_Sky_Stars"])
    au_scale = AURORA["radius_km"] * 100000.0 / MESH_RADIUS_CM
    spawn_mesh(ss, meshes["SM_Sky_Aurora"], center, (0, AURORA["az"] + SKY_YAW, 0), au_scale, AURORA["label"],
               SORT_PRIORITY["aurora"], mis["MI_Sky_Aurora"])
    info["placed"] = placed
    # Sem captura em tempo real: recaptura agora, já com planeta/luas/aurora no lugar.
    for a in ss.get_all_level_actors():
        if isinstance(a, unreal.SkyLight):
            c = comp_of(a, unreal.SkyLightComponent)
            try:
                if c is not None:
                    c.recapture_sky()
            except Exception as exc:  # noqa: BLE001
                warn(f"recapture_sky: {exc}")
    log(f"céu alienígena aplicado ({preset_name}): {len(old)} ator(es) antigo(s) do céu e {len(clouds)} nuvem(ns) removidos")
    if save:
        if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level():
            warn("save_current_level retornou False")
    return info


def main(argv=None):
    import unreal
    preset = parse_preset(argv if argv is not None else sys.argv[1:])
    R["preset"] = preset
    log(f"preset: {preset}")
    eal = unreal.EditorAssetLibrary
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    current = package_from_world_path(world.get_path_name() if world else "")
    ensure_assets(preset)
    if current is None:
        warn("o mapa aberto nunca foi salvo: recebe o céu, mas salve-o você (Ctrl+S)")
        try:
            R["maps"]["(aberto, sem salvar)"] = apply_to_current_level(preset, save=False)
        except Exception as exc:  # noqa: BLE001
            err("mapa aberto", exc)
    for m in EXTRA_MAPS:
        if not eal.does_asset_exist(m):
            warn(f"mapa não existe (pulado): {m}")
    maps = maps_to_process(current, EXTRA_MAPS, eal.does_asset_exist)
    loaded = current
    for m in maps:
        try:
            if m != loaded and not les.load_level(m):
                raise RuntimeError(f"não abriu {m}")
            loaded = m
            R["maps"][m] = apply_to_current_level(preset, save=True)
        except Exception as exc:  # noqa: BLE001
            err(m, exc)
    if current and loaded != current:
        les.load_level(current)
        log(f"mapa original reaberto: {current}")


def run():
    import unreal
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        err("main", exc)
    finally:
        os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
        with open(os.path.join(REPO, "reports", "setup_alien_sky.json"), "w", encoding="utf-8") as fh:
            json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
        unreal.log(f"[alien_sky] fim | mapas: {len(R['maps'])} | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")


# Roda sozinho só quando executado como script no editor (py "...setup_alien_sky.py").
# "import setup_alien_sky" (build_l01.py, make_sky.py, pytest) só carrega as funções.
if __name__ != "setup_alien_sky":
    try:
        import unreal as _unreal_check  # noqa: F401
    except ImportError:
        _unreal_check = None
    if _unreal_check is not None and hasattr(_unreal_check, "EditorAssetLibrary"):
        run()
