import bpy, sys, os, glob, math, json
from mathutils import Matrix, Quaternion, Vector
blend, animdir, cfgp, outblend = sys.argv[-4], sys.argv[-3], sys.argv[-2], sys.argv[-1]
C=json.load(open(cfgp))
bpy.ops.wm.open_mainfile(filepath=blend)
sc=bpy.context.scene; sc.render.fps=30
K=bpy.data.objects["Arm_"+C["nome"]]
MAP=[n for n in K.pose.bones.keys() if n.startswith("mixamorig:")]
def depth(n):
    d=0; b=K.data.bones[n]
    while b.parent: d+=1; b=b.parent
    return d
MAP.sort(key=depth)
EXTRAS=[n for n in K.pose.bones.keys() if not n.startswith("mixamorig:")]
def rest_world(arm,name): return arm.matrix_world @ arm.data.bones[name].matrix_local
def bone_dir(arm,name):
    b=arm.data.bones[name]; return ((arm.matrix_world.to_3x3()) @ (b.tail_local-b.head_local)).normalized()
ABRE=math.radians(C.get("abre_graus",10))
OFF_L=Quaternion((0,1,0),-ABRE); OFF_R=Quaternion((0,1,0),ABRE)
for f in sorted(glob.glob(animdir+"/*.fbx")):
    nome=os.path.splitext(os.path.basename(f))[0]
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=f)
    S=[o for o in bpy.data.objects if o not in before and o.type=='ARMATURE'][0]
    sa=S.animation_data.action; f0,f1=[int(x) for x in sa.frame_range]
    corr={}
    for n in MAP:
        if n not in S.data.bones or n.endswith("HeadTop_End"): continue
        if any(k in n for k in ("Shoulder","Arm","Hand")):
            corr[n]=bone_dir(K,n).rotation_difference(bone_dir(S,n))
        else: corr[n]=Quaternion()
    act=bpy.data.actions.new(C["nome"]+"_"+nome); K.animation_data_create(); K.animation_data.action=act
    for pb in K.pose.bones: pb.rotation_mode='QUATERNION'
    Rs0={n:rest_world(S,n).to_quaternion() for n in corr}; Rt0={n:rest_world(K,n).to_quaternion() for n in corr}
    hs0=(S.matrix_world@S.data.bones["mixamorig:Hips"].head_local); hk0=(K.matrix_world@K.data.bones["mixamorig:Hips"].head_local)
    escala=hk0.z/max(hs0.z,1e-6)
    for fr in range(f0,f1+1):
        sc.frame_set(fr)
        for pb in K.pose.bones: pb.rotation_quaternion=(1,0,0,0); pb.location=(0,0,0)
        bpy.context.view_layer.update()
        for n in MAP:
            if n not in corr: continue
            Rs=(S.matrix_world @ S.pose.bones[n].matrix).to_quaternion()
            alvo=(Rs @ Rs0[n].inverted()) @ corr[n] @ Rt0[n]
            if ("LeftArm" in n or "LeftForeArm" in n or "LeftHand" in n): alvo=OFF_L @ alvo
            if ("RightArm" in n or "RightForeArm" in n or "RightHand" in n): alvo=OFF_R @ alvo
            pb=K.pose.bones[n]; cur=(K.matrix_world @ pb.matrix)
            pb.matrix=K.matrix_world.inverted() @ (Matrix.Translation(cur.to_translation()) @ alvo.to_matrix().to_4x4())
            bpy.context.view_layer.update()
        hs=(S.matrix_world @ S.pose.bones["mixamorig:Hips"].matrix).to_translation()
        pbh=K.pose.bones["mixamorig:Hips"]; cur=K.matrix_world @ pbh.matrix
        pbh.matrix=K.matrix_world.inverted() @ (Matrix.Translation(hk0+(hs-hs0)*escala) @ cur.to_quaternion().to_matrix().to_4x4())
        bpy.context.view_layer.update()
        t=(fr-f0)/30.0
        for i,n in enumerate(EXTRAS):
            if C["procedural"]["extras"]=="cauda":
                K.pose.bones[n].rotation_quaternion=Quaternion((0,0,1),math.radians(5*math.sin(t*1.8-i*0.7)))
            else:
                s=1 if n.startswith("Left") else -1
                K.pose.bones[n].rotation_quaternion=Quaternion((1,0,0),math.radians(7*math.sin(t*2.4+s*0.8+i*0.9)))
        for pb in K.pose.bones: pb.keyframe_insert("rotation_quaternion",frame=fr-f0+1)
        pbh.keyframe_insert("location",frame=fr-f0+1)
    act.use_fake_user=True
    for o in [o for o in bpy.data.objects if o not in before]: bpy.data.objects.remove(o, do_unlink=True)
    print("ANIM", nome, f1-f0+1)
K.animation_data.action=None
bpy.ops.wm.save_as_mainfile(filepath=outblend)
