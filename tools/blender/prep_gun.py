"""Prepara a arma do usuário (GLB) para a Unreal: escala real, origem na empunhadura, cano em +X, cima em +Z."""
import bpy, sys, os
import numpy as np
from mathutils import Vector, Matrix
src, out, length = sys.argv[-3], sys.argv[-2], float(sys.argv[-1])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
o = [x for x in bpy.data.objects if x.type == 'MESH'][0]
bpy.context.view_layer.objects.active = o
for x in bpy.data.objects:
    x.select_set(x == o)
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
co = np.array([v.co[:] for v in o.data.vertices])
mn, mx = co.min(0), co.max(0)
s = length / (mx[0] - mn[0])
# empunhadura: parte de baixo e de trás da arma
low = co[(co[:, 2] < mn[2] + 0.45 * (mx[2] - mn[2])) & (co[:, 0] < mn[0] + 0.45 * (mx[0] - mn[0]))]
grip = np.array([low[:, 0].mean(), low[:, 1].mean(), mn[2] + 0.62 * (low[:, 2].max() - mn[2])])
print("grip (orig)", grip.round(3), "escala", round(s, 3))
o.data.transform(Matrix.Translation(Vector(-grip)))
o.data.transform(Matrix.Scale(s, 4))
o.name = "SM_AlienPistol"; o.data.name = "SM_AlienPistol"
# reduz polígonos e textura
dec = o.modifiers.new("dec", "DECIMATE"); dec.ratio = 0.5
bpy.ops.object.modifier_apply(modifier="dec")
for img in bpy.data.images:
    if img.size[0] > 1024:
        img.scale(1024, 1024)
    img.filepath_raw = os.path.join(os.path.dirname(out), "T_AlienPistol_BaseColor.png")
    img.file_format = "PNG"
    img.save()
for m in o.data.materials:
    m.name = "M_AlienPistol"
tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
co = np.array([v.co[:] for v in o.data.vertices])
print("tris", tris, "bbox", co.min(0).round(3), co.max(0).round(3))
bpy.ops.export_scene.fbx(filepath=out, use_selection=True, object_types={'MESH'}, apply_unit_scale=True,
                         mesh_smooth_type='FACE', path_mode='COPY', embed_textures=True)
print("OK")
