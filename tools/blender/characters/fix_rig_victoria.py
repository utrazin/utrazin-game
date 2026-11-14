import bpy, bmesh, numpy as np, sys
from mathutils import Vector
args=sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.open_mainfile(filepath=args[0]); out=args[1]
SM_R=float(args[2]); SM_REP=int(args[3]); ZTOP=float(args[5]); DO_KD=int(args[6]) if len(args)>6 else 0; BAND=float(args[7]) if len(args)>7 else 0.0
a=bpy.data.objects["Armature"]; m=bpy.data.objects["sk_hero02"]; me=m.data; mw=m.matrix_world
a.animation_data_clear()
mats=[x.name for x in me.materials]
jmat=[i for i,n in enumerate(mats) if n.startswith("tripo_node_c8b5")]  # descoberto abaixo
# descobre qual material é o top: o que tem mais faces com z entre 1.0 e 1.2 e |x|<0.15
cnt={}
for p in me.polygons:
    c=mw@p.center
    if 1.0<c.z<1.2 and abs(c.x)<0.15: cnt[p.material_index]=cnt.get(p.material_index,0)+1
top_mi=max(cnt,key=cnt.get); print("TOP_MAT",mats[top_mi],cnt)
under_mi=[i for i,n in enumerate(mats) if n.startswith("jacket_underlayer")]
img=[nd.image for nd in me.materials[top_mi].node_tree.nodes if nd.type=='TEX_IMAGE'][0]
W,H=img.size; px=np.empty(W*H*4,np.float32); img.pixels.foreach_get(px); px=px.reshape(H,W,4)
uv=me.uv_layers.active.data
skin_v=set(); cloth_v=set(); topverts=set(); head_or_nail={}
for p in me.polygons:
    if p.material_index==top_mi or p.material_index in under_mi:
        for li in p.loop_indices:
            vi=me.loops[li].vertex_index
            if p.material_index in under_mi: cloth_v.add(vi); continue
            u,v=uv[li].uv; c=px[int(v*H)%H,int(u*W)%W]
            if c[0]>0.35 and c[0]-c[2]>0.12: skin_v.add(vi)
            else: cloth_v.add(vi)
cloth_only=cloth_v-skin_v
gi={g.index:g.name for g in m.vertex_groups}
armish=lambda n: any(k in n for k in ("upperarm","clavicle","lowerarm","forearm","hand"))
sp4=m.vertex_groups["spine_04"]; sp3=m.vertex_groups["spine_03"]
nfix=0
for vi in cloth_only:
    v=me.vertices[vi]; w=mw@v.co
    if abs(w.x)>0.19 or w.z>ZTOP+BAND or w.z<0.95: continue
    arm=[g for g in v.groups if armish(gi[g.group])]
    if not arm: continue
    if w.z>ZTOP:
        t=(w.z-ZTOP)/BAND
        for g in arm: g.weight*=t
        tot=sum(g.weight for g in v.groups)
        if tot>1e-6:
            for g in v.groups: g.weight/=tot
        nfix+=1; continue
    rest=sum(g.weight for g in v.groups if not armish(gi[g.group]))
    for g in arm: m.vertex_groups[gi[g.group]].remove([vi])
    if rest<1e-4: (sp4 if w.z>1.12 else sp3).add([vi],1.0,'REPLACE')
    nfix+=1
print("CLOTH_FIXED",nfix)
# suaviza pesos da pele no sovaco
bpy.context.view_layer.objects.active=m; m.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.object.mode_set(mode='OBJECT')
sel=0
for v in me.vertices:
    w=mw@v.co
    for sx in (1,-1):
        if (w-Vector((0.125*sx,0.035,1.215))).length<SM_R: v.select=True; sel+=1
print("ARMPIT_SEL",sel)
bpy.ops.object.mode_set(mode='EDIT')
if SM_REP>0: bpy.ops.object.vertex_group_smooth(group_select_mode='ALL',factor=0.5,repeat=SM_REP,expand=0.0)
bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL',lock_active=False)
bpy.ops.object.mode_set(mode='OBJECT')
# camadas pretas: copia os pesos do vértice "de verdade" mais próximo (pra acompanharem a pele/roupa igualzinho)
from mathutils.kdtree import KDTree
me=m.data
umi=[i for i,n in enumerate([x.name for x in me.materials]) if "underlayer" in n]
uv_set=set(); real=set()
for p in me.polygons:
    (uv_set if p.material_index in umi else real).update(p.vertices)
uv_set-=real
kd=KDTree(len(real))
for vi in real: kd.insert(me.vertices[vi].co,vi)
kd.balance()
for vi in (uv_set if DO_KD else []):
    v=me.vertices[vi]; co,src,d=kd.find(v.co)
    for g in list(v.groups): m.vertex_groups[g.group].remove([vi])
    for g in me.vertices[src].groups: m.vertex_groups[g.group].add([vi],g.weight,'REPLACE')
print("UNDER_COPY",len(uv_set))
# unha do dedão: suaviza a geometria quebrada (verts com peso no thumb_03 e cor escura de unha)
me=m.data; uv=me.uv_layers.active.data
bm=bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
dark=set()
for p in me.polygons:
    if p.material_index!=top_mi: continue
    for li in p.loop_indices:
        u,v=uv[li].uv; c=px[int(v*H)%H,int(u*W)%W]
        if c[:3].mean()<0.25: dark.add(me.loops[li].vertex_index)
for side in ("l","r"):
    g=m.vertex_groups["thumb_03_"+side].index; g2=m.vertex_groups["thumb_02_"+side].index
    ids=[v.index for v in me.vertices if any((x.group==g and x.weight>0.05) or (x.group==g2 and x.weight>0.5) for x in v.groups) and v.index in dark]
    bone=a.data.bones["thumb_03_"+side]
    A=mw.inverted()@(a.matrix_world@bone.head_local); B=mw.inverted()@(a.matrix_world@bone.tail_local)
    Bx=A+(B-A)*1.6
    def seg(p):
        ab=Bx-A; t=max(0.0,min(1.0,(p-A).dot(ab)/ab.dot(ab))); q=A+ab*t; return q,(p-q).length
    allv=[v for v in me.vertices if any(x.group==g and x.weight>0.05 for x in v.groups)]
    sk=[seg(v.co)[1] for v in allv if v.index not in dark]
    sk.sort(); rc=sk[len(sk)//2]*float(args[4]) if sk else 0
    nmov=0
    for i in ids:
        v=bm.verts[i]; q,d=seg(v.co)
        if d>rc and d>0: v.co=q+(v.co-q)*(rc/d); nmov+=1
    for v in allv:
        if v.index in ids: continue
        bv=bm.verts[v.index]; q,d=seg(bv.co)
        if d>rc*1.2 and d>0: bv.co=q+(bv.co-q)*(rc*1.2/d); nmov+=1
    print("THUMB_CLAMP",side,"rc",round(rc,3),"moved",nmov)
    print("THUMB",side,len(ids))
bm.to_mesh(me); bm.free()
bpy.ops.wm.save_as_mainfile(filepath=out); print("SAVED")
