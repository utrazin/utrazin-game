#!/usr/bin/env python3
"""[A-076] Confere a planta de cada construção: móveis dentro das paredes, sem sobrepor, sem bater nas paredes
internas e com o giro das portas livre. Roda com o módulo bpy (usa a biblioteca de móveis do gerador) e shapely:
  python tools/blender/check_interiors_l01.py
Também inunda o chão livre a partir da porta principal (herói de raio 38 cm) e confere se dá para chegar a cada
item, baú e porta. Sai com código 1 se achar problema."""
import math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_interiors_l01 as G
from shapely.geometry import Polygon, box, LineString, Point
from shapely import affinity

def footprint(kind, x, y, yaw):
    B, r, h = G.furniture(kind)
    polys = []
    if B.colliders:
        for (c, s, rot) in B.colliders:
            p = box(c[0]-s[0]/2, c[1]-s[1]/2, c[0]+s[0]/2, c[1]+s[1]/2)
            p = affinity.rotate(p, rot, origin=(c[0], c[1]), use_radians=True)
            polys.append(p)
        solid = True
    else:
        xs=[v[0] for v in B.verts]; ys=[v[1] for v in B.verts]
        polys=[box(min(xs),min(ys),max(xs),max(ys))]; solid=False
    out=[]
    for p in polys:
        p = affinity.rotate(p, yaw, origin=(0,0))
        out.append(affinity.translate(p, x, y))
    from shapely.ops import unary_union
    return unary_union(out), solid

def check(key, spec):
    sx, sy = spec["size"]; hx, hy = sx/2, sy/2; t = G.WALL_T/2
    inner_room = box(-hx+t, -hy+t, hx-t, hy-t)
    walls = [LineString([a,b]).buffer(0.075, cap_style=2) for (a,b,ops) in spec.get("inner",[])]
    # vãos das paredes internas não são parede
    probs=[]
    fps=[]
    for i,(kind,x,y,yaw) in enumerate(spec["furniture"]):
        fp, solid = footprint(kind,x,y,yaw)
        if not inner_room.buffer(0.01).contains(fp):
            probs.append(f"{kind}#{i} fura a parede externa")
        if solid:
            for w in walls:
                if fp.intersection(w).area > 0.01:
                    probs.append(f"{kind}#{i} bate numa parede interna")
        fps.append((i,kind,fp,solid))
    for j,(lab,x,y,yaw) in enumerate(spec.get("chests",[])):
        fp=affinity.translate(affinity.rotate(box(-0.5,-0.3,0.5,0.3),yaw,origin=(0,0)),x,y)
        if not inner_room.contains(fp): probs.append(f"baú {lab} fura parede")
        fps.append((100+j,"Bau",fp,True))
    for a in range(len(fps)):
        for b in range(a+1,len(fps)):
            ia,ka,fa,sa=fps[a]; ib,kb,fb,sb=fps[b]
            if sa and sb and fa.intersection(fb).area>0.005:
                probs.append(f"{ka}#{ia} sobrepõe {kb}#{ib}")
    # giro das portas: retângulo de profundidade = largura da folha dos dois lados (ou só fora se começa aberta)
    for d in G.door_list(spec):
        w=d["width_m"]; leaf = w/2 if d["double"] else w
        depth = leaf
        zone = box(-depth, -w/2, depth, w/2) if not d["start_open"] else box(0, -w/2, depth, w/2)
        zone = affinity.rotate(zone, d["yaw"], origin=(0,0))
        zone = affinity.translate(zone, d["x"], d["y"])
        for (i,kind,fp,solid) in fps:
            if solid and fp.intersection(zone).area>0.01:
                probs.append(f"porta ({d['x']:.1f},{d['y']:.1f}) {'int' if d['inner'] else 'ext'} bate em {kind}#{i}")
    # pickups dentro
    for (tp,x,y,z) in spec["pickups"]:
        if not inner_room.contains(Point(x,y)): probs.append(f"item {tp} fora")
    # cobertura: % da área com coisas
    from shapely.ops import unary_union
    used = unary_union([fp for (_,_,fp,_) in fps]).area
    return probs, used/(sx*sy)

if __name__=="__main__":
    tot=0
    for k,s in G.BUILDINGS.items():
        p,cov=check(k,s)
        tot+=len(p)
        print(f"{k:18s} móveis={len(s['furniture']):2d} ocupação={cov*100:4.1f}%  portas={len(G.door_list(s))}")
        for x in p: print("   -",x)
    print("PROBLEMAS", tot)
    if tot:
        sys.exit(1)

def reach(key, spec, r=0.38, cell=0.1):
    """Inunda o espaço livre (herói de raio r) a partir da porta principal e confere se dá para chegar
    perto (<= 1,4 m) de cada item, baú e porta."""
    import numpy as np
    from shapely.ops import unary_union
    from collections import deque
    sx, sy = spec["size"]; hx, hy = sx/2, sy/2; t = G.WALL_T/2
    solids=[]
    for (kind,x,y,yaw) in spec["furniture"]:
        fp,s=footprint(kind,x,y,yaw)
        if s: solids.append(fp)
    for (lab,x,y,yaw) in spec.get("chests",[]):
        solids.append(affinity.translate(affinity.rotate(box(-0.5,-0.3,0.5,0.3),yaw,origin=(0,0)),x,y))
    # paredes internas com vãos
    for (a,b,ops) in spec.get("inner",[]):
        from mathutils import Vector
        A,Bv=Vector(a),Vector(b); L=(Bv-A).length; u=(Bv-A).normalized()
        cuts=sorted([(o[0]-o[1]/2,o[0]+o[1]/2) for o in ops if o[4]=="porta"])
        tt=0.0
        for c0,c1 in cuts+[(L,L)]:
            if c0-tt>0.01:
                p0=A+u*tt; p1=A+u*c0; solids.append(LineString([(p0.x,p0.y),(p1.x,p1.y)]).buffer(0.075,cap_style=2))
            tt=c1
    blocked=unary_union(solids).buffer(r) if solids else None
    nx,ny=int(sx/cell),int(sy/cell)
    free=np.zeros((nx,ny),bool)
    from shapely.prepared import prep
    pb=prep(blocked) if blocked is not None else None
    for i in range(nx):
        for j in range(ny):
            x=-hx+(i+0.5)*cell; y=-hy+(j+0.5)*cell
            if abs(x)>hx-t-r or abs(y)>hy-t-r: continue
            if pb and pb.contains(Point(x,y)): continue
            free[i,j]=True
    doors=G.door_list(spec)
    main=[d for d in doors if not d["inner"]][0]
    # semente: logo dentro da porta principal
    import math as m
    yr=m.radians(main["yaw"]); sxp=main["x"]-m.cos(yr)*0.6; syp=main["y"]-m.sin(yr)*0.6
    si,sj=int((sxp+hx)/cell),int((syp+hy)/cell)
    seen=np.zeros_like(free); q=deque()
    if 0<=si<nx and 0<=sj<ny and free[si,sj]:
        seen[si,sj]=True; q.append((si,sj))
    while q:
        i,j=q.popleft()
        for di,dj in ((1,0),(-1,0),(0,1),(0,-1)):
            a,b=i+di,j+dj
            if 0<=a<nx and 0<=b<ny and free[a,b] and not seen[a,b]:
                seen[a,b]=True; q.append((a,b))
    pts=np.argwhere(seen)
    def ok(x,y,lim=1.4):
        if len(pts)==0: return False
        xs=-hx+(pts[:,0]+0.5)*cell; ys=-hy+(pts[:,1]+0.5)*cell
        return float(np.min(np.hypot(xs-x,ys-y)))<=lim
    probs=[]
    if not seen.any(): probs.append("porta principal bloqueada")
    for (tp,x,y,z) in spec["pickups"]:
        if not ok(x,y): probs.append(f"item {tp} ({x},{y}) inalcançável")
    for (lab,x,y,yaw) in spec.get("chests",[]):
        if not ok(x,y,1.2): probs.append(f"baú {lab} inalcançável")
    for d in doors:
        if not ok(d["x"],d["y"],0.9): probs.append(f"porta ({d['x']},{d['y']}) inalcançável por dentro")
    return probs, seen.sum()/max(1,free.sum())

if __name__=="__main__":
    n=0
    for k,s in G.BUILDINGS.items():
        p,f=reach(k,s); n+=len(p)
        print(f"{k:18s} alcançável {f*100:5.1f}% do chão livre")
        for x in p: print("   -",x)
    print("PROBLEMAS DE ACESSO", n)
    sys.exit(1 if n else 0)
