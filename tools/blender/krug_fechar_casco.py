"""Fecha a fresta entre a borda do casco e o corpo (vista de lado), empurrando o fundo da fresta para fora."""
import bpy, bmesh, sys, json, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from scipy import ndimage
src, out, rep_path = sys.argv[-3], sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
o=[x for x in bpy.context.scene.objects if x.type=='MESH'][0]; me=o.data
bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
STEP=0.01; Y0,Y1,Z0,Z1=-0.75,0.35,0.75,2.0
ys=np.arange(Y0,Y1,STEP); zs=np.arange(Z0,Z1,STEP)
rep={}
moved_total=0
for lado in (1,-1):
    bvh=BVHTree.FromBMesh(bm)
    D=np.full((len(zs),len(ys)),np.nan)
    for i,z in enumerate(zs):
        for j,y in enumerate(ys):
            loc,nor,fi,d=bvh.ray_cast(Vector((lado*5,y,z)),Vector((-lado,0,0)))
            if loc is not None: D[i,j]=lado*loc.x   # quanto maior, mais para fora
    valid=~np.isnan(D); Df=np.where(valid,D,-1.0)
    env=ndimage.grey_closing(Df,size=(13,13))       # envelope que tapa frestas de ate ~12 cm
    env=ndimage.grey_opening(env,size=(3,3))
    YY=np.broadcast_to(ys[None,:],Df.shape)
    gap=valid&(env-Df>0.04)&(env-Df<0.15)&(Df>0.15)&(YY>-0.55)&(YY<0.05)   # fresta estreita, so na borda do casco
    gap=ndimage.binary_opening(gap,iterations=1)
    lab,n=ndimage.label(gap); sizes=ndimage.sum(gap,lab,range(1,n+1))
    keep=np.isin(lab,[k+1 for k,s in enumerate(sizes) if s>=15])
    rep[f"lado_{lado}_pixels_fresta"]=int(keep.sum())
    # move vertices visiveis do lado cujo (y,z) cai na fresta e que estao abaixo do envelope
    moved=0
    for v in bm.verts:
        x=lado*v.co.x
        if x<0.1: continue
        j=int(round((v.co.y-Y0)/STEP)); i=int(round((v.co.z-Z0)/STEP))
        if not (0<=i<len(zs) and 0<=j<len(ys)): continue
        # area da fresta dilatada um pouco para suavizar
        win=keep[max(0,i-2):i+3, max(0,j-2):j+3]
        if not win.any(): continue
        target=min(env[i,j]-0.012, x+0.12)
        if env[i,j]-Df[i,j]>0.15: continue
        if x<target-0.01 and x>Df[i,j]-0.06:
            novo=x+(target-x)*0.9
            v.co.x=lado*novo; moved+=1
    rep[f"lado_{lado}_vertices_movidos"]=moved; moved_total+=moved
    np.save(out.replace('.glb',f'_gap_{lado}.npy'),keep)
bm.to_mesh(me); me.update()
for p in me.polygons: p.use_smooth=True
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_image_format='JPEG', export_jpeg_quality=92)
json.dump(rep,open(rep_path,'w'),indent=1); print(json.dumps(rep))
