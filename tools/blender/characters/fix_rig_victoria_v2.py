import bpy, sys, numpy as np
from mathutils import Vector
args=sys.argv[sys.argv.index("--")+1:]
R=float(args[0]); BAND=float(args[1]); out=args[2]
bpy.ops.wm.open_mainfile(filepath="/home/claude/rig3/rig_cor.blend")
a=bpy.data.objects["Armature"]; m=bpy.data.objects["sk_hero02"]; me=m.data; mw=m.matrix_world
hood=[i for i,mt in enumerate(me.materials) if "4bb142d0" in mt.name][0]
hv=set()
for p in me.polygons:
    if p.material_index==hood: hv.update(p.vertices)
def P(b,t="head"): bb=a.data.bones[b]; return a.matrix_world@(bb.head_local if t=="head" else bb.tail_local)
chains={s:[P("upperarm_"+s),P("lowerarm_"+s),P("hand_"+s),P("middle_03_"+s,"tail")] for s in "lr"}
RAD=[float(x) for x in args[3].split(",")]  # raio no ombro, cotovelo, pulso, ponta da mão
def dseg(p,a_,b_,r0,r1):
    ab=b_-a_; t=max(0,min(1,(p-a_).dot(ab)/ab.dot(ab))); return (p-(a_+ab*t)).length-(r0+(r1-r0)*t)
gi={g.index:g.name for g in m.vertex_groups}
armish=lambda n: any(k in n for k in ("upperarm","lowerarm","forearm","hand","clavicle","elbow")) or any(n.startswith(f) for f in ("thumb","index","middle","ring","pinky"))
VG={n:m.vertex_groups[n] for n in ("spine_02","spine_03","spine_04","pelvis") if n in m.vertex_groups}
n_fix=0
for vi in hv:
    v=me.vertices[vi]; p=mw@v.co
    arm=[g for g in v.groups if armish(gi[g.group]) and g.weight>0]
    if not arm: continue
    handw=sum(g.weight for g in v.groups if gi[g.group].startswith(("hand","thumb","index","middle","ring","pinky")))
    if handw>0.2: continue  # a mão faz parte da malha do moletom
    side="l" if p.x>0 else "r"; c=chains[side]
    d=min(dseg(p,c[i],c[i+1],RAD[i],RAD[i+1]) for i in range(3))
    if d<0: continue
    t=min(1.0,d/BAND)  # 1 = tronco puro
    keep=1-t
    for g in arm: g.weight*=keep
    tot=sum(g.weight for g in v.groups)
    if tot<0.999:
        miss=1-tot
        tgt="spine_04" if p.z>1.2 else "spine_03" if p.z>1.08 else "spine_02" if p.z>0.98 else "pelvis"
        VG[tgt].add([vi],miss,'ADD')
    n_fix+=1
print("FIXED",n_fix)
# calça nunca segue braço/mão
pm=[i for i,mt in enumerate(me.materials) if "2deb5f24" in mt.name][0]
pv=set()
for p in me.polygons:
    if p.material_index==pm: pv.update(p.vertices)
npf=0
for vi in pv:
    v=me.vertices[vi]; arm=[g for g in v.groups if armish(gi[g.group]) and g.weight>0]
    if not arm: continue
    for g in arm: g.weight=0.0
    tot=sum(g.weight for g in v.groups)
    if tot<1e-4: VG["pelvis"].add([vi],1.0,'REPLACE')
    else:
        for g in v.groups: g.weight/=tot
    npf+=1
print("PANTS_FIXED",npf)
# suaviza pesos na faixa lateral do moletom (tira pontas)
bpy.context.view_layer.objects.active=m
for v in me.vertices: v.select=False
ns=0
for vi in hv:
    p=mw@me.vertices[vi].co
    hw=sum(g.weight for g in me.vertices[vi].groups if gi[g.group].startswith(("hand","thumb","index","middle","ring","pinky")))
    if 0.9<p.z<1.22 and abs(p.x)>0.12 and hw<0.05:
        c=chains["l" if p.x>0 else "r"]
        if min(dseg(p,c[i],c[i+1],RAD[i],RAD[i+1]) for i in range(3))>-0.02: me.vertices[vi].select=True; ns+=1
print("SMOOTH_SEL",ns)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.object.vertex_group_smooth(group_select_mode='ALL',factor=0.5,repeat=int(args[4]) if len(args)>4 else 4)
bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL',lock_active=False); bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.wm.save_as_mainfile(filepath=out)
