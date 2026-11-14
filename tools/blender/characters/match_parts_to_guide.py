import numpy as np
from PIL import Image
def load(f,v):
    a=np.asarray(Image.open(f"r_{f}_{v}.png").convert("RGBA")).astype(np.float32)/255; return a
G={v:load("human",v) for v in ("front","side")}
def pts(img,step=3):
    al=img[...,3]>0.5; vv,uu=np.nonzero(al); sel=slice(None,None,step)
    vv,uu=vv[sel],uu[sel]; col=img[vv,uu,:3]
    x=(uu-550)/1000; z=0.5-(vv-550)/1000; return x,z,col
def score(g,x,z,col,s,dx,z0):
    gx=s*x+dx; gz=z0+s*z
    u=np.round(gx*1000+550).astype(int); v=np.round((0.5-gz)*1000+550).astype(int)
    ok=(u>=0)&(u<1100)&(v>=0)&(v<1100)
    inside=np.zeros(len(u),bool); d=np.ones(len(u))
    gi=g[v[ok],u[ok]]; inside[ok]=gi[:,3]>0.5
    d[ok]=np.abs(gi[:,:3]-col[ok]).mean(1)
    d[~inside]=1.0
    return 1-d.mean()
res={}
for f,(srange,zrange) in {"pants":((0.4,0.75),(-0.05,0.1)),"hoodie":((0.3,0.6),(0.3,0.6)),"head":((0.12,0.3),(0.65,0.9))}.items():
    x,z,col=pts(load(f,"front"))
    best=(-1,)
    for s in np.linspace(*srange,36):
        for z0 in np.linspace(*zrange,36):
            sc=score(G["front"],x,z,col,s,0,z0)
            if sc>best[0]: best=(sc,s,z0)
    _,s0,z00=best
    for s in np.linspace(s0-0.012,s0+0.012,13):
        for z0 in np.linspace(z00-0.006,z00+0.006,13):
            sc=score(G["front"],x,z,col,s,0,z0)
            if sc>best[0]: best=(sc,s,z0)
    sc,s,z0=best
    xs,zs,cs=pts(load(f,"side"))
    bd=(-1,)
    for dy in np.linspace(-0.08,0.08,81):
        v=score(G["side"],xs,zs,cs,s,dy,z0)
        if v>bd[0]: bd=(v,dy)
    res[f]=dict(score=round(float(sc),3),scale=round(float(s),4),z0=round(float(z0),4),dy_img=round(float(bd[1]),4),side_score=round(float(bd[0]),3))
    print(f,res[f])
import json; json.dump(res,open("match.json","w"),indent=1)
