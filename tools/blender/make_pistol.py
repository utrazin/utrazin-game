"""Pistola alienígena cartoon (low poly). Origem = centro da empunhadura; cano em +X; cima em +Z."""
import bpy, bmesh, sys, math
out = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)

def mat(name, rgb, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*rgb, 1)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = 0.45
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m

M_body = mat("M_Pistol_Body", (0.12, 0.13, 0.16))
M_trim = mat("M_Pistol_Trim", (0.55, 0.58, 0.62))
M_glow = mat("M_Pistol_Glow", (0.1, 0.95, 0.55), emit=3.0)
parts = []

def box(name, loc, size, m, bevel=0.004):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        mod = o.modifiers.new("b", "BEVEL"); mod.width = bevel; mod.segments = 2
    o.data.materials.append(m); parts.append(o); return o

def cyl(name, loc, r, depth, m, rot=(0, math.pi / 2, 0), verts=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.data.materials.append(m); parts.append(o); return o

# corpo/ferrolho (em cima da empunhadura, avança para +X)
box("slide", (0.045, 0, 0.065), (0.16, 0.032, 0.036), M_body)
box("frame", (0.035, 0, 0.038), (0.12, 0.028, 0.022), M_trim)
# cano com anéis e ponta brilhante
cyl("barrel", (0.14, 0, 0.068), 0.011, 0.05, M_trim)
cyl("ring1", (0.125, 0, 0.068), 0.016, 0.008, M_glow)
cyl("muzzle", (0.168, 0, 0.068), 0.008, 0.008, M_glow)
# faixa brilhante lateral
box("strip_l", (0.05, 0.0165, 0.066), (0.10, 0.002, 0.008), M_glow, bevel=0)
box("strip_r", (0.05, -0.0165, 0.066), (0.10, 0.002, 0.008), M_glow, bevel=0)
# empunhadura inclinada (origem no centro dela)
g = box("grip", (0, 0, 0), (0.032, 0.03, 0.095), M_body)
g.rotation_euler = (0, math.radians(15), 0)
# guarda-mato e gatilho
box("guard", (0.035, 0, 0.012), (0.045, 0.008, 0.006), M_trim, bevel=0.002)
box("trigger", (0.025, 0, 0.022), (0.006, 0.006, 0.02), M_trim, bevel=0.001)

for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.convert(target="MESH")
bpy.ops.object.join()
p = bpy.context.object
p.name = "SM_AlienPistol"
bpy.ops.object.shade_flat()
print("tris", sum(len(f.vertices) - 2 for f in p.data.polygons), "dims", tuple(round(d, 3) for d in p.dimensions))
bpy.ops.export_scene.fbx(filepath=out, use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
                         mesh_smooth_type="FACE", axis_forward="X", axis_up="Z")
# preview
bpy.ops.object.camera_add(location=(0.05, -0.45, 0.12), rotation=(math.radians(82), 0, 0))
bpy.context.scene.camera = bpy.context.object
bpy.ops.object.light_add(type="SUN", rotation=(0.6, 0.2, 0.3))
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.color_type = "MATERIAL"
sc.render.resolution_x, sc.render.resolution_y = 640, 400
sc.render.filepath = out.replace(".fbx", ".png")
bpy.ops.render.render(write_still=True)
print("OK")
