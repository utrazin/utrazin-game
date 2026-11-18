"""Conferência do encaixe das armas na mão dos heróis (Blender 5.2, sem interface).

Uso (bpy em Python ou blender -b --python):
  python -I tools/blender/grip_check.py tools/blender/grip_check_Hero01.json
Variáveis opcionais: GRIP_REPO (raiz do repositório), GRIP_OUT (pasta das imagens).

Como funciona:
 - importa o rig do herói (FBX), a animação Mixamo (esqueleto do X Bot) e copia a pose para o herói
   (rotação no mundo osso a osso, alinhando a direção dos ossos na pose de descanso: T do X Bot -> A do herói);
 - coloca a arma no osso hand_r com o transform RELATIVO da Unreal (cm + rotator). Unreal = FBX espelhado em Y,
   então: loc (x, -y, z) e rotação conjugada pelo espelho (conferido: o cano bate com o "fwd" do setup_mixamo);
 - "proposta": cabo da arma no centro do punho, cano na frente do personagem (mesma conta do
   tools/unreal/fix_weapon_grips.py);
 - renderiza (Workbench) frente/lado; linha vermelha = eixo +X da arma (cano/lâmina), verde = frente do herói.
"""
import bpy, json, math, os, sys
from mathutils import Matrix, Vector, Quaternion
U = os.environ.get("GRIP_REPO", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))) + "/"
OUT = os.environ.get("GRIP_OUT", U + "assets/work/weapons/_grip_check_out") + "/"
os.makedirs(OUT, exist_ok=True)
cfg = json.load(open(sys.argv[-1]))
sc = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.color_type = "MATERIAL"
sc.display.shading.light = "STUDIO"
if cfg.get("xray"):
    sc.display.shading.show_xray = True
    sc.display.shading.xray_alpha = 0.45
sc.render.resolution_x, sc.render.resolution_y = 520, 520
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"

MAP = {"Hips": ["pelvis"], "Spine": ["spine_01", "spine_02"], "Spine1": ["spine_03"], "Spine2": ["spine_04", "spine_05"],
       "Neck": ["neck_01", "neck_02"], "Head": ["head"]}
for s, h in (("Right", "r"), ("Left", "l")):
    MAP.update({f"{s}Shoulder": [f"clavicle_{h}"], f"{s}Arm": [f"upperarm_{h}"], f"{s}ForeArm": [f"lowerarm_{h}"],
                f"{s}Hand": [f"hand_{h}"], f"{s}UpLeg": [f"thigh_{h}"], f"{s}Leg": [f"calf_{h}"], f"{s}Foot": [f"foot_{h}"],
                f"{s}ToeBase": [f"ball_{h}"]})
    for fm, fh in (("Thumb", "thumb"), ("Index", "index"), ("Middle", "middle"), ("Ring", "ring"), ("Pinky", "pinky")):
        for k in (1, 2, 3):
            MAP[f"{s}Hand{fm}{k}"] = [f"{fh}_0{k}_{h}"]
# filho que define a direção do osso (para alinhar a pose de descanso)
CHILD_MIX = {"RightArm": "RightForeArm", "RightForeArm": "RightHand", "RightHand": "RightHandMiddle1",
             "LeftArm": "LeftForeArm", "LeftForeArm": "LeftHand", "LeftHand": "LeftHandMiddle1",
             "RightShoulder": "RightArm", "LeftShoulder": "LeftArm", "RightUpLeg": "RightLeg", "RightLeg": "RightFoot",
             "LeftUpLeg": "LeftLeg", "LeftLeg": "LeftFoot"}
for s in ("Right", "Left"):
    for fm in ("Thumb", "Index", "Middle", "Ring", "Pinky"):
        CHILD_MIX[f"{s}Hand{fm}1"] = f"{s}Hand{fm}2"; CHILD_MIX[f"{s}Hand{fm}2"] = f"{s}Hand{fm}3"
        CHILD_MIX[f"{s}Hand{fm}3"] = f"{s}Hand{fm}4"
CHILD_HERO = {"upperarm": "lowerarm", "lowerarm": "hand", "hand": "middle_01", "clavicle": "upperarm", "thigh": "calf", "calf": "foot"}
for fh in ("thumb", "index", "middle", "ring", "pinky"):
    CHILD_HERO[f"{fh}_01"] = f"{fh}_02"; CHILD_HERO[f"{fh}_02"] = f"{fh}_03"


def imp(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=U + path)
    new = [o for o in bpy.data.objects if o not in before]
    return [o for o in new if o.type == "ARMATURE"][0], new


def wrot(arm, pb, rest=False):
    m = pb.bone.matrix_local if rest else pb.matrix
    return (arm.matrix_world.to_3x3().normalized() @ m.to_3x3().normalized()).to_quaternion()


def whead(arm, pb, rest=False):
    return arm.matrix_world @ (pb.bone.head_local if rest else pb.head)


def hero_child(n):
    if n.count("_") < 1 or n.split("_")[-1] not in ("l", "r"):
        return None
    base, side = n.rsplit("_", 1)
    c = CHILD_HERO.get(base)
    return f"{c}_{side}" if c else None


hero, hero_objs = imp(cfg["hero_fbx"])
HB = hero.pose.bones


def retarget(mix):
    """Copia a pose do Mixamo para o herói (rotações no mundo, alinhando a direção dos ossos no descanso)."""
    MB = mix.pose.bones
    order = [pb for pb in HB]  # já em ordem de hierarquia
    inv = {}
    for m, hs in MAP.items():
        for h in hs:
            inv[h] = "mixamorig:" + m
    for pb in order:
        mname = inv.get(pb.name)
        if not mname or mname not in MB:
            continue
        mb = MB[mname]
        S = Quaternion()
        mc = CHILD_MIX.get(mname.replace("mixamorig:", ""))
        hc = hero_child(pb.name)
        if mc and hc and ("mixamorig:" + mc) in MB and hc in HB:
            dm = (whead(mix, MB["mixamorig:" + mc], True) - whead(mix, mb, True)).normalized()
            dh = (whead(hero, HB[hc], True) - whead(hero, pb, True)).normalized()
            S = dh.rotation_difference(dm)
        Rm_rest = wrot(mix, mb, True); Rm = wrot(mix, mb)
        Rh_rest = wrot(hero, pb, True)
        Rh = Rm @ Rm_rest.inverted() @ S @ Rh_rest
        # para matriz no espaço da armadura
        A = hero.matrix_world.to_3x3().normalized().to_quaternion()
        local = (A.inverted() @ Rh).to_matrix().to_4x4()
        cur = pb.matrix.copy()
        local.translation = cur.translation
        pb.matrix = local
        bpy.context.view_layer.update()


def ue_rot_matrix(p, y, r):
    """FRotator (graus) -> matriz 3x3 (colunas = eixos X,Y,Z) no espaço da Unreal."""
    P, Y, R = map(math.radians, (p, y, r))
    CP, SP, CY, SY, CR, SR = math.cos(P), math.sin(P), math.cos(Y), math.sin(Y), math.cos(R), math.sin(R)
    X = Vector((CP * CY, CP * SY, SP))
    Yv = Vector((SR * SP * CY - CR * SY, SR * SP * SY + CR * CY, -SR * CP))
    Z = Vector((-(CR * SP * CY + SR * SY), CY * SR - CR * SP * SY, CR * CP))
    return Matrix((X, Yv, Z)).transposed()


MIR = Matrix.Diagonal((1, -1, 1))


def ue_to_local(loc, rot):
    """Transform relativo da Unreal (cm, rotator) -> matriz 4x4 no quadro do osso no Blender (m)."""
    R = MIR @ ue_rot_matrix(*rot) @ MIR
    M = R.to_4x4()
    M.translation = Vector((loc[0], -loc[1], loc[2])) * 0.01
    return M


def local_to_ue(M):
    R = MIR @ M.to_3x3() @ MIR
    X, Y, Z = R.col[0], R.col[1], R.col[2]
    pitch = math.degrees(math.asin(max(-1, min(1, X.z))))
    yaw = math.degrees(math.atan2(X.y, X.x))
    roll = math.degrees(math.atan2(-Y.z, Z.z))
    t = M.translation * 100
    return [round(t.x, 3), round(-t.y, 3), round(t.z, 3)], [round(pitch, 3), round(yaw, 3), round(roll, 3)]


def hand_world(name="hand_r"):
    pb = HB[name]
    M = hero.matrix_world @ pb.matrix
    loc, rot, _ = M.decompose()
    W = rot.to_matrix().to_4x4(); W.translation = loc
    return W


weapons = {}
for key, path in cfg["weapons"].items():
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=U + path)
    o = [x for x in bpy.data.objects if x not in before][0]
    o.rotation_mode = "QUATERNION"
    weapons[key] = o
    o.hide_render = True
    # linha de mira (+X da arma)
    ln = bpy.data.objects.new(key + "_aim", None)
    ln.empty_display_type = "SINGLE_ARROW"
    sc.collection.objects.link(ln)
mat_line = bpy.data.materials.new("lin"); mat_line.diffuse_color = (1, 0.1, 0.1, 1)
bpy.ops.mesh.primitive_cylinder_add(radius=0.004, depth=1.5)
aim = bpy.context.active_object; aim.data.materials.append(mat_line)
for v in aim.data.vertices:
    v.co = Vector((v.co.z + 0.75, v.co.x, v.co.y))  # cilindro ao longo de +X, começando na origem
aim.rotation_mode = "QUATERNION"
mat_fwd = bpy.data.materials.new("fwd"); mat_fwd.diffuse_color = (0.1, 0.9, 0.1, 1)
bpy.ops.mesh.primitive_cylinder_add(radius=0.004, depth=1.5)
fwdl = bpy.context.active_object; fwdl.data.materials.append(mat_fwd)
for v in fwdl.data.vertices:
    v.co = Vector((v.co.x, -(v.co.z + 0.75), v.co.y))  # frente do personagem (-Y)

results = {}
PROPOSED = {}
def _ball(name, col):
    m = bpy.data.materials.new(name); m.diffuse_color = col
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.008)
    o = bpy.context.active_object; o.data.materials.append(m); o.name = name
    return o
BALL_FIST = _ball("fist", (1, 1, 0, 1)); BALL_HC = _ball("hc", (0, 0.4, 1, 1))
if not cfg.get("balls"):
    BALL_FIST.hide_render = True; BALL_HC.hide_render = True


def P(n):
    return hero.matrix_world @ HB[n].head


def handle_center(key):
    """Centro do cabo na malha da arma (espaço local, m)."""
    if key == "Graveto":
        return Vector((cfg.get("stick_handle_x", 0.165), 0, 0))
    if key == "Graveto0":
        return Vector()
    o = weapons[key]
    vs = [v.co for v in o.data.vertices if v.co.z < -0.02 and v.co.x < 0.06]
    c = sum(vs, Vector()) / len(vs)
    return Vector((c.x, 0, c.z))


def fist_center():
    h = P("hand_r")
    kn = sum((P(f"{f}_01_r") for f in ("index", "middle", "ring", "pinky")), Vector()) / 4
    pts = [h + (kn - h) * 0.55, P("middle_02_r"), P("middle_03_r"), P("thumb_02_r")]
    return sum(pts, Vector()) / len(pts), h, kn


def propose_gun(key):
    fist, h, kn = fist_center()
    fwd = Vector((0, -1, 0))                       # frente do personagem
    up = Vector((0, 0, 1))
    hc = handle_center(key)
    # o cabo é inclinado: alinhamos o cabo da arma ao punho, mantendo o cano na linha de mira
    R = Matrix((fwd, up.cross(fwd), up)).transposed()   # X=frente, Y=esquerda, Z=cima (destro)
    R = Matrix((fwd, (up.cross(fwd)).normalized(), up)).transposed()
    origin = fist - R @ hc - up * cfg.get("gun_drop", 0.015)
    M = R.to_4x4(); M.translation = origin
    return hand_world().inverted() @ M


def propose_stick(key="Graveto", fwd_deg=None, roll_deg=0.0):
    import math as _m
    fist, h, kn = fist_center()
    la = P("lowerarm_r")
    f = (h - la).normalized()
    idx, pin = P("index_01_r"), P("pinky_01_r")
    ax = (idx - pin); ax = (ax - f * ax.dot(f)).normalized()
    a = _m.radians(cfg.get("blade_forward_deg", 20.0) if fwd_deg is None else fwd_deg)
    # roll: gira o eixo da lâmina em volta do antebraço (0 = sai do lado do indicador)
    if roll_deg:
        ax = (Quaternion(f, _m.radians(roll_deg)) @ ax).normalized()
    blade = (ax * _m.cos(a) + f * _m.sin(a)).normalized()
    edge = (kn - h); edge = (edge - blade * edge.dot(blade)).normalized()
    R = Matrix((blade, edge.cross(blade), edge)).transposed()
    origin = fist - R @ handle_center(key)
    M = R.to_4x4(); M.translation = origin
    return hand_world().inverted() @ M


def shoot(tag, center, size, views):
    cam.data.ortho_scale = size
    for vname, d in views:
        dv = Vector(d)
        cam.location = center + dv * 3
        up = Vector((0, 0, 1)) if abs(dv.z) < 0.9 else Vector((0, -1, 0))
        cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = OUT + f"{tag}_{vname}.png"
        bpy.ops.render.render(write_still=True)


VIEWS = [("frente", (0, -1, 0)), ("lado", (-1, 0, 0)), ("cima", (0, 0.001, 1)), ("baixo", (-0.5, -0.3, -1))]
for job in cfg["jobs"]:
    for pb in HB:
        pb.matrix_basis = Matrix()
    bpy.context.view_layer.update()
    if job["anim"] == "BRACO_ABAIXADO":
        # aproximação do MM_Idle (desarmado): braço caído ao lado do corpo, cotovelo um pouco dobrado
        for side, sx in (("r", -1), ("l", 1)):
            for bone, child, d in ((f"upperarm_{side}", f"lowerarm_{side}", Vector((0.10 * sx, 0.02, -1))),
                                   (f"lowerarm_{side}", f"hand_{side}", Vector((0.04 * sx, -0.30, -1)))):
                pb = HB[bone]
                cur = (P(child) - P(bone)).normalized()
                q = cur.rotation_difference(d.normalized())
                A = hero.matrix_world.to_3x3().normalized().to_quaternion()
                Rw = q @ wrot(hero, pb)
                m = (A.inverted() @ Rw).to_matrix().to_4x4(); m.translation = pb.matrix.translation
                pb.matrix = m
                bpy.context.view_layer.update()
    else:
        mix, mobjs = imp(job["anim"])
        act = mix.animation_data.action
        f0, f1 = act.frame_range
        frame = f0 + (f1 - f0) * job.get("frac", 0.0)
        sc.frame_set(int(round(frame)))
        retarget(mix)
        for o in mobjs:
            bpy.data.objects.remove(o)
    H = hand_world()
    for w in weapons.values():
        w.hide_render = True
    if job.get("score_ref"):
        SCORE_L = {}
        for fa in cfg["score_angles"]:
            for ra in cfg.get("score_rolls", [0]):
                SCORE_L[(fa, ra)] = propose_stick("Graveto", fa, ra)
        SCORES = {k: 0.0 for k in SCORE_L}
    if job.get("score"):
        segs = []
        def seg(a, b, r):
            segs.append((P(a), P(b), r))
        seg("pelvis", "spine_03", 0.14); seg("spine_03", "neck_01", 0.15); seg("neck_01", "head", 0.07)
        segs.append((P("head") + Vector((0, 0, 0.08)), P("head") + Vector((0, 0, 0.1)), 0.11))
        for sd in ("l", "r"):
            seg(f"thigh_{sd}", f"calf_{sd}", 0.08); seg(f"calf_{sd}", f"foot_{sd}", 0.06); seg(f"upperarm_{sd}", f"lowerarm_{sd}", 0.055)
        seg("lowerarm_l", "hand_l", 0.045)
        def dseg(p, a, b):
            ab = b - a; t = max(0, min(1, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
            return (p - (a + ab * t)).length
        Hn = hand_world()
        for k, L in SCORE_L.items():
            M = Hn @ L
            pen = 0.0
            for i in range(14):
                x = 0.25 + i * (0.79 - 0.25) / 13
                pt = M @ Vector((x, 0, 0))
                for a, b, r in segs:
                    d = dseg(pt, a, b)
                    if d < r:
                        pen += (r - d)
            SCORES[k] += pen
    for k in job.get("propose", []):
        L = propose_stick(k) if k.startswith("Graveto") else propose_gun(k)
        PROPOSED[k] = L
        loc, rot = local_to_ue(L)
        results[f"{cfg['hero']}_proposta_{k}"] = {"loc_cm": loc, "rot_pyr": rot, "pose": job["pose"]}
    for var in job["variants"]:
        w = weapons[var["weapon"]]
        if var.get("loc") == "proposta":
            L = PROPOSED[var.get("from", var["weapon"])]
        else:
            L = ue_to_local(var["loc"], var["rot"])
        M = H @ L
        if var.get("scale"):
            M = M @ Matrix.Scale(var["scale"], 4)
        w.matrix_world = M
        w.hide_render = False
        BALL_FIST.location = fist_center()[0]
        try:
            BALL_HC.location = M @ handle_center(var.get("from", var["weapon"]) if var["weapon"] != "Graveto" else "Graveto")
        except Exception:
            pass
        aim.matrix_world = H @ L
        bx = (H @ L).to_3x3() @ Vector((1, 0, 0))
        tag = f"{cfg['hero']}_{var['weapon']}_{job['pose']}_{var['name']}"
        hand = H.translation
        fwdl.location = hand
        results[tag] = {"barrel_dir_world_blender": [round(x, 3) for x in bx],
                        "angle_to_forward_deg": round(math.degrees(bx.angle(Vector((0, -1, 0)))), 1),
                        "barrel_pitch_deg": round(math.degrees(math.asin(max(-1, min(1, bx.z)))), 1)}
        if var.get("render", True):
            shoot(cfg.get("prefix", "_grip_check_") + tag, hand + bx * cfg.get("center_off", 0.12), cfg.get("size", job.get("size", 0.7)), VIEWS[: job.get("nviews", 2)])
        w.hide_render = True
    # pose inteira (uma vista)
if "SCORES" in dir():
    for k, v in sorted(SCORES.items(), key=lambda kv: kv[1]):
        print("SCORE", k, round(v, 3))
json.dump(results, open(OUT + f"res_{cfg['hero']}.json", "w"), indent=1)
print("RESULTS", json.dumps(results))
