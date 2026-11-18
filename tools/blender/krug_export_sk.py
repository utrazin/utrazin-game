import bpy, sys
blend, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
K=bpy.data.objects["Krug_Armature"]; K.name="SK_NPC_Krug"
mesh=[o for o in bpy.data.objects if o.type=='MESH'][0]; mesh.name="NPC_Krug_Mesh"
for o in list(bpy.data.objects):
    if o.type not in ('MESH','ARMATURE'): bpy.data.objects.remove(o, do_unlink=True)
# cada action vira uma faixa NLA para exportar todas
K.animation_data_create(); K.animation_data.action=None
for a in list(bpy.data.actions):
    if a.name.startswith("Krug_"): a.name=a.name[5:]; a.use_fake_user=True
    else: bpy.data.actions.remove(a)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_image_format='JPEG', export_jpeg_quality=92,
    export_animation_mode='ACTIONS', export_optimize_animation_size=False, export_skins=True, export_def_bones=False, export_anim_single_armature=True)
