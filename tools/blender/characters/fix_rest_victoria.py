import bpy, numpy as np, sys
from mathutils.kdtree import KDTree
A=np.load("v19.npy")
args=sys.argv[sys.argv.index("--")+1:]
# pesos originais (do AccuRig) pra saber quem tinha braço
bpy.ops.wm.open_mainfile(filepath="/home/claude/rig3/rig_cor.blend")
m0=bpy.data.objects["sk_hero02"]; gi={g.index:g.name for g in m0.vertex_groups}
armish=lambda n: any(k in n for k in ("upperarm","lowerarm","forearm","hand","clavicle","elbow")) or n.startswith(("thumb","index","middle","ring","pinky"))
AW0=np.array([sum(g.weight for g in v.groups if armish(gi[g.group])) for v in m0.data.vertices])
bpy.ops.wm.open_mainfile(filepath="/home/claude/rig3/hd.blend")
m=bpy.data.objects["sk_hero02"]; me=m.data; mw=m.matrix_world; mi=mw.inverted()
gi={g.index:g.name for g in m.vertex_groups}
B=np.array([(mw@v.co)[:] for v in me.vertices])
AW1=np.array([sum(g.weight for g in v.groups if armish(gi[g.group])) for v in me.vertices])
mat=np.zeros(len(B),int)
for p in me.polygons:
    for vi in p.vertices: mat[vi]=p.material_index
cloth=(mat==1)|(mat==2)
clean=cloth&(AW0<0.01)&(A[:,2]>0.75)&(A[:,2]<1.35)
moved=cloth&(AW0>0.01)&(AW1<0.99)
t=np.clip(1-AW1,0,1)[moved]
print("clean",clean.sum(),"moved",moved.sum())
idx=np.where(clean)[0]; kd=KDTree(len(idx))
for j,i in enumerate(idx): kd.insert(A[i],j)
kd.balance()
D=B-A; K=int(args[0])
newB=B.copy()
for k,i in enumerate(np.where(moved)[0]):
    nn=kd.find_n(A[i],K); w=np.array([1/(d+1e-3) for _,_,d in nn]); dd=np.array([D[idx[j]] for _,j,_ in nn])
    tgt=A[i]+(w[:,None]*dd).sum(0)/w.sum()
    newB[i]=B[i]*(1-t[k])+tgt*t[k]
for i in np.where(moved)[0]: me.vertices[i].co=mi@__import__('mathutils').Vector(newB[i])
print("MAXMOVE",np.linalg.norm(newB-B,axis=1).max().round(3))
bpy.ops.wm.save_as_mainfile(filepath=args[1])
