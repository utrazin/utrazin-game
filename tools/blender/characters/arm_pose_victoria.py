import bpy, numpy as np, sys, math
from mathutils import Vector, Matrix
args=sys.argv[sys.argv.index("--")+1:]
DOWN=float(args[0]); BEND=float(args[1]); out=args[2]
bpy.ops.wm.open_mainfile(filepath="/home/claude/v3/CHR-002_Hero02_v024.blend")
o=bpy.data.objects["SK_Hero02"]; me=o.data; mw=o.matrix_world; mi=mw.inverted()
co=np.array([(mw@v.co)[:] for v in me.vertices])
def ss(t): t=min(1,max(0,t)); return t*t*(3-2*t)
res={}
for s in (1,-1):
    cs=[]
    for z in np.arange(0.97,1.21,0.03):
        sl=co[(np.abs(co[:,2]-z)<0.01)&(co[:,0]*s>0.2)]
        xs=sl[:,0]*s; xmax=xs.max(); sl=sl[xs>xmax-0.12]   # só a manga (pega a parte de fora)
        cs.append(sl.mean(0))
    cs=np.array(cs); c=cs.mean(0); u,sv,vt=np.linalg.svd(cs-c); d=vt[0]; d=d if d[2]<0 else -d
    t=(1.32-c[2])/d[2]; S=c+d*t
    tw=(0.93-c[2])/d[2]; W=c+d*tw
    E=(S+W)/2
    print("ARM",s,"S",S.round(3),"E",E.round(3),"W",W.round(3),"dir",d.round(3))
    res[s]=(Vector(S),Vector(E),Vector(d))
n=0
for v in me.vertices:
    p=mw@v.co; s=1 if p.x>0 else -1; S,E,d=res[s]
    rel=p-S; along=rel.dot(d); lat=(rel-d*along).length
    if p.z>1.40 or along<-0.04: continue
    R=0.075+0.03*max(0,1-along/0.15)   # raio da manga (maior perto do ombro)
    if lat>R+0.02: continue
    wcap=1-ss((lat-R)/0.02)
    w=ss((along+0.04)/0.10)*wcap
    if w<=0: continue
    # 1) abaixa o braço todo girando no ombro (eixo Y)
    ang=math.radians(DOWN)*w*(s)
    Ry=Matrix.Rotation(ang,3,'Y'); q=S+Ry@(p-S)
    # 2) dobra o cotovelo pra frente
    alongE=(p-E).dot(d)
    wb=ss(alongE/0.06+0.5)*wcap
    if wb>0:
        Ey=S+Ry@(E-S); dy=Ry@d
        axis=dy.cross(Vector((0,-1,0))).normalized()
        q=Ey+Matrix.Rotation(math.radians(BEND)*wb,3,axis)@(q-Ey)
    v.co=mi@q; n+=1
print("MOVED",n)
bpy.ops.wm.save_as_mainfile(filepath=out)
