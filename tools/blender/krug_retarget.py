"""Passa animacoes Mixamo (FBX sem skin) para o esqueleto do Krug e adiciona braco de baixo e rabo procedurais."""
import bpy, sys, os, glob, math
from mathutils import Matrix, Quaternion, Vector
blend, animdir, outblend = sys.argv[-3], sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
sc=bpy.context.scene; sc.render.fps=30
K=bpy.data.objects["Krug_Armature"]
MAP=[n for n in K.pose.bones.keys() if n.startswith("mixamorig:")]
def depth(n):
    d=0; b=K.data.bones[n]
    while b.parent: d+=1; b=b.parent
    return d
MAP.sort(key=depth)
def rest_world(arm,name):
    return arm.matrix_world @ arm.data.bones[name].matrix_local
def bone_dir(arm,name):
    b=arm.data.bones[name]; return ((arm.matrix_world.to_3x3()) @ (b.tail_local-b.head_local)).normalized()
acts={}
ABRE=math.radians(28)
OFF_L=Quaternion((0,1,0),-ABRE); OFF_R=Quaternion((0,1,0),ABRE)
for f in sorted(glob.glob(animdir+"/*.fbx")):
    nome=os.path.splitext(os.path.basename(f))[0]
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=f)
    S=[o for o in bpy.data.objects if o not in before and o.type=='ARMATURE'][0]
    sa=S.animation_data.action; f0,f1=[int(x) for x in sa.frame_range]
    # correcao de pose de repouso (alinha direcao dos ossos do Krug a do Mixamo)
    corr={}
    for n in MAP:
        if n not in S.data.bones: continue
        if n.endswith(("HeadTop_End",)): continue
        braco=any(k in n for k in ("Shoulder","Arm","Hand")) 
        if braco:
            dk=bone_dir(K,n); ds=bone_dir(S,n)
            corr[n]=dk.rotation_difference(ds)  # leva a direcao do Krug para a do Mixamo (so bracos)
        else:
            corr[n]=Quaternion()
    act=bpy.data.actions.new("Krug_"+nome); K.animation_data_create(); K.animation_data.action=act
    for pb in K.pose.bones: pb.rotation_mode='QUATERNION'
    Rs0={n:rest_world(S,n).to_quaternion() for n in corr}
    Rt0={n:rest_world(K,n).to_quaternion() for n in corr}
    hs0=(S.matrix_world@S.data.bones["mixamorig:Hips"].head_local)
    hk0=(K.matrix_world@K.data.bones["mixamorig:Hips"].head_local)
    escala=hk0.z/max(hs0.z,1e-6)
    for fr in range(f0,f1+1):
        sc.frame_set(fr)
        for pb in K.pose.bones: pb.rotation_quaternion=(1,0,0,0); pb.location=(0,0,0)
        bpy.context.view_layer.update()
        for n in MAP:
            if n not in corr: continue
            Rs=(S.matrix_world @ S.pose.bones[n].matrix).to_quaternion()
            delta=Rs @ Rs0[n].inverted()
            alvo=delta @ corr[n] @ Rt0[n]
            if ("LeftArm" in n or "LeftForeArm" in n or "LeftHand" in n): alvo=OFF_L @ alvo
            if ("RightArm" in n or "RightForeArm" in n or "RightHand" in n): alvo=OFF_R @ alvo
            pb=K.pose.bones[n]
            cur=(K.matrix_world @ pb.matrix)
            M=Matrix.Translation(cur.to_translation()) @ alvo.to_matrix().to_4x4()
            pb.matrix=K.matrix_world.inverted() @ M
            bpy.context.view_layer.update()
        # quadril: deslocamento
        hs=(S.matrix_world @ S.pose.bones["mixamorig:Hips"].matrix).to_translation()
        d=(hs-hs0)*escala
        pbh=K.pose.bones["mixamorig:Hips"]
        cur=K.matrix_world @ pbh.matrix
        pbh.matrix=K.matrix_world.inverted() @ (Matrix.Translation(hk0+d) @ cur.to_quaternion().to_matrix().to_4x4())
        bpy.context.view_layer.update()
        t=(fr-f0)/30.0
        # bracos de baixo: apoiados, balanco leve
        for side,sg in (("Left",1),("Right",-1)):
            K.pose.bones[f"{side}ArmB_Arm"].rotation_quaternion=Quaternion((1,0,0),math.radians(-12+3*math.sin(t*1.3+sg)))
            K.pose.bones[f"{side}ArmB_ForeArm"].rotation_quaternion=Quaternion((1,0,0),math.radians(-18+4*math.sin(t*1.1)))
        for i in range(5):
            K.pose.bones[f"Tail{i+1:02d}"].rotation_quaternion=Quaternion((0,0,1),math.radians(4*math.sin(t*1.6-i*0.6)))
        for pb in K.pose.bones:
            pb.keyframe_insert("rotation_quaternion",frame=fr-f0+1)
        K.pose.bones["mixamorig:Hips"].keyframe_insert("location",frame=fr-f0+1)
    act.use_fake_user=True; acts[nome]=(f1-f0+1)
    # remove o esqueleto mixamo
    for o in [o for o in bpy.data.objects if o not in before]: bpy.data.objects.remove(o, do_unlink=True)
    print("ANIM", nome, f1-f0+1, "frames")
K.animation_data.action=None
bpy.ops.wm.save_as_mainfile(filepath=outblend)
