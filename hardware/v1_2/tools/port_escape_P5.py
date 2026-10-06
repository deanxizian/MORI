"""Plan outward pin escapes together with a limited local copper displacement.

Protect pads, bodies, fixed interfaces and load conductors. Candidate signal /
plane copper displaced by a selected escape is logged and must be reconnected.
This does not claim acceptance: native DRC and whole-route review follow.
"""
import math,json,sys,time
import pcbnew as k
from layout_P5 import *
from body_P5 import normal
from geometry_guard_P5 import Guard

def run(kind,requests,width=.2,vd=.8,dr=.3,protected_nets=()):
 n,d,p,r=paths(kind);b=k.LoadBoard(str(p));log=[]
 for ref,pin in requests:
  f=next(f for f in b.GetFootprints() if f.GetReference()==ref);pad=next(q for q in f.Pads() if q.GetNumber()==pin);net=pad.GetNetname();a=xy(pad.GetPosition());l=f.GetLayer();nx,ny=normal(kind,f,pad)
  other=[t for t in b.GetTracks() if t.GetNetname()!=net and t.GetNetname() not in protected_nets and (isinstance(t,k.PCB_VIA) or k.ToMM(t.GetWidth())<=.25)]
  for t in other:b.Remove(t)
  g=Guard(b,net);candidates=[]
  for dist in [1.2,1.5,1.8,2.2,2.7,3.2,4.0]:
   for side in [0,.6,-.6,1.2,-1.2,1.8,-1.8,2.4,-2.4]:
    v=tuple(round(x/.0254)*.0254 for x in (a[0]+nx*dist-ny*side,a[1]+ny*dist+nx*side))
    if not g.via_clear(v,vd):continue
    if any(z.GetIsRuleArea() and z.GetZoneName().startswith('NETBODY_') and z.Outline().Collide(pt(*v),mm(vd/2+.002)) for z in b.Zones()):continue
    if side==0:
     landing=(a[0],v[1]) if nx else (v[0],a[1]);ps=[landing,v]
    else:
     dx,dy=v[0]-a[0],v[1]-a[1];ax=nx*dx+ny*dy;orth=-ny*dx+nx*dy;advance=ax-abs(orth)
     if advance<.5:continue
     ps=[a,(a[0]+nx*advance,a[1]+ny*advance),v]
    if not all(g.line_clear(u,z,l,width) for u,z in zip(ps,ps[1:])):continue
    temp=track(b,net,ps,width,l);vv=k.PCB_VIA(b);vv.SetPosition(pt(*v));vv.SetWidth(mm(vd));vv.SetDrill(mm(dr));vv.SetViaType(k.VIATYPE_THROUGH);vv.SetLayerPair(F,B);vv.SetNet(b.GetNetsByName()[net]);b.Add(vv)
    shapes=[(t.GetEffectiveShape(l),l) for t in temp]+[(vv.GetEffectiveShape(c),c) for c in [F,B]]
    hit=[]
    for t in other:
     if any(t.IsOnLayer(c) and sh.Collide(t.GetEffectiveShape(c),mm(.205)) for sh,c in shapes):hit.append(t)
    for t in temp:b.Delete(t)
    b.Delete(vv)
    cost=sum(7 if isinstance(t,k.PCB_VIA) else 2+min(6,k.ToMM(t.GetLength())*.1) for t in hit)+sum(math.dist(u,z) for u,z in zip(ps,ps[1:]))
    candidates.append((cost,ps,v,[t.m_Uuid.AsString() for t in hit]))
  for t in other:b.Add(t)
  if not candidates:print('NO ESCAPE',ref,pin,flush=True);log.append(dict(ref=ref,pin=pin,status='BLOCKED'));continue
  cost,ps,v,ids=min(candidates,key=lambda q:q[0]);ripped=[]
  for t in list(b.GetTracks()):
   if t.m_Uuid.AsString() in ids:
    ripped.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname(),is_via=isinstance(t,k.PCB_VIA),start=xy(t.GetStart()),end=xy(t.GetEnd())));b.Delete(t)
  track(b,net,ps,width,l);via(b,net,*v,vd=vd,dr=dr,grid=False)
  log.append(dict(ref=ref,pin=pin,net=net,path=ps,new_via=v,displaced=ripped));print('ESCAPE',ref,pin,net,ps,'displaced',len(ripped),flush=True)
  k.SaveBoard(str(p),b)
 (r/('escape_displacement_'+str(int(time.time()))+'.json')).write_text(json.dumps(log,indent=2)+'\n')
if __name__=='__main__':run(sys.argv[1],[x.split('.') for x in sys.argv[2:]])
