import bpy, bmesh, sys, numpy as np
from mathutils import kdtree
src, out, altura = sys.argv[-3], sys.argv[-2], float(sys.argv[-1])
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=src)
o=[x for x in bpy.context.scene.objects if x.type=='MESH'][0]; me=o.data
bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=1e-5); bm.verts.ensure_lookup_table()
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
isl.sort(key=len,reverse=True)
kd=kdtree.KDTree(sum(len(c) for c in isl[:1])); [kd.insert(v.co,v.index) for v in isl[0]]; kd.balance()
rest=[v for c in isl[1:] for v in c]
apagar=[c for c in isl[1:] if len(c)<=8 and min(kd.find(v.co)[2] for v in c)>0.03]
bmesh.ops.delete(bm, geom=[v for c in apagar for v in c], context='VERTS'); print("APAGADAS", len(apagar))
bm.to_mesh(me); me.update()
zs=[ (o.matrix_world@v.co).z for v in me.vertices]; zmin,zmax=min(zs),max(zs); k=altura/(zmax-zmin)
for v in me.vertices: v.co.z-=zmin; v.co*=k
print("ESCALA", round(k,4), "verts", len(me.vertices))
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_image_format='JPEG', export_jpeg_quality=92)
