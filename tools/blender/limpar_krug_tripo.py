"""Limpeza do Krug (Tripo): tira pecas da regua, pinta cova da boca e bolso escuro do avental (troca de UV), escala 2,4 m.
Uso: python -I limpar_krug_tripo.py -- entrada.glb textura_basecolor.png saida.glb relatorio.json
Coordenadas dos defeitos sao especificas deste modelo (vista de frente ortografica 1,15 de largura)."""
import bpy, bmesh, sys, json, math
import numpy as np
from mathutils import Vector, kdtree
from mathutils.geometry import barycentric_transform
src, tex_orig, out, report = sys.argv[-4], sys.argv[-3], sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
o=[x for x in bpy.context.scene.objects if x.type=='MESH'][0]
me=o.data; rep={}
bm=bmesh.new(); bm.from_mesh(me)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.verts.ensure_lookup_table()
# 1) ilhas soltas pequenas e longe (regua)
seen=set(); isl=[]
for v in bm.verts:
    if v in seen: continue
    st=[v]; c=[]; seen.add(v)
    while st:
        x=st.pop(); c.append(x)
        for e in x.link_edges:
            y=e.other_vert(x)
            if y not in seen: seen.add(y); st.append(y)
    isl.append(c)
isl.sort(key=len, reverse=True)
kd=kdtree.KDTree(len(isl[0]))
for v in isl[0]: kd.insert(v.co, v.index)
kd.balance()
apagar=[c for c in isl[1:] if len(c)<=8 and min(kd.find(v.co)[2] for v in c)>0.03]
rep["ilhas_apagadas"]=[[len(c), [round(x,3) for x in c[0].co]] for c in apagar]
bmesh.ops.delete(bm, geom=[v for c in apagar for v in c], context='VERTS')
# 2) buracos (bordas abertas)
bm.edges.ensure_lookup_table()
borda=[e for e in bm.edges if e.is_boundary]
# agrupa bordas em lacos
grupos=[]; usadas=set()
for e in borda:
    if e in usadas: continue
    st=[e]; g=[]; usadas.add(e)
    while st:
        x=st.pop(); g.append(x)
        for v in x.verts:
            for y in v.link_edges:
                if y.is_boundary and y not in usadas: usadas.add(y); st.append(y)
    grupos.append(g)
alvo=Vector((-0.0099,-0.36,0.4628))
rep["buracos"]=[]
uvl=bm.loops.layers.uv.active
# UV de pele: ponto da superficie logo ao lado do buraco
pele_uv=None
bm.faces.ensure_lookup_table()
from mathutils.bvhtree import BVHTree
bvh=BVHTree.FromBMesh(bm)
loc,nor,fi,d=bvh.ray_cast(Vector((-0.0132,-3,0.4628+0.0016)),Vector((0,1,0)))
f=bm.faces[fi]; vs=[l.vert.co for l in f.loops]; uvs=[l[uvl].uv for l in f.loops]
r=barycentric_transform(loc,vs[0],vs[1],vs[2],Vector((uvs[0].x,uvs[0].y,0)),Vector((uvs[1].x,uvs[1].y,0)),Vector((uvs[2].x,uvs[2].y,0)))
pele_uv=(r.x,r.y); rep["pele_uv"]=pele_uv; rep["pele_hit_y"]=round(loc.y,3)
for g in grupos:
    c=sum((v.co for e in g for v in e.verts), Vector())/(2*len(g))
    perto=(c-alvo).length<0.04
    rep["buracos"].append({"arestas":len(g),"centro":[round(x,3) for x in c],"fechado":perto})
    if perto:
        res=bmesh.ops.holes_fill(bm, edges=g, sides=0)
        novas=[fa for fa in res["faces"] if fa.is_valid]
        tri=bmesh.ops.triangulate(bm, faces=novas)
        novas=[fa for fa in tri["faces"] if fa.is_valid]
        for fa in novas:
            for l in fa.loops: l[uvl].uv=pele_uv
        rep["faces_novas"]=len(novas)
# 2b) bolso escuro do avental: faces com UV apontando para o fundo preto do atlas
from PIL import Image
T=np.asarray(Image.open(tex_orig).convert('L')).astype(int); TH,TW=T.shape
def lum_uv(uv):
    x=min(TW-1,max(0,int(uv.x*TW))); y=min(TH-1,max(0,int((1-uv.y)*TH))); return T[y,x]
bm.faces.ensure_lookup_table(); bm.verts.ensure_lookup_table()
bvh=BVHTree.FromBMesh(bm)
S=1.15/1400
def hit(x,z):
    loc,nor,fi,d=bvh.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
    return loc,fi
def face_dark(f):
    us=[l[uvl].uv for l in f.loops]; c=sum((u for u in us),Vector((0,0)))/len(us)
    return lum_uv(c)<95

LIM=60
marcadas=set()
def face_min_lum(f):
    us=[l[uvl].uv for l in f.loops]; c=sum((u for u in us),Vector((0,0)))/len(us)
    return min([lum_uv(c)]+[lum_uv(c+(u-c)*0.7) for u in us])
for f in bm.faces:
    c=f.calc_center_median()
    if -0.062<c.x<0.016 and 0.14<c.z<0.215 and c.y<-0.17 and face_min_lum(f)<LIM:
        marcadas.add(f.index)
rep["faces_bolso"]=len(marcadas)
def uv_at(loc,fi):
    f=bm.faces[fi]; vs=[l.vert.co for l in f.loops]; uvs=[l[uvl].uv for l in f.loops]
    r=barycentric_transform(loc,vs[0],vs[1],vs[2],Vector((uvs[0].x,uvs[0].y,0)),Vector((uvs[1].x,uvs[1].y,0)),Vector((uvs[2].x,uvs[2].y,0)))
    return Vector((r.x,r.y))
loc,fd=hit((720-700)*S,0.31-(672-500)*S); uv_av=uv_at(loc,fd); rep["uv_avental"]=list(uv_av)
for fi in marcadas:
    for l in bm.faces[fi].loops: l[uvl].uv=uv_av
falhas=0
rep["loops_sem_doador"]=falhas
# 2c) boca: cova funda (sem borda aberta) -> pinta de pele trocando o UV das faces da cova
cova=set()
for v4 in range(306*4,322*4):
    for u4 in range(680*4,698*4):
        u=u4/4; v=v4/4
        loc,fi=hit((u-700)*S,0.31-(v-500)*S)
        if fi is not None and loc.y>-0.42: cova.add(fi)
for _ in range(2):
    viz=set()
    for fi in cova:
        for e in bm.faces[fi].edges:
            for f2 in e.link_faces:
                if f2.index not in cova and f2.calc_center_median().y>-0.425: viz.add(f2.index)
    cova|=viz
rep["faces_boca"]=len(cova)
loc,fd=hit((682-700)*S,0.31-(326-500)*S); uv_pele=uv_at(loc,fd); rep["uv_pele"]=list(uv_pele)
for fi in cova:
    for l in bm.faces[fi].loops: l[uvl].uv=uv_pele
falhas=0
rep["boca_loops_sem_doador"]=falhas

bm.to_mesh(me)
# 3) textura corrigida
for im in bpy.data.images: im.name="Krug_basecolor"
# 4) escala 2,4 m, pes no chao
zmin=min(v.co.z for v in me.vertices); zmax=max(v.co.z for v in me.vertices)
k=2.4/(zmax-zmin); rep["escala"]=round(k,4)
for v in me.vertices: v.co.z-=zmin; v.co*=k
o.name="NPC_Krug"; me.name="NPC_Krug"
rep["verts"]=len(me.vertices); rep["faces"]=len(me.polygons)
rep["altura_m"]=round(max(v.co.z for v in me.vertices),3)
rep["largura_m"]=round(max(v.co.x for v in me.vertices)-min(v.co.x for v in me.vertices),3)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_image_format='JPEG', export_jpeg_quality=92)
bpy.ops.wm.save_as_mainfile(filepath=out.replace('.glb','.blend'))
json.dump(rep, open(report,'w'), indent=1); print(json.dumps(rep, indent=1))
