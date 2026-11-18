"""Esqueleto (nomes Mixamo + extras) e pesos por regiao + difusao, a partir de um JSON de juntas."""
import bpy, bmesh, sys, json, numpy as np
from mathutils import Vector
src, cfgp, out = sys.argv[-3], sys.argv[-2], sys.argv[-1]
C=json.load(open(cfgp))
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=src)
mesh=[x for x in bpy.context.scene.objects if x.type=='MESH'][0]
P="mixamorig:"
J=dict(C["J"])
for k in list(J):
    if k.startswith("Left"):
        h,t,p=J[k]; J["Right"+k[4:]]=[[-h[0],h[1],h[2]],[-t[0],t[1],t[2]],("Right"+p[4:]) if p and p.startswith("Left") else p]
E=dict(C.get("extras",{}))
for k in list(E):
    if k.startswith("Left"):
        h,t,p=E[k]; E["Right"+k[4:]]=[[-h[0],h[1],h[2]],[-t[0],t[1],t[2]],("Right"+p[4:]) if p and p.startswith("Left") else p]
def full(k): return k if k in E else P+k
ALL={**{k:v for k,v in J.items()},**E}
arm_d=bpy.data.armatures.new("Skel_"+C["nome"]); arm=bpy.data.objects.new("Arm_"+C["nome"],arm_d); bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode='EDIT')
eb={}
for k,(h,t,p) in ALL.items():
    b=arm_d.edit_bones.new(full(k)); b.head=Vector(h); b.tail=Vector(t); eb[k]=b
for k,(h,t,p) in ALL.items():
    if p:
        pp=p if p in ALL else p.replace(P,"")
        eb[k].parent=eb[pp]; eb[k].use_connect=(Vector(ALL[pp][1])-Vector(h)).length<1e-6
for k,b in eb.items():
    b.align_roll(Vector((0,-1,0)) if abs((b.tail-b.head).normalized().y)<0.8 else Vector((0,0,1)))
bpy.ops.object.mode_set(mode='OBJECT')
me=mesh.data
bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bm.to_mesh(me); me.update(); bm.free()
V=np.array([mesh.matrix_world@v.co for v in me.vertices]); N=len(V)
bones=[b for b in arm_d.bones if not b.name.endswith("HeadTop_End")]; names=[b.name for b in bones]
H=np.array([b.head_local for b in bones]); T=np.array([b.tail_local for b in bones])
def segdist(Pp,a,b):
    ab=b-a; t=np.clip(((Pp-a)@ab)/(ab@ab),0,1); return np.linalg.norm(Pp-(a+t[:,None]*ab),axis=1)
Dm=np.stack([segdist(V,H[i],T[i]) for i in range(len(bones))],axis=1)
x,y,z=V[:,0],V[:,1],V[:,2]; ax=np.abs(x)
R={k:eval(v) for k,v in C["regras"].items()}
def idx(cond): return [i for i,n in enumerate(names) if cond(n.split(':')[-1])]
SPINE=idx(lambda n:n.startswith(("Hips","Spine"))); HEAD=idx(lambda n:n.startswith(("Neck","Head")))
ARML=idx(lambda n:n.startswith(("LeftShoulder","LeftArm","LeftForeArm","LeftHand"))); ARMR=idx(lambda n:n.startswith(("RightShoulder","RightArm","RightForeArm","RightHand")))
LEGL=idx(lambda n:n.startswith(("LeftUpLeg","LeftLeg","LeftFoot","LeftToe"))); LEGR=idx(lambda n:n.startswith(("RightUpLeg","RightLeg","RightFoot","RightToe")))
EXT=[i for i,n in enumerate(names) if n in E]
EXTL=[i for i in EXT if not names[i].startswith("Right")]; EXTR=[i for i in EXT if names[i].startswith("Right") or not names[i].startswith("Left")]
allow=np.zeros(Dm.shape,bool); allow[:,SPINE]=True
allow[np.ix_(R["HEAD"],HEAD)]=True
allow[np.ix_(R["ARML"],ARML)]=True; allow[np.ix_(R["ARMR"],ARMR)]=True
allow[np.ix_(R["LEGL"],LEGL)]=True; allow[np.ix_(R["LEGR"],LEGR)]=True
if EXT:
    if any(names[i].startswith(("Left","Right")) for i in EXT):
        allow[np.ix_(R["EXTRA"]&(x>=0),[i for i in EXT if names[i].startswith("Left")])]=True
        allow[np.ix_(R["EXTRA"]&(x<0),[i for i in EXT if names[i].startswith("Right")])]=True
    else:
        allow[np.ix_(R["EXTRA"],EXT)]=True
if "SO_QUADRIL" in R:
    m=R["SO_QUADRIL"]; allow[m,:]=False; allow[np.ix_(m,idx(lambda n:n=="Hips"))]=True
if "SO_COSTAS" in R:
    m=R["SO_COSTAS"]; allow[m,:]=False; allow[np.ix_(m,idx(lambda n:n in("Spine1","Spine2")))]=True
D=np.where(allow,Dm,1e9); lab=D.argmin(1)
W=np.zeros(Dm.shape); W[np.arange(N),lab]=1.0
nb=[[] for _ in range(N)]
for e in me.edges:
    a,b=e.vertices; nb[a].append(b); nb[b].append(a)
for it in range(8):
    W2=W.copy()
    for i in range(N):
        if nb[i]: W2[i]=0.5*W[i]+0.5*W[nb[i]].mean(0)
    W=np.where(allow,W2,0); W/=np.maximum(W.sum(1,keepdims=True),1e-9)
order=np.argsort(-W,1)[:,:4]
for nm in names: mesh.vertex_groups.new(name=nm)
for vi in range(N):
    ws=W[vi,order[vi]]; ws=ws/ws.sum()
    for bi,w in zip(order[vi],ws):
        if w>0.01: mesh.vertex_groups[names[bi]].add([vi],float(w),'REPLACE')
mesh.parent=arm; mod=mesh.modifiers.new("Armature",'ARMATURE'); mod.object=arm
from collections import Counter
print("ROTULOS", dict(Counter(names[i] for i in lab)))
bpy.ops.wm.save_as_mainfile(filepath=out)
