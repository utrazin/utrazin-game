import bpy, sys, json
blend, cfgp, out = sys.argv[-3], sys.argv[-2], sys.argv[-1]
C=json.load(open(cfgp)); bpy.ops.wm.open_mainfile(filepath=blend)
A=bpy.data.objects["Arm_"+C["nome"]]; A.name="SK_NPC_"+C["nome"]
m=[o for o in bpy.data.objects if o.type=='MESH'][0]; m.name="NPC_"+C["nome"]+"_Mesh"
for o in list(bpy.data.objects):
    if o.type not in ('MESH','ARMATURE'): bpy.data.objects.remove(o, do_unlink=True)
A.animation_data_create(); A.animation_data.action=None
pref=C["nome"]+"_"
for a in list(bpy.data.actions):
    if a.name.startswith(pref): a.name=a.name[len(pref):]; a.use_fake_user=True
    else: bpy.data.actions.remove(a)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_image_format='JPEG', export_jpeg_quality=92,
    export_animation_mode='ACTIONS', export_optimize_animation_size=False, export_skins=True)
