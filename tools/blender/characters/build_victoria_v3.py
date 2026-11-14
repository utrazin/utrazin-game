import bpy, json, sys
args=sys.argv[sys.argv.index("--")+1:]
cfg=json.load(open(args[0])); out=args[1]; H=cfg["height_m"]
bpy.ops.wm.read_factory_settings(use_empty=True)
objs={}
for name,p in cfg["parts"].items():
    b=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=f"/home/claude/v3/src/{p.get('file',name)}.glb")
    new=[o for o in bpy.data.objects if o not in b]; mesh=[o for o in new if o.type=="MESH"][0]
    mw=mesh.matrix_world.copy(); mesh.parent=None; mesh.matrix_world=mw
    for o in new:
        if o is not mesh: bpy.data.objects.remove(o)
    s=p["scale"]*H; mesh.scale=(s,s,s); mesh.location=(0,p.get("dy",0)*H,p["z0"]*H); mesh.name="Part_"+name; objs[name]=mesh
bpy.ops.object.select_all(action="DESELECT")
for o in objs.values(): o.select_set(True)
bpy.context.view_layer.objects.active=objs["hoodie"]
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
# calça: estica da canela pra cima até a cintura entrar por baixo do moletom
ps=cfg.get("pants_stretch")
if ps:
    p=objs["pants"]; zmin=min(v.co.z for v in p.data.vertices)
    for v in p.data.vertices: v.co.z-=zmin
    top=max(v.co.z for v in p.data.vertices); k=(ps["top"]-ps["from"])/(top-ps["from"])
    for v in p.data.vertices:
        if v.co.z>ps["from"]: v.co.z=ps["from"]+(v.co.z-ps["from"])*k
    print("PANTS_K",round(k,3))
zmin=min((o.matrix_world@v.co).z for o in objs.values() for v in o.data.vertices)
print("ZMIN",zmin)
for sr in cfg.get("smooth_regions",[]):  # alisa pedacinhos serrilhados da malha
    import bmesh
    from mathutils import Vector
    ob_=objs[sr["part"]]; b_=bmesh.new(); b_.from_mesh(ob_.data); c_=Vector(sr["c"])
    vs_=[v for v in b_.verts if (v.co-c_).length<sr["r"] and v.co.y>sr.get("ymin",-9)]
    for _ in range(sr["it"]): bmesh.ops.smooth_laplacian_vert(b_,verts=vs_,lambda_factor=sr["f"],lambda_border=0.0,use_x=True,use_y=True,use_z=True,preserve_volume=True)
    b_.to_mesh(ob_.data); b_.free(); print("SMOOTH",sr["part"],len(vs_))
for dr in cfg.get("delete_islands",[]):  # apaga fragmentos soltos (pedacinhos serrilhados)
    import bmesh
    from mathutils import Vector
    ob_=objs[dr["part"]]; b_=bmesh.new(); b_.from_mesh(ob_.data); c_=Vector(dr["c"]); seen=set(); kill=[]
    for f in b_.faces:
        if f in seen: continue
        st=[f]; comp=[]; seen.add(f)
        while st:
            x=st.pop(); comp.append(x)
            for e in x.edges:
                for g in e.link_faces:
                    if g not in seen: seen.add(g); st.append(g)
        if len(comp)<=dr["max_faces"] and min((g.calc_center_median()-c_).length for g in comp)<dr["r"]: kill+=comp
    bmesh.ops.delete(b_,geom=kill,context="FACES"); b_.to_mesh(ob_.data); b_.free(); print("DEL_ISLANDS",len(kill))
hx=cfg.get("head_dx",0)
if hx:
    for v in objs["head"].data.vertices: v.co.x+=hx
ns=cfg.get("neck_stretch")  # igual ao Enzo: estica o colo pra baixo pra dentro do moletom
if ns:
    hd=objs["head"]; bot=min(v.co.z for v in hd.data.vertices); k=(ns["top"]-ns["new_bottom"])/(ns["top"]-bot)
    for v in hd.data.vertices:
        if v.co.z<ns["top"]:
            v.co.z=ns["top"]-(ns["top"]-v.co.z)*k
            if ns.get("push_back"): v.co.y+=ns["push_back"]*(ns["top"]-v.co.z)/(ns["top"]-ns["new_bottom"])
    print("NECK_K",round(k,2),"bottom",round(bot,3))
if "--guide" in args:
    b=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath="/home/claude/v3/src/human.glb")
    for o in set(bpy.data.objects)-b:
        if o.parent is None: o.location.x=0.9; o.scale=(H,H,H)
fl=cfg.get("collar_fill")  # "tecido" por dentro da gola: faixa colada ao pescoço, cor do moletom
if fl:
    import math, bmesh
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    hd=objs["head"]; ho=objs["hoodie"]
    hb=bmesh.new(); hb.from_mesh(hd.data); ht=BVHTree.FromBMesh(hb)
    ob=bmesh.new(); ob.from_mesh(ho.data); ob.faces.ensure_lookup_table(); otree=BVHTree.FromBMesh(ob); ouv=ob.loops.layers.uv.active
    loc,nrm,fi,d=otree.find_nearest(Vector(fl["uv_from"])); fuv=ob.faces[fi].loops[0][ouv].uv.copy(); fmat=ob.faces[fi].material_index
    cx,cy=fl["axis"]; N,K=fl["n"],fl["k"]; a0,a1=math.radians(fl["ang"][0]),math.radians(fl["ang"][1])
    bm=bmesh.new(); bm.from_mesh(ho.data); uvl=bm.loops.layers.uv.active
    rows=[]
    for kk in range(K+1):
        row=[]
        for i in range(N+1):
            a=a0+(a1-a0)*i/N; dvec=Vector((math.cos(a),math.sin(a),0))
            zt=fl["z"][1]
            if fl.get("top_curve"):
                tc=fl["top_curve"]; xx=abs(cx+dvec.x*0.04); zt=min(zt,tc[0]+tc[1]*xx)
            z=fl["z"][0]+(zt-fl["z"][0])*kk/K
            h=ht.ray_cast(Vector((cx,cy,z)),dvec,0.2)
            r=(Vector((h[0].x-cx,h[0].y-cy,0)).length if h[0] else 0.05)+fl["off"]
            row.append(bm.verts.new((cx+dvec.x*r,cy+dvec.y*r,z)))
        rows.append(row)
    nf=0
    for kk in range(K):
        for i in range(N):
            f=bm.faces.new((rows[kk][i],rows[kk][i+1],rows[kk+1][i+1],rows[kk+1][i])); f.material_index=fmat; f.smooth=True; nf+=1
            for lp in f.loops: lp[uvl].uv=fuv
            c=f.calc_center_median()
            if f.normal.dot(Vector((c.x-cx,c.y-cy,0)))<0: f.normal_flip()
    bm.to_mesh(ho.data); bm.free(); hb.free(); ob.free()
    print("COLLAR_FILL",nf)
sk=cfg.get("bib_skirt")  # "camiseta": tecido que sai da borda de baixo do colo da cabeça e desce por dentro do moletom
if sk:
    import math, bmesh
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    hd=objs["head"]; ho=objs["hoodie"]; cx,cy=sk["axis"]
    hb=bmesh.new(); hb.from_mesh(hd.data); hb.verts.ensure_lookup_table()
    bverts=set()
    for e in hb.edges:
        if e.is_boundary and max(v.co.z for v in e.verts)<sk["zmax"]: bverts.update(e.verts)
    # componentes da borda; pega o maior laço (a borda de baixo do colo)
    allb=set(); 
    for e in hb.edges:
        if e.is_boundary: allb.update(e.verts)
    adj={v:[e.other_vert(v) for e in v.link_edges if e.is_boundary] for v in allb}
    seen=set(); comps=[]
    for v in allb:
        if v in seen: continue
        st=[v]; comp=[]; seen.add(v)
        while st:
            x=st.pop(); comp.append(x)
            for n in adj[x]:
                if n not in seen: seen.add(n); st.append(n)
        comps.append(comp)
    comps=[c for c in comps if min(v.co.z for v in c)<sk["zmax"]]
    comps.sort(key=lambda c:-len(c)); print("COMPS",[(len(c),round(min(v.co.z for v in c),3),round(max(v.co.z for v in c),3)) for c in comps[:5]])
    comp=set(comps[0]); start=min(comp,key=lambda v:v.co.y); loop=[start]; prev=None; cur=start
    while True:
        nx=[n for n in adj[cur] if n is not prev and n in comp]
        if not nx: break
        nxt=nx[0]
        if nxt is start: break
        if nxt in loop:
            alt=[n for n in nx if n not in loop]
            if not alt: break
            nxt=alt[0]
        prev,cur=cur,nxt; loop.append(cur)
    print("BIB_LOOP",len(loop),"of",len(bverts))
    # suaviza a borda (tira o serrilhado), só em z
    L=len(loop)
    for _ in range(sk["smooth"]):
        zs=[v.co.z for v in loop]
        for i,v in enumerate(loop): v.co.z=0.25*zs[i-1]+0.5*zs[i]+0.25*zs[(i+1)%L]
    hb.to_mesh(hd.data)
    ob=bmesh.new(); ob.from_mesh(ho.data); ob.faces.ensure_lookup_table(); otree=BVHTree.FromBMesh(ob); ouv=ob.loops.layers.uv.active
    loc,nrm,fi,d=otree.find_nearest(Vector(sk["uv_from"])); fuv=ob.faces[fi].loops[0][ouv].uv.copy(); fmat=ob.faces[fi].material_index
    bm=bmesh.new(); bm.from_mesh(ho.data); uvl=bm.loops.layers.uv.active
    rows=[]
    for k in range(sk["k"]+1):
        row=[]
        for v in loop:
            p=v.co; dvec=Vector((p.x-cx,p.y-cy,0)); r=dvec.length; dvec.normalize()
            if k==0: z=p.z+sk["up"]; rr=r-sk["inset"]
            else: z=p.z-sk["down"]*k/sk["k"]; rr=r+sk["out"]*k/sk["k"]
            row.append(bm.verts.new((cx+dvec.x*rr,cy+dvec.y*rr,z)))
        rows.append(row)
    nf=0
    for k in range(sk["k"]):
        for i in range(L):
            f=bm.faces.new((rows[k][i],rows[k][(i+1)%L],rows[k+1][(i+1)%L],rows[k+1][i])); f.material_index=fmat; f.smooth=True; nf+=1
            for lp in f.loops: lp[uvl].uv=fuv
            c=f.calc_center_median()
            if f.normal.dot(Vector((c.x-cx,c.y-cy,0)))<0: f.normal_flip()
    bm.to_mesh(ho.data); bm.free(); hb.free(); ob.free()
    print("BIB_SKIRT",nf)
vs=cfg.get("v_sheet")  # fecha o vão do V da gola: folha de tecido logo atrás do colo/gola, só onde se via o fundo do moletom
if vs:
    import bmesh, numpy as np
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    hd=objs["head"]; ho=objs["hoodie"]
    hb=bmesh.new(); hb.from_mesh(hd.data); ht=BVHTree.FromBMesh(hb)
    ob=bmesh.new(); ob.from_mesh(ho.data); ob.faces.ensure_lookup_table(); ot=BVHTree.FromBMesh(ob); ouv=ob.loops.layers.uv.active
    loc,nrm,fi,d=ot.find_nearest(Vector(vs["uv_from"])); fuv=ob.faces[fi].loops[0][ouv].uv.copy(); fmat=ob.faces[fi].material_index
    xs=np.arange(vs["x"][0],vs["x"][1]+1e-9,vs["step"]); zs=np.arange(vs["z"][1],vs["z"][0]-1e-9,-vs["step"])
    Y=np.zeros((len(zs),len(xs))); need=np.zeros_like(Y,bool)
    last=[None]*len(xs)
    for i,z in enumerate(zs):
        for j,x in enumerate(xs):
            o=Vector((x,-1,z)); dd=Vector((0,1,0)); b=ot.ray_cast(o,dd,2)
            ya=None; oo=o.copy()
            while True:  # pega a pele mais funda (atravessa o colar)
                a=ht.ray_cast(oo,dd,2)
                if a[0] is None or a[0].y>vs["skin_ymax"]: break
                ya=a[0].y; oo=a[0]+dd*1e-4
            first=ht.ray_cast(o,dd,2); yfirst=first[0].y if first[0] else None
            yb=b[0].y if b[0] else None
            if ya is not None: last[j]=ya
            base=last[j] if last[j] is not None else vs["y_default"]
            y=base+vs["behind"]
            if yb is not None and yb<vs["front_max"]: y=max(y,yb+vs["behind"]) if yb<y else y
            Y[i,j]=y
            if yb is not None and yb>vs["front_max"] and (yfirst is None or yfirst>yb): need[i,j]=True
    # suaviza a folha
    for _ in range(3): Y[1:-1,1:-1]=(Y[1:-1,1:-1]*2+Y[:-2,1:-1]+Y[2:,1:-1]+Y[1:-1,:-2]+Y[1:-1,2:])/6
    print("V_SHEET holes",int(need.sum()),"of",need.size)
    bm=bmesh.new(); bm.from_mesh(ho.data); uvl=bm.loops.layers.uv.active
    V=[[bm.verts.new((xs[j],Y[i,j],zs[i])) for j in range(len(xs))] for i in range(len(zs))]
    nf=0
    keep=need.copy()
    for _ in range(vs["grow"]):
        k2=keep.copy(); k2[1:]|=keep[:-1]; k2[:-1]|=keep[1:]; k2[:,1:]|=keep[:,:-1]; k2[:,:-1]|=keep[:,1:]; keep=k2
    for i in range(len(zs)-1):
        for j in range(len(xs)-1):
            if not (keep[i,j] or keep[i+1,j] or keep[i,j+1] or keep[i+1,j+1]): continue
            f=bm.faces.new((V[i][j],V[i+1][j],V[i+1][j+1],V[i][j+1])); f.material_index=fmat; f.smooth=True; nf+=1
            for lp in f.loops: lp[uvl].uv=fuv
            if f.normal.y>0: f.normal_flip()
    bm.to_mesh(ho.data); bm.free(); hb.free(); ob.free(); print("V_SHEET faces",nf)
us=cfg.get("undershirt")  # gola de camiseta por baixo do moletom: cobre a borda do colo e fecha o V
if us:
    import bmesh, numpy as np
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    hd=objs["head"]; ho=objs["hoodie"]
    hb=bmesh.new(); hb.from_mesh(hd.data); ht=BVHTree.FromBMesh(hb)
    ob=bmesh.new(); ob.from_mesh(ho.data); ob.faces.ensure_lookup_table(); ot=BVHTree.FromBMesh(ob); ouv=ob.loops.layers.uv.active
    loc,nrm,fi,d=ot.find_nearest(Vector(us["uv_from"])); fuv=ob.faces[fi].loops[0][ouv].uv.copy(); fmat=ob.faces[fi].material_index
    dd=Vector((0,1,0))
    def skin_y(x,z):
        o=Vector((x,-1,z)); ya=None
        while True:
            a=ht.ray_cast(o,dd,2)
            if a[0] is None or a[0].y>us["skin_ymax"]: break
            ya=a[0].y; o=a[0]+dd*1e-4
        return ya
    xs=np.arange(us["x"][0],us["x"][1]+1e-9,us["dx"])
    # borda de baixo do colo (pele) por coluna
    ze=[]
    for x in xs:
        z=us["zscan"][1]; zl=None
        while z>us["zscan"][0]:
            if skin_y(x,z) is not None: zl=z
            elif zl is not None: break
            z-=0.001
        ze.append(zl if zl is not None else np.nan)
    ze=np.array(ze); ok=~np.isnan(ze)
    cf=np.polyfit(xs[ok]-us["cx"],ze[ok],2)   # curva lisa (decote em U)
    zl=np.polyval(cf,xs-us["cx"])+us["lift"]
    if us.get("side_raise"):
        sr=us["side_raise"]; d=np.abs(xs-us["cx"]); t=np.clip((d-sr["from"])/(sr["to"]-sr["from"]),0,1); zl=zl+sr["dz"]*t*t*(3-2*t)
    zl=np.minimum(zl,us["zcap"])
    print("UNDERSHIRT edge pts",int(ok.sum()),"curve",np.round(cf,3))
    if us.get("cut_skin_below"):
        hb2=bmesh.new(); hb2.from_mesh(hd.data); kill=[]
        for f in hb2.faces:
            c_=f.calc_center_median()
            if c_.y<0.0 and abs(c_.x-us["cx"])<0.065:
                zc=np.polyval(cf,c_.x-us["cx"])+us["lift"]-us["cut_skin_below"]
                if c_.z<zc and c_.z>1.30: kill.append(f)
        bmesh.ops.delete(hb2,geom=kill,context="FACES"); hb2.to_mesh(hd.data); hb2.free(); print("SKIN_CUT",len(kill))
    bm=bmesh.new(); bm.from_mesh(ho.data); uvl=bm.loops.layers.uv.active
    prof=us["profile"]   # [(dz abaixo da linha, deslocamento pra frente)]
    cols=[]; YY=[]
    for j,x in enumerate(xs):
        col=[]; last=None
        for dz,fwd in prof:
            z=zl[j]-dz; y=skin_y(x,z)
            if y is None:
                y=(last if last is not None else -0.03)-us["slope"]*(dz-(prof_prev if last is not None else 0)) if False else (last if last is not None else -0.03)
            else: last=y
            yb_=y-fwd
            if us.get("side_back"):
                sb=us["side_back"]; dxx=abs(x-us["cx"]); t=min(1,max(0,(dxx-sb["from"])/(sb["to"]-sb["from"]))); yb_+=sb["dy"]*t*t*(3-2*t)
            if us.get("front_ref")=="first":
                fh=ht.ray_cast(Vector((x,-1,z)),dd,2); ref=(fh[0].y if fh[0] is not None and fh[0].y<us["skin_ymax"] else 9.0)
            else: ref=(y if skin_y(x,z) is not None else 9.0)
            col.append([x,yb_,z,ref])
        cols.append(col)
    A=np.array(cols)  # (nx, nprof, 3)
    for _ in range(us.get("ysmooth",0)):
        Y=A[:,:,1].copy(); A[1:-1,:,1]=0.25*Y[:-2]+0.5*Y[1:-1]+0.25*Y[2:]
    A[:,:,1]=np.minimum(A[:,:,1],A[:,:,3]-us.get("min_front",0.0008))
    if "max_back_step" in us:
        for k in range(1,A.shape[1]-2): A[:,k,1]=np.minimum(A[:,k,1],A[:,k-1,1]+us["max_back_step"])
    for _ in range(us.get("vsmooth",0)):  # alisa na vertical (tira vinco)
        Y=A[:,:,1].copy(); A[:,2:-1,1]=0.25*Y[:,1:-2]+0.5*Y[:,2:-1]+0.25*Y[:,3:]
        A[:,:,1]=np.minimum(A[:,:,1],A[:,:,3]-us.get("min_front",0.0008))
    if us.get("behind_hoodie"):
        hob=bmesh.new(); hob.from_mesh(ho.data); hot=BVHTree.FromBMesh(hob); nb=0
        for j in range(A.shape[0]):
            for k in range(2,A.shape[1]):
                x,y,z=A[j,k,:3]; h=hot.ray_cast(Vector((x,-1,z)),Vector((0,1,0)),2)
                if h[0] is not None and y<h[0].y+us["behind_hoodie"] and h[0].y<us["skin_ymax"]:
                    # só empurra se o moletom está na frente da pele nesse ponto
                    A[j,k,1]=h[0].y+us["behind_hoodie"]; nb+=1
        hob.free(); print("BEHIND",nb)
    cols=[[bm.verts.new(tuple(A[j,k,:3])) for k in range(A.shape[1])] for j in range(A.shape[0])]
    nf=0
    for j in range(len(xs)-1):
        for k in range(len(prof)-1):
            f=bm.faces.new((cols[j][k],cols[j+1][k],cols[j+1][k+1],cols[j][k+1])); f.material_index=fmat; f.smooth=True; nf+=1
            for lp in f.loops: lp[uvl].uv=fuv
            if f.normal.y>0: f.normal_flip()
    bm.to_mesh(ho.data); bm.free(); hb.free(); ob.free(); print("UNDERSHIRT faces",nf)
bpy.ops.wm.save_as_mainfile(filepath=out); print("SAVED")
