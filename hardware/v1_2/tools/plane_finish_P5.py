"""Local motion logic plane connections, after the new placement fanout."""
import json,math
import pcbnew as k
from layout_P5 import paths,xy,pt,mm,F,B,track,via
from body_P5 import normal
from geometry_guard_P5 import Guard

def simple(a,z):
    dx,dy=z[0]-a[0],z[1]-a[1]
    if abs(dx)<1e-6 or abs(dy)<1e-6:return [[a,z]]
    sx=1 if dx>0 else -1;sy=1 if dy>0 else -1;m=min(abs(dx),abs(dy))
    out=[]
    for c in [(a[0]+sx*m,a[1]+sy*m),(z[0]-sx*m,z[1]-sy*m)]:
        q=[a,c,z];q=[v for i,v in enumerate(q) if i==0 or math.dist(q[i-1],v)>1e-5]
        if all(math.dist(u,v)>.49 for u,v in zip(q,q[1:])):out.append(q)
    if min(abs(dx),abs(dy))>=.5:
        out += [[a,(z[0]-sx*.5,a[1]),(z[0],a[1]+sy*.5),z],
                [a,(a[0],z[1]-sy*.5),(a[0]+sx*.5,z[1]),z]]
    return out

def run():
    name,d,p,r=paths('motion');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
    todo=json.loads((r/'plane_ports.json').read_text())['unresolved'];fan=json.loads((r/'fanout.json').read_text())['routes'];log=[]
    for row in sorted(todo,key=lambda x:x['net']!='/+3V3'):
        ref,pin,net=row['ref'],row['pin'],row['net'];f=fps[ref];q=next(q for q in f.Pads() if q.GetNumber()==pin)
        a=xy(q.GetPosition());nx,ny=normal('motion',f,q);port=next((t for t in fan if t['ref']==ref and t['pin']==pin),None)
        e=tuple(port['end']) if port else (a[0]+nx*.7,a[1]+ny*.7);g=Guard(b,net);routes=[]
        for t in b.GetTracks():
            if not isinstance(t,k.PCB_VIA) or t.GetNetname()!=net:continue
            z=xy(t.GetPosition())
            if math.dist(e,z)>5:continue
            for points in simple(e,z):
                if all(g.line_clear(u,v,f.GetLayer()) for u,v in zip(points,points[1:])):routes.append((sum(math.dist(u,v) for u,v in zip(points,points[1:])),points,None))
        for dist in [1.3,1.6,2.0,2.5,3,3.5]:
            for side in [0,.8,-.8,1.6,-1.6,2.4,-2.4]:
                raw=(a[0]+nx*dist-ny*side,a[1]+ny*dist+nx*side);z=tuple(round(v/.0254)*.0254 for v in raw)
                if not g.via_clear(z):continue
                if side==0:
                    landing=(a[0],z[1]) if nx else (z[0],a[1]);points=[landing,z]
                    if q.GetEffectiveShape(f.GetLayer()).Collide(pt(*landing),0) and g.line_clear(*points,f.GetLayer()):routes.append((math.dist(landing,z)+.7,points,z))
                else:
                    for points in simple(e,z):
                        if all(g.line_clear(u,v,f.GetLayer()) for u,v in zip(points,points[1:])):routes.append((sum(math.dist(u,v) for u,v in zip(points,points[1:]))+.7,points,z))
        if not routes:log.append(dict(**row,status='BLOCKED'));continue
        cost,points,v=min(routes,key=lambda q:q[0])
        # Remove only the new dangling fanout when the new straight line lands
        # directly inside the same actual pad. No legacy route is involved.
        if math.dist(points[0],a)<.03 and port:
            ids=set(port['tracks'])
            for t in list(b.GetTracks()):
                if t.m_Uuid.AsString() in ids:b.Delete(t)
        track(b,net,points,.2,f.GetLayer())
        if v:via(b,net,*v,grid=False)
        log.append(dict(**row,status='CONNECTED',points=points,new_via=v))
    k.SaveBoard(str(p),b);(r/'plane_completion.json').write_text(json.dumps(log,indent=2)+'\n')
    print('motion plane connections',[(q['ref']+'.'+q['pin'],q['status']) for q in log],flush=True)
if __name__=='__main__':run()
