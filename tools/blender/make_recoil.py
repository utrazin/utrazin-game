"""Gera A_Fire_Recoil.fbx: tiro curto (recuo) a partir da pose de 'pistol idle' do Mixamo."""
import bpy, sys, math
from mathutils import Matrix, Vector
src, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
sc = bpy.context.scene
sc.render.fps = 30
sc.frame_set(1)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
pbs = arm.pose.bones
# pose base (frame 1) em espaço da armadura
base = {pb.name: pb.matrix.copy() for pb in pbs}
old = arm.animation_data.action
arm.animation_data.action = None
for pb in pbs:
    pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
M = arm.matrix_world
Mi = M.inverted()
AX = Vector((1, 0, 0))  # eixo lateral (personagem olha para -Y)

def set_pose(kick):
    """kick 0..1. Aplica rotações em ordem pai->filho, em espaço de mundo."""
    world = {n: M @ m for n, m in base.items()}
    rots = [("mixamorig:Spine1", -2.0), ("mixamorig:Spine2", -3.5),
            ("mixamorig:RightArm", -4.0), ("mixamorig:LeftArm", -4.0),
            ("mixamorig:RightHand", -14.0), ("mixamorig:LeftHand", -10.0)]
    for pb in pbs:  # ordem hierárquica
        pb.matrix = base[pb.name]
        bpy.context.view_layer.update()
    for name, deg in rots:
        pb = pbs[name]
        W = M @ pb.matrix
        p = W.to_translation()
        R = Matrix.Translation(p) @ Matrix.Rotation(math.radians(deg * kick), 4, AX) @ Matrix.Translation(-p)
        pb.matrix = Mi @ R @ W
        bpy.context.view_layer.update()
    # leve empurrão para trás dos braços (translação do ombro não; só rotação)

act = bpy.data.actions.new("Fire_Recoil")
arm.animation_data.action = act
curve = {1: 0.0, 2: 1.0, 3: 0.85, 5: 0.45, 7: 0.15, 9: 0.0}
for f, k in curve.items():
    sc.frame_set(f)
    set_pose(k)
    for pb in pbs:
        pb.keyframe_insert("location", frame=f)
        pb.keyframe_insert("rotation_quaternion", frame=f)
sc.frame_start, sc.frame_end = 1, 9
bpy.ops.object.mode_set(mode='OBJECT')
for o in list(bpy.data.objects):
    if o.type != 'ARMATURE':
        bpy.data.objects.remove(o)
bpy.ops.export_scene.fbx(filepath=out, use_selection=False, object_types={'ARMATURE'}, add_leaf_bones=False,
                         bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                         bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0)
print("OK", out)
