import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="/home/claude/rig5/rig_fix.blend")
a = bpy.data.objects["Armature"]
mw = a.matrix_world; mi = mw.inverted()
# alvo: Y no mundo (m); frente = -Y. Coluna reta como a do Enzo.
T = {"spine_01": -0.040, "spine_02": -0.036, "spine_03": -0.031, "spine_04": -0.027, "spine_05": -0.020,
     "neck_01": -0.014, "neck_02": -0.024, "head": -0.034}
bpy.context.view_layer.objects.active = a; a.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
eb = a.data.edit_bones
for n, ty in T.items():
    b = eb[n]
    b.use_connect = False
    hw = mw @ b.head
    d = mi.to_3x3() @ Vector((0, ty - hw.y, 0))
    b.head += d; b.tail += d
    for c in b.children:
        c.use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')
for n in T:
    print(n, [round(x, 3) for x in (mw @ a.data.bones[n].head_local)])
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/rig5/rig_fix2.blend"); print("OK")
