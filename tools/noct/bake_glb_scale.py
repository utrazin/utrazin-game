"""Assa a escala do no raiz de um GLB do Noct Asset Forge 3D nos vertices e ossos.

Por que: o Forge 3D exporta em "unidades do modelo" (16 = 1 m) e coloca
scale=0.0625 no no raiz. Na Unreal isso vira o mesmo problema dos zumbis
(osso raiz com escala diferente de 1 => animacao retargetada quebra).
Este script deixa tudo em metros com escala 1 em todos os nos.

Uso (Blender 4.x/5.x, sem abrir a interface):
  blender -b --python tools/noct/bake_glb_scale.py -- entrada.glb saida.glb
ou, com o modulo bpy do pip:
  python tools/noct/bake_glb_scale.py -- entrada.glb saida.glb
Prop estatico (junta as pecas numa malha so, vira 1 StaticMesh na Unreal):
  blender -b --python tools/noct/bake_glb_scale.py -- entrada.glb SM_Nome.glb --juntar
"""
import sys
import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
juntar = "--juntar" in argv          # prop estatico: junta todas as pecas numa malha so
argv = [a for a in argv if not a.startswith("--")]
src, dst = argv[0], argv[1]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
scene = bpy.context.scene

# Escala de cada armadura no mundo antes de aplicar (para corrigir chaves de posicao dos ossos).
arm_scale = {o.name: o.matrix_world.to_scale()[0] for o in scene.objects if o.type == "ARMATURE"}

# Desfaz a hierarquia mantendo a transformacao e aplica tudo.
bpy.ops.object.select_all(action="DESELECT")
for o in scene.objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = next(iter(scene.objects))
for o in list(scene.objects):
    if o.parent and o.parent.type == "EMPTY":
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
for o in [o for o in scene.objects if o.type == "EMPTY" and not o.children]:
    bpy.data.objects.remove(o)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Chaves de posicao dos ossos estavam em unidades do modelo: reescala.
for name, s in arm_scale.items():
    if abs(s - 1.0) < 1e-6:
        continue
    for act in bpy.data.actions:
        fcurves = []
        if hasattr(act, "fcurves"):
            fcurves = list(act.fcurves)
        else:  # Blender 5: canais em layers/strips
            for layer in act.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        fcurves += list(bag.fcurves)
        for fc in fcurves:
            if fc.data_path.endswith(".location"):
                for kp in fc.keyframe_points:
                    kp.co.y *= s
                    kp.handle_left.y *= s
                    kp.handle_right.y *= s

if juntar and not arm_scale:
    meshes = [o for o in scene.objects if o.type == "MESH"]
    if len(meshes) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in meshes:
            o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
    import os
    scene.objects[0].name = os.path.splitext(os.path.basename(dst))[0]

bad = [(o.name, tuple(round(v, 4) for v in o.scale)) for o in scene.objects if any(abs(v - 1) > 1e-4 for v in o.scale)]
if bad:
    raise SystemExit(f"[bake] ERRO: ainda ha escala diferente de 1: {bad}")
bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", export_animations=True,
                          export_apply=False, export_yup=True)
print(f"[bake] OK {dst} (armaduras corrigidas: {arm_scale})")
