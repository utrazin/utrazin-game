import bpy, sys, json
from mathutils import Vector
src, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
mesh=[x for x in bpy.context.scene.objects if x.type=='MESH'][0]
P="mixamorig:"
J={  # (cabeca, cauda, pai)
 "Hips":((0,-0.40,0.98),(0,-0.39,1.15),None),
 "Spine":((0,-0.39,1.15),(0,-0.38,1.32),"Hips"),
 "Spine1":((0,-0.38,1.32),(0,-0.40,1.50),"Spine"),
 "Spine2":((0,-0.40,1.50),(0,-0.60,1.62),"Spine1"),
 "Neck":((0,-0.60,1.62),(0,-0.95,1.72),"Spine2"),
 "Head":((0,-0.95,1.72),(0,-1.10,2.02),"Neck"),
 "HeadTop_End":((0,-1.10,2.02),(0,-1.15,2.12),"Head"),
 "LeftShoulder":((0.15,-0.40,1.60),(0.55,-0.45,1.68),"Spine2"),
 "LeftArm":((0.55,-0.45,1.68),(0.95,-0.78,1.74),"LeftShoulder"),
 "LeftForeArm":((0.95,-0.78,1.74),(1.32,-1.12,1.86),"LeftArm"),
 "LeftHand":((1.32,-1.12,1.86),(1.62,-1.36,2.0),"LeftForeArm"),
 "LeftHandMiddle1":((1.62,-1.36,2.0),(1.85,-1.58,2.12),"LeftHand"),
 "LeftUpLeg":((0.30,-0.45,0.95),(0.42,-0.56,0.52),"Hips"),
 "LeftLeg":((0.42,-0.56,0.52),(0.46,-0.50,0.20),"LeftUpLeg"),
 "LeftFoot":((0.46,-0.50,0.20),(0.46,-0.80,0.06),"LeftLeg"),
 "LeftToeBase":((0.46,-0.80,0.06),(0.46,-1.00,0.04),"LeftFoot"),
 "LeftArmB_Shoulder":((0.20,-0.40,1.30),(0.55,-0.45,1.25),"Spine1"),
 "LeftArmB_Arm":((0.55,-0.45,1.25),(0.95,-0.50,1.18),"LeftArmB_Shoulder"),
 "LeftArmB_ForeArm":((0.95,-0.50,1.18),(1.33,-0.55,1.04),"LeftArmB_Arm"),
 "LeftArmB_Hand":((1.33,-0.55,1.04),(1.80,-0.66,0.85),"LeftArmB_ForeArm"),
}
for k in list(J):
    if k.startswith("Left"):
        h,t,p=J[k]; J["Right"+k[4:]]=((-h[0],h[1],h[2]),(-t[0],t[1],t[2]),("Right"+p[4:]) if p and p.startswith("Left") else p)
tail=[(0,0.05,0.70),(0.02,0.45,0.60),(0.10,0.85,0.50),(0.35,1.25,0.42),(0.72,1.62,0.39),(1.02,1.97,0.33)]
for i in range(5):
    J[f"Tail{i+1:02d}"]=(tail[i],tail[i+1],"Hips" if i==0 else f"Tail{i:02d}")
arm_d=bpy.data.armatures.new("Krug_Skeleton"); arm=bpy.data.objects.new("Krug_Armature",arm_d)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode='EDIT')
eb={}
order=list(J)
for k in order:
    b=arm_d.edit_bones.new(P+k if not k.startswith(("Tail","LeftArmB","RightArmB")) else k)
    b.head=Vector(J[k][0]); b.tail=Vector(J[k][1]); eb[k]=b
for k in order:
    p=J[k][2]
    if p: eb[k].parent=eb[p]; eb[k].use_connect=(Vector(J[p][1])-Vector(J[k][0])).length<1e-6
# roll: deixar Z dos ossos apontando para frente(-Y)/cima de forma consistente
for k,b in eb.items():
    b.align_roll(Vector((0,-1,0)) if abs((b.tail-b.head).normalized().y)<0.8 else Vector((0,0,1)))
bpy.ops.object.mode_set(mode='OBJECT')
# pesos por regiao + difusao na malha (o "automatico" do Blender falha nesta malha)
import bmesh, numpy as np
me=mesh.data
bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bm.to_mesh(me); me.update(); bm.free()
mw=mesh.matrix_world
V=np.array([mw@v.co for v in me.vertices]); N=len(V)
bones=[b for b in arm_d.bones if not b.name.endswith("HeadTop_End")]
names=[b.name for b in bones]
H=np.array([arm.matrix_world@b.head_local for b in bones]); T=np.array([arm.matrix_world@b.tail_local for b in bones])
def segdist(P,a,b):
    ab=b-a; t=np.clip(((P-a)@ab)/(ab@ab),0,1); return np.linalg.norm(P-(a+t[:,None]*ab),axis=1)
Dm=np.stack([segdist(V,H[i],T[i]) for i in range(len(bones))],axis=1)
x,y,z=V[:,0],V[:,1],V[:,2]; ax=np.abs(x)
def idx(pref): return [i for i,n in enumerate(names) if any(n.split(':')[-1].startswith(p) for p in pref)]
SPINE=idx(["Hips","Spine"]); HEAD=idx(["Neck","Head"]); TAIL=idx(["Tail"])
LEGL=idx(["LeftUpLeg","LeftLeg","LeftFoot","LeftToe"]); LEGR=idx(["RightUpLeg","RightLeg","RightFoot","RightToe"])
ARMAL=idx(["LeftShoulder","LeftArm","LeftForeArm","LeftHand"]); ARMAL=[i for i in ARMAL if "ArmB" not in names[i]]
ARMAR=idx(["RightShoulder","RightArm","RightForeArm","RightHand"]); ARMAR=[i for i in ARMAR if "ArmB" not in names[i]]
ARMBL=idx(["LeftArmB"]); ARMBR=idx(["RightArmB"])
allow=np.zeros(Dm.shape,bool); allow[:,SPINE]=True
m=(z>1.55)&(y<-0.6)&(ax<0.5); allow[np.ix_(m,HEAD)]=True
m=(y>-0.1)&(z<0.78); allow[np.ix_(m,TAIL)]=True
m=(z<1.0)&(y<0.05)&(x>0.15); allow[np.ix_(m,LEGL)]=True
m=(z<1.0)&(y<0.05)&(x<-0.15); allow[np.ix_(m,LEGR)]=True
m=(x>0.42)&(z>1.42); allow[np.ix_(m,ARMAL)]=True
m=(x<-0.42)&(z>1.42); allow[np.ix_(m,ARMAR)]=True
m=(x>0.42)&(z>0.5)&(z<1.48)&(y<0.05); allow[np.ix_(m,ARMBL)]=True
m=(x<-0.42)&(z>0.5)&(z<1.48)&(y<0.05); allow[np.ix_(m,ARMBR)]=True
# avental da frente: segue o quadril, nao as pernas
apr=(y<-0.82)&(z>0.45)&(z<1.15)&(ax<0.5); allow[apr,:]=False; allow[np.ix_(apr,idx(["Hips"]))]=True
D=np.where(allow,Dm,1e9)
lab=D.argmin(1)
W=np.zeros(Dm.shape); W[np.arange(N),lab]=1.0
# vizinhanca
nb=[[] for _ in range(N)]
for e in me.edges:
    a,b=e.vertices; nb[a].append(b); nb[b].append(a)
for it in range(10):
    W2=W.copy()
    for i in range(N):
        if nb[i]: W2[i]=0.5*W[i]+0.5*W[nb[i]].mean(0)
    W=np.where(allow,W2,0); W/=np.maximum(W.sum(1,keepdims=True),1e-9)
# top 4
order=np.argsort(-W,1)[:,:4]
for i,nm in enumerate(names): mesh.vertex_groups.new(name=nm)
for vi in range(N):
    ws=W[vi,order[vi]]; ws=ws/ws.sum()
    for bi,w in zip(order[vi],ws):
        if w>0.01: mesh.vertex_groups[names[bi]].add([vi],float(w),'REPLACE')
mesh.parent=arm
mod=mesh.modifiers.new("Armature",'ARMATURE'); mod.object=arm
from collections import Counter
cnt=Counter(names[i] for i in lab)
print("ROTULOS", dict(cnt))
bpy.ops.wm.save_as_mainfile(filepath=out)
